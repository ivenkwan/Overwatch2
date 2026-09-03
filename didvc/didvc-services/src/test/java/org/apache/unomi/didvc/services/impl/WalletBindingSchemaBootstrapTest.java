/*
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.apache.unomi.didvc.services.impl;

import org.apache.unomi.didvc.api.items.DidSchema;
import org.apache.unomi.didvc.api.services.CredentialSchemaService;
import org.apache.unomi.didvc.services.MockPersistence;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Wallet binding schema bootstrap (AWI TASK-043): registers
 * {@code hkt_wallet_binding_v1} exactly once, with a minimized whitelist
 * that rejects plaintext wallet addresses and raw PII.
 */
class WalletBindingSchemaBootstrapTest {

    private CredentialSchemaServiceImpl bootstrapped() {
        CredentialSchemaServiceImpl schemaService = new CredentialSchemaServiceImpl();
        schemaService.setPersistenceService(MockPersistence.create());
        WalletBindingSchemaBootstrap bootstrap = new WalletBindingSchemaBootstrap();
        bootstrap.setSchemaService(schemaService);
        bootstrap.activate();
        return schemaService;
    }

    @Test
    void registersSchemaOnActivation() {
        CredentialSchemaService schemaService = bootstrapped();
        DidSchema schema = schemaService.getSchema("hkt-wallet-binding-v1");
        assertNotNull(schema);
        assertEquals("hkt_wallet_binding_v1", schema.getVct());
        assertTrue(schema.getAllowedClaims().contains("walletAddressHash"));
        assertTrue(schema.getAllowedClaims().contains("blockchain"));
        assertTrue(schema.getAllowedClaims().contains("custodyType"));
        assertTrue(schema.getRequiredClaims().contains("walletAddressHash"));
        assertTrue(schema.getRequiredClaims().contains("validUntil"));
        assertEquals("string", schema.getClaimTypes().get("walletAddressHash"));
    }

    @Test
    void activationIsIdempotent() {
        CredentialSchemaServiceImpl schemaService = new CredentialSchemaServiceImpl();
        schemaService.setPersistenceService(MockPersistence.create());
        WalletBindingSchemaBootstrap bootstrap = new WalletBindingSchemaBootstrap();
        bootstrap.setSchemaService(schemaService);
        bootstrap.activate();
        bootstrap.activate();
        assertEquals(1, schemaService.getSchemas(null).size());
    }

    @Test
    void whitelistRejectsPlaintextAddressAndPii() {
        CredentialSchemaService schemaService = bootstrapped();
        java.util.Map<String, Object> claims = new java.util.HashMap<>();
        claims.put("walletAddressHash", "a3f5".repeat(16));
        claims.put("blockchain", "ETHEREUM");
        claims.put("custodyType", "UNHOSTED");
        claims.put("bindingLevel", "ADDRESS_PROOF_VERIFIED");
        claims.put("validUntil", "2027-01-01T00:00:00Z");
        claims.put("walletAddress", "0xAbCdEf1234567890"); // plaintext address — not whitelisted
        assertThrows(IllegalArgumentException.class,
                () -> schemaService.validateClaims(schemaService.getSchema("hkt-wallet-binding-v1"), claims));
    }

    @Test
    void whitelistRejectsMissingRequiredClaims() {
        CredentialSchemaService schemaService = bootstrapped();
        java.util.Map<String, Object> claims = new java.util.HashMap<>();
        claims.put("walletAddressHash", "a3f5".repeat(16));
        claims.put("blockchain", "ETHEREUM");
        // custodyType / bindingLevel / validUntil missing
        assertThrows(IllegalArgumentException.class,
                () -> schemaService.validateClaims(schemaService.getSchema("hkt-wallet-binding-v1"), claims));
    }
}
