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

import java.net.URI;
import java.security.MessageDigest;
import java.util.List;

/**
 * Redirect / API-key hardening helpers closing security-review findings
 * F-7, F-9 and F-12:
 *
 * <ul>
 *   <li>F-7 — {@code /authorize} and {@code /par} previously accepted any
 *       {@code client_id}/{@code redirect_uri}. When an allowlist is
 *       configured, both must now match an exact {@code clientId|redirectUri}
 *       pair (RFC 6749 §3.1.2.3 exact-match semantics). An empty allowlist
 *       keeps the demo/conformance behaviour (logged at startup).</li>
 *   <li>F-9 — API keys are compared with constant-time equality.</li>
 *   <li>F-12 — browser redirects to a caller-supplied
 *       {@code wallet_authorization_endpoint} require an exact match against
 *       the configured wallet endpoint allowlist when one is present.</li>
 * </ul>
 *
 * Allowlists are configuration/environment-supplied only
 * (e.g. {@code DIDVC_EDGE_REDIRECTURIALLOWLIST_0}) — never source literals.
 */
public final class RedirectGuard {

    private RedirectGuard() {
    }

    /**
     * Exact-match URI comparison after normalization (lowercase scheme and
     * host; default ports dropped; no userinfo; trailing slash on the path
     * is significant). No substring or prefix matching — ever.
     */
    public static boolean uriAllowed(String candidate, List<String> allowlist) {
        if (allowlist == null || allowlist.isEmpty()) {
            return false;
        }
        String normalized = normalizeUri(candidate);
        if (normalized == null) {
            return false;
        }
        for (String allowed : allowlist) {
            String normalizedAllowed = normalizeUri(allowed);
            if (normalized.equals(normalizedAllowed)) {
                return true;
            }
        }
        return false;
    }

    /**
     * F-7 client-registry check: the allowlist holds
     * {@code clientId|redirectUri} entries; both must match exactly.
     */
    public static boolean clientRedirectAllowed(String clientId, String redirectUri, List<String> allowlist) {
        if (allowlist == null || allowlist.isEmpty() || clientId == null || redirectUri == null) {
            return false;
        }
        String normalizedRedirect = normalizeUri(redirectUri);
        for (String entry : allowlist) {
            int separator = entry.indexOf('|');
            if (separator <= 0 || separator == entry.length() - 1) {
                continue;
            }
            String allowedClient = entry.substring(0, separator);
            String allowedRedirect = normalizeUri(entry.substring(separator + 1));
            if (normalizedRedirect != null
                    && clientId.equals(allowedClient)
                    && normalizedRedirect.equals(allowedRedirect)) {
                return true;
            }
        }
        return false;
    }

    /**
     * F-9: constant-time API key comparison. Returns false for null/empty
     * expected keys rather than opening the endpoint.
     */
    public static boolean apiKeyMatches(String expected, String provided) {
        if (expected == null || expected.isEmpty() || provided == null || provided.isEmpty()) {
            return false;
        }
        return MessageDigest.isEqual(
                expected.getBytes(java.nio.charset.StandardCharsets.UTF_8),
                provided.getBytes(java.nio.charset.StandardCharsets.UTF_8));
    }

    /** True when no allowlist is configured (demo/conformance mode). */
    public static boolean allowlistUnconfigured(List<String> allowlist) {
        return allowlist == null || allowlist.isEmpty();
    }

    private static String normalizeUri(String value) {
        if (value == null || value.isEmpty()) {
            return null;
        }
        try {
            URI uri = URI.create(value.trim());
            if (uri.getScheme() == null || uri.getHost() == null) {
                return null;
            }
            String scheme = uri.getScheme().toLowerCase();
            String host = uri.getHost().toLowerCase();
            int port = uri.getPort();
            if ((scheme.equals("http") && port == 80) || (scheme.equals("https") && port == 443)) {
                port = -1;
            }
            String path = uri.getPath() == null ? "" : uri.getPath();
            StringBuilder normalized = new StringBuilder(scheme).append("://").append(host);
            if (port != -1) {
                normalized.append(':').append(port);
            }
            return normalized.append(path).toString();
        } catch (IllegalArgumentException e) {
            return null;
        }
    }
}
