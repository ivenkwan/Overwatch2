"use client";

/**
 * Authorized-wallet onboarding console (AWI TASK-047).
 *
 * Operator workflow, end to end:
 *   1. Submit the applicant's KYC/KYB credential -> verified against the
 *      identity provider (party + credential recorded, idempotent).
 *   2. Issue an address-control challenge; the applicant signs it with the
 *      wallet key; paste the signature -> wallet registered (maker).
 *   3. A different operator approves the pending authorization (checker) —
 *      maker-checker enforced server-side.
 *   4. The authorization list shows masked state; revoke is one click.
 *
 * Claims render masked by the server per the caller's role; every action is
 * audited server-side.
 */

import React, { useCallback, useEffect, useState } from "react";
import { api } from "../../../services/api";

type Wallet = {
  instrument_id: string;
  blockchain: string;
  wallet_address: string;
  custody_type: string | null;
  party_id: string | null;
  authorized: boolean;
  authorized_until: string | null;
  authorized_by: string | null;
  approved_by: string | null;
};

export default function OnboardingConsolePage() {
  const [credential, setCredential] = useState("");
  const [walletAddress, setWalletAddress] = useState("");
  const [blockchain, setBlockchain] = useState("ETHEREUM");
  const [custodyType, setCustodyType] = useState("UNHOSTED");
  const [partyId, setPartyId] = useState("");
  const [challenge, setChallenge] = useState<string | null>(null);
  const [signature, setSignature] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const refreshWallets = useCallback(async () => {
    try {
      const data = await api.onboarding.listWallets(false);
      setWallets((data.wallets || []) as Wallet[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to list wallets");
    }
  }, []);

  useEffect(() => {
    refreshWallets();
  }, [refreshWallets]);

  async function handleVerifyCredential(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setIsLoading(true);
    try {
      const result = await api.onboarding.verifyCredential(credential, true);
      setPartyId(result.party_id || "");
      setMessage(
        result.status === "verified"
          ? `Credential verified — party ${result.party_id} recorded.`
          : `Credential rejected: ${JSON.stringify(result.verdict)}`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleIssueChallenge() {
    setError(null);
    setMessage(null);
    setIsLoading(true);
    try {
      const result = await api.onboarding.challenge(walletAddress, blockchain);
      setChallenge(result.challenge);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Challenge failed");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleRegisterWallet(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setIsLoading(true);
    try {
      const result = await api.onboarding.registerWallet({
        party_id: partyId,
        blockchain,
        wallet_address: walletAddress,
        custody_type: custodyType || null,
        challenge: challenge ?? undefined,
        signature: signature || undefined,
      });
      setMessage(`${result.note || "Registered"} — awaiting checker approval.`);
      setChallenge(null);
      setSignature("");
      await refreshWallets();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleApprove(instrumentId: string) {
    setError(null);
    try {
      await api.onboarding.approveWallet(instrumentId);
      await refreshWallets();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval failed");
    }
  }

  async function handleRevoke(instrumentId: string) {
    setError(null);
    try {
      await api.onboarding.revokeWallet(instrumentId);
      await refreshWallets();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Revoke failed");
    }
  }

  const masked = (value: string) =>
    value && value.length > 10 ? `${value.slice(0, 6)}…${value.slice(-4)}` : value;

  return (
    <main className="min-h-screen bg-slate-950 p-8 text-slate-100">
      <div className="mx-auto max-w-5xl">
        <h1 className="mb-6 text-2xl font-semibold">Authorized-Wallet Onboarding</h1>

        {error && (
          <p role="alert" aria-live="assertive" className="mb-4 rounded-lg border border-red-900 bg-red-950 px-4 py-2 text-red-300">
            {error}
          </p>
        )}
        {message && (
          <p role="status" aria-live="polite" className="mb-4 rounded-lg border border-emerald-900 bg-emerald-950 px-4 py-2 text-emerald-300">
            {message}
          </p>
        )}

        <section className="mb-6 rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="mb-3 text-lg font-medium">1 · Verify KYC/KYB credential</h2>
          <form onSubmit={handleVerifyCredential} className="flex flex-col gap-3">
            <textarea
              value={credential}
              onChange={(e) => setCredential(e.target.value)}
              placeholder="Paste the SD-JWT credential…"
              required
              rows={4}
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-xs outline-none focus:border-sky-500"
            />
            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={isLoading || credential.length < 20}
                className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium hover:bg-sky-500 disabled:opacity-50"
              >
                {isLoading ? "Verifying…" : "Verify"}
              </button>
              {partyId && (
                <span className="text-xs text-slate-400">
                  Party: <span className="font-mono text-emerald-400">{partyId}</span>
                </span>
              )}
            </div>
          </form>
        </section>

        <section className="mb-6 rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="mb-3 text-lg font-medium">2 · Register wallet (address-control proof)</h2>
          <form onSubmit={handleRegisterWallet} className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-3">
              <input
                value={walletAddress}
                onChange={(e) => setWalletAddress(e.target.value)}
                placeholder="Wallet address (0x… / base58)"
                required
                className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-xs outline-none focus:border-sky-500"
              />
              <select
                value={blockchain}
                onChange={(e) => setBlockchain(e.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none"
              >
                <option value="ETHEREUM">Ethereum / EVM</option>
                <option value="SOLANA">Solana</option>
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <select
                value={custodyType}
                onChange={(e) => setCustodyType(e.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none"
              >
                <option value="HOSTED">Hosted</option>
                <option value="UNHOSTED">Unhosted</option>
                <option value="EXCHANGE_CUSTODIED">Exchange-custodied</option>
                <option value="MULTI_SIG">Multi-sig</option>
              </select>
              <button
                type="button"
                onClick={handleIssueChallenge}
                disabled={isLoading || walletAddress.length < 8}
                className="rounded-lg border border-slate-600 px-3 py-2 text-sm hover:bg-slate-800 disabled:opacity-50"
              >
                {challenge ? "Re-issue challenge" : "Issue challenge"}
              </button>
            </div>
            {challenge && (
              <div className="rounded-lg border border-amber-900 bg-amber-950/40 p-3">
                <p className="mb-1 text-xs text-amber-300">
                  Have the applicant sign this message with the wallet key (EIP-191 / Ed25519):
                </p>
                <code className="block break-all font-mono text-[11px] text-amber-100">
                  {challenge}
                </code>
              </div>
            )}
            <input
              value={signature}
              onChange={(e) => setSignature(e.target.value)}
              placeholder="Signature hex / base58 from the wallet"
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 font-mono text-xs outline-none focus:border-sky-500"
            />
            <button
              type="submit"
              disabled={isLoading || !partyId || !challenge || !signature}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
            >
              Register (maker)
            </button>
            {!partyId && (
              <p className="text-xs text-slate-500">Verify a credential first to obtain the party id.</p>
            )}
          </form>
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="mb-3 text-lg font-medium">3 · Authorizations (maker-checker)</h2>
          {wallets.length === 0 ? (
            <p className="text-sm text-slate-500">No wallets registered yet.</p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-700 text-slate-400">
                  <th className="pb-2">Wallet (masked)</th>
                  <th className="pb-2">Chain</th>
                  <th className="pb-2">Party</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2">Valid until</th>
                  <th className="pb-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {wallets.map((wallet) => (
                  <tr key={wallet.instrument_id} className="border-b border-slate-800">
                    <td className="py-2 font-mono text-xs">{masked(wallet.wallet_address)}</td>
                    <td className="py-2">{wallet.blockchain}</td>
                    <td className="py-2 font-mono text-xs">{wallet.party_id || "—"}</td>
                    <td className="py-2">
                      {wallet.authorized ? (
                        <span className="text-emerald-400">Authorized</span>
                      ) : wallet.approved_by === null && wallet.authorized_by ? (
                        <span className="text-amber-400">Awaiting checker</span>
                      ) : (
                        <span className="text-slate-400">Not authorized</span>
                      )}
                    </td>
                    <td className="py-2 text-xs">
                      {wallet.authorized_until ? wallet.authorized_until.slice(0, 10) : "—"}
                    </td>
                    <td className="py-2">
                      {!wallet.authorized && wallet.authorized_by ? (
                        <button
                          onClick={() => handleApprove(wallet.instrument_id)}
                          className="mr-2 rounded bg-emerald-700 px-2 py-1 text-xs hover:bg-emerald-600"
                        >
                          Approve
                        </button>
                      ) : null}
                      {wallet.authorized ? (
                        <button
                          onClick={() => handleRevoke(wallet.instrument_id)}
                          className="rounded bg-red-800 px-2 py-1 text-xs hover:bg-red-700"
                        >
                          Revoke
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </main>
  );
}
