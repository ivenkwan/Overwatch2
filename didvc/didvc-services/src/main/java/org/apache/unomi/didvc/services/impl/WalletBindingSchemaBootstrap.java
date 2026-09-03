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
import org.osgi.service.component.annotations.Activate;
import org.osgi.service.component.annotations.Component;
import org.osgi.service.component.annotations.Reference;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Wallet binding schema (AWI TASK-043, ADR-0002): {@code hkt_wallet_binding_v1}
 * binds a subject DID to a hashed on-chain wallet address for AML
 * authorized-wallet onboarding. The binding surface is deliberately minimal —
 * a SHA-256 address hash (never the plaintext address), chain, custody type,
 * binding level and validity — mirroring the agent-binding pattern: key
 * hashes and levels, no principal PII. The AML platform verifies this
 * credential through the M2M path and refreshes it nightly.
 */
@Component(service = WalletBindingSchemaBootstrap.class, immediate = true)
public class WalletBindingSchemaBootstrap {

    private static final Logger LOGGER = LoggerFactory.getLogger(WalletBindingSchemaBootstrap.class);

    @Reference
    private CredentialSchemaService schemaService;

    public void setSchemaService(CredentialSchemaService schemaService) {
        this.schemaService = schemaService;
    }

    @Activate
    public void activate() {
        if (schemaService.getSchema("hkt-wallet-binding-v1") != null) {
            return;
        }
        DidSchema schema = new DidSchema("hkt-wallet-binding-v1");
        schema.setName("Wallet binding credential");
        schema.setVct("hkt_wallet_binding_v1");
        schema.setDescription("Binds a hashed on-chain wallet address to an HKT-verified "
                + "principal for AML authorized-wallet onboarding (ADR-0002). Carries an "
                + "address hash — never a plaintext address — plus chain, custody type, "
                + "binding level and validity.");
        schema.setAllowedClaims(new HashSet<>(Arrays.asList(
                "walletAddressHash", "blockchain", "custodyType",
                "bindingLevel", "validUntil", "vaspLicenseRef", "jurisdiction", "proofRef")));
        schema.setRequiredClaims(new HashSet<>(Arrays.asList(
                "walletAddressHash", "blockchain", "custodyType", "bindingLevel", "validUntil")));
        Map<String, String> claimTypes = new LinkedHashMap<>();
        claimTypes.put("walletAddressHash", "string");
        claimTypes.put("blockchain", "string");
        claimTypes.put("custodyType", "string");
        claimTypes.put("bindingLevel", "string");
        claimTypes.put("validUntil", "string");
        claimTypes.put("vaspLicenseRef", "string");
        claimTypes.put("jurisdiction", "string");
        claimTypes.put("proofRef", "string");
        schema.setClaimTypes(claimTypes);
        schema.setScope("didvc");
        schemaService.saveSchema(schema);
        LOGGER.info("Bootstrapped wallet binding schema hkt-wallet-binding-v1 (vct={})", schema.getVct());
    }
}
