/*
 * TLS variant of the wallet round-trip harness (TASK-057): points at the
 * local TLS front (https://localhost:8443) which terminates TLS onto the
 * http pilot edge. Run with NODE_TLS_REJECT_UNAUTHORIZED=0 for the
 * self-signed validation certificate.
 */
import { Openid4vciClient } from '@openid4vc/openid4vci'
import { clientAuthenticationNone } from '@openid4vc/oauth2'
import * as jose from 'jose'
import { createHash, randomBytes, webcrypto } from 'node:crypto'

const ISSUER = 'https://localhost:8443/hkt'
const EDGE = 'https://localhost:8443'
const API_KEY = requiredEnv('DIDVC_INTERNAL_API_KEY')

function requiredEnv(name: string): string {
  const value = process.env[name]
  if (!value) throw new Error(`Missing required environment variable ${name}`)
  return value
}

const b64url = (input) => Buffer.from(input).toString('base64url')
const sha256 = (data) => createHash('sha256').update(data).digest()

async function main() {
  const holderKey = await jose.generateKeyPair('EdDSA', { crv: 'Ed25519', extractable: true })
  const holderPrivateJwk = await jose.exportJWK(holderKey.privateKey)
  holderPrivateJwk.alg = 'EdDSA'
  const holderPublicJwk = await jose.exportJWK(holderKey.publicKey)
  holderPublicJwk.alg = 'EdDSA'

  const client = new Openid4vciClient({
    callbacks: {
      hash: (data, alg) => {
        if (alg !== 'sha-256') throw new Error('unsupported hash ' + alg)
        return sha256(data)
      },
      generateRandom: (byteLength) => randomBytes(byteLength),
      signJwt: async (signer, { header, payload }) => {
        const key = await jose.importJWK(signer.jwk, 'EdDSA')
        const compact = await new jose.CompactSign(
          new TextEncoder().encode(JSON.stringify(payload)),
        )
          .setProtectedHeader(header)
          .sign(key)
        return { jwt: compact, signerJwk: signer.jwk }
      },
      decryptJwe: async () => ({ decrypted: false }),
      clientAuthentication: clientAuthenticationNone({ clientId: 'didvc:pairwise:wallet-demo' }),
    },
  })

  const kid = (await (await fetch(`${EDGE}/demo/issuer-kid`)).json()).kid
  const offerResponse = await fetch(`${ISSUER}/internal/offers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Api-Key': API_KEY },
    body: JSON.stringify({
      schemaId: 'hkt-kyc-v1',
      vct: 'hkt_kyc_v1',
      subjectId: 'didvc:pairwise:wallet-demo',
      kid,
      alwaysDisclosedClaims: { kycLevel: 'REMOTE_FULL' },
      selectivelyDisclosedClaims: { givenName: 'WalletDemo', nationality: 'HK' },
    }),
  })
  if (!offerResponse.ok) throw new Error('offer creation failed: ' + (await offerResponse.text()))
  const offer = await offerResponse.json()
  console.log('STEP 1 offer received:', JSON.stringify(offer).slice(0, 120))

  const offerUri = 'openid-credential-offer://?' + new URLSearchParams({
    credential_offer: JSON.stringify(offer),
  }).toString()
  const resolvedOffer = await client.resolveCredentialOffer(offerUri)
  console.log('STEP 2a offer resolved')
  const issuerMetadata = await client.resolveIssuerMetadata(ISSUER)
  console.log('STEP 2b issuer metadata resolved:', issuerMetadata.credentialIssuer.credentialIssuer)
  const tokenResponse = await client.retrievePreAuthorizedCodeAccessTokenFromOffer({
    credentialOffer: resolvedOffer,
    issuerMetadata,
  })
  if (!tokenResponse.accessTokenResponse?.access_token) throw new Error('no access token received')
  const accessToken = tokenResponse.accessTokenResponse.access_token
  const cNonce = tokenResponse.accessTokenResponse.c_nonce
  console.log('STEP 2 pre-authorized code exchanged')

  const proof = await client.createCredentialRequestJwtProof({
    signer: { method: 'jwk', alg: 'EdDSA', jwk: holderPrivateJwk, publicJwk: holderPublicJwk },
    nonce: cNonce,
    issuedAt: new Date(),
    issuerMetadata,
    credentialConfigurationId: 'hkt_kyc_v1',
  })
  const credentialResponse = await client.retrieveCredentials({
    issuerMetadata,
    accessToken,
    proof: { proof_type: 'jwt', jwt: proof.jwt },
    credentialConfigurationId: 'hkt_kyc_v1',
  })
  const credential = credentialResponse.credentialResponse?.credential
  if (!credential) throw new Error('no credential in response: ' + JSON.stringify(credentialResponse).slice(0, 200))
  console.log('STEP 3 credential received (vc+sd-jwt):', credential.slice(0, 60) + '...')

  const jwsPart = credential.split('~')[0]
  const issuerJwk = await (await fetch(`${EDGE}/demo/issuer-jwk`)).json()
  const issuerKey = await jose.importJWK(issuerJwk, 'EdDSA')
  const { payload } = await jose.compactVerify(jwsPart, issuerKey)
  const payloadJson = JSON.parse(new TextDecoder().decode(payload))
  if (payloadJson.vct !== 'hkt_kyc_v1') throw new Error('vct mismatch')
  console.log('STEP 4 wallet-side signature verification OK, vct =', payloadJson.vct)

  const nonce = 'wallet-nonce-1'
  const authorizeResponse = await fetch(`${EDGE}/bank-a/vp/authorize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      client_id: 'wallet-demo',
      nonce,
      dcql_query: {
        credentials: [
          {
            id: 'kyc_credential',
            format: 'vc+sd-jwt',
            meta: { vct_values: ['hkt_kyc_v1'] },
            claims: [{ path: ['givenName'], values: ['WalletDemo'] }],
          },
        ],
      },
    }),
  })
  if (!authorizeResponse.ok) throw new Error('authorize failed: ' + (await authorizeResponse.text()))
  const requestUri = (await authorizeResponse.json()).request_uri
  const requestObject = await (await fetch(requestUri)).text()
  if (!requestObject.split('.').length) throw new Error('request object is not a JWT')
  console.log('STEP 5 authorization request received:', requestUri.split('/').pop())

  const sdHash = b64url(sha256(credential))
  const kbJwt = await new jose.CompactSign(
    new TextEncoder().encode(JSON.stringify({
      nonce,
      aud: 'wallet-demo',
      iat: Math.floor(Date.now() / 1000),
      sd_hash: sdHash,
    })),
  )
    .setProtectedHeader({ alg: 'EdDSA', typ: 'kb+jwt' })
    .sign(holderKey.privateKey)
  const vpToken = credential + '~' + kbJwt

  const requestId = requestUri.split('/').pop()
  const directPostResponse = await fetch(`${EDGE}/bank-a/vp/direct_post`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ state: requestId, nonce, vp_token: vpToken }),
  })
  const verificationResult = await directPostResponse.json()
  if (!directPostResponse.ok) {
    throw new Error('verification rejected: ' + JSON.stringify(verificationResult))
  }
  if (verificationResult.valid !== true) throw new Error('verification returned valid=false')
  if (verificationResult.claims.givenName !== 'WalletDemo') {
    throw new Error('disclosed claim mismatch: ' + JSON.stringify(verificationResult.claims))
  }
  console.log('STEP 6 presentation verified:', JSON.stringify({
    valid: verificationResult.valid,
    vct: verificationResult.vct,
    claims: verificationResult.claims,
  }))

  console.log('WALLET ROUND TRIP OK')
}

main().catch((error) => {
  console.error('WALLET ROUND TRIP FAILED:', error.message)
  console.error(error.stack)
  process.exit(1)
})
