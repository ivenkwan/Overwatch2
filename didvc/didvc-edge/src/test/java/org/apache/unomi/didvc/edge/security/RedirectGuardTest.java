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

package org.apache.unomi.didvc.edge.security;

import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Regression tests for the F-7 / F-9 / F-12 hardening helpers.
 */
class RedirectGuardTest {

    private static final List<String> WALLET_ALLOWLIST = Arrays.asList(
            "https://wallet.example.com/authorize",
            "https://other.example.org/authorize");

    private static final List<String> CLIENT_REDIRECT_ALLOWLIST = Arrays.asList(
            "aml-portal|https://portal.example.com/callback",
            "conformance-suite|https://suite.example.org/callback");

    // ---------------------------------------------------------------- F-12 / F-7 URI matching

    @Test
    void exactUriMatchAllowed() {
        assertTrue(RedirectGuard.uriAllowed("https://wallet.example.com/authorize", WALLET_ALLOWLIST));
    }

    @Test
    void normalizationApplies() {
        assertTrue(RedirectGuard.uriAllowed("HTTPS://WALLET.EXAMPLE.COM:443/authorize", WALLET_ALLOWLIST));
    }

    @Test
    void substringAndPrefixNeverMatch() {
        assertFalse(RedirectGuard.uriAllowed("https://wallet.example.com/authorize/extra", WALLET_ALLOWLIST));
        assertFalse(RedirectGuard.uriAllowed("https://wallet.example.com", WALLET_ALLOWLIST));
        assertFalse(RedirectGuard.uriAllowed("https://evil.example.com/authorize?url=wallet.example.com",
                WALLET_ALLOWLIST));
    }

    @Test
    void differentHostRejected() {
        assertFalse(RedirectGuard.uriAllowed("https://wallet.example.com.evil.io/authorize", WALLET_ALLOWLIST));
    }

    @Test
    void emptyAllowlistDeniesUri() {
        assertFalse(RedirectGuard.uriAllowed("https://wallet.example.com/authorize", Collections.emptyList()));
        assertTrue(RedirectGuard.allowlistUnconfigured(Collections.emptyList()));
    }

    // ---------------------------------------------------------------- F-7 client registry

    @Test
    void clientRedirectPairMatchAllowed() {
        assertTrue(RedirectGuard.clientRedirectAllowed(
                "aml-portal", "https://portal.example.com/callback", CLIENT_REDIRECT_ALLOWLIST));
    }

    @Test
    void wrongClientRejectedEvenWithAllowedRedirect() {
        assertFalse(RedirectGuard.clientRedirectAllowed(
                "evil-client", "https://portal.example.com/callback", CLIENT_REDIRECT_ALLOWLIST));
    }

    @Test
    void wrongRedirectRejectedEvenWithAllowedClient() {
        assertFalse(RedirectGuard.clientRedirectAllowed(
                "aml-portal", "https://portal.example.com/evil", CLIENT_REDIRECT_ALLOWLIST));
    }

    // ---------------------------------------------------------------- F-9 constant-time keys

    @Test
    void apiKeyExactMatch() {
        assertTrue(RedirectGuard.apiKeyMatches("secret-value-123456", "secret-value-123456"));
    }

    @Test
    void apiKeyMismatchAndDegenerateCases() {
        assertFalse(RedirectGuard.apiKeyMatches("secret-value-123456", "secret-value-123457"));
        assertFalse(RedirectGuard.apiKeyMatches("", "anything"));
        assertFalse(RedirectGuard.apiKeyMatches(null, "anything"));
        assertFalse(RedirectGuard.apiKeyMatches("expected", null));
        assertFalse(RedirectGuard.apiKeyMatches("expected", ""));
    }
}
