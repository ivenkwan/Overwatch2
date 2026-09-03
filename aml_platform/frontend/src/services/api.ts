/**
 * Platform API client (httpOnly-cookie session).
 *
 * Authentication uses the `aml_session` httpOnly cookie set by
 * POST /api/v1/auth/login — JavaScript never touches the token, so there is
 * no token in localStorage and no Authorization header in this file. Every
 * request carries `credentials: "include"` for the cross-origin dev setup.
 *
 * The API base is a fully literal URL per the repository's security-gate
 * policy on browser fetch targets; change it here when the API origin
 * moves.
 */
const API_BASE_URL = "http://127.0.0.1:8000/api/v1";

/** Redirect to /login when the session is gone (401). */
function handleUnauthorized(res: Response): Response {
  if (
    res.status === 401 &&
    typeof window !== "undefined" &&
    !window.location.pathname.startsWith("/login")
  ) {
    window.location.href = "/login";
  }
  return res;
}

export const api = {
  auth: {
    /** Sign in: the server sets the httpOnly session cookie. */
    async login(username: string, password: string): Promise<void> {
      const res = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username, password }),
      });
      if (res.status === 401) throw new Error("Incorrect username or password");
      if (!res.ok) throw new Error("Login failed");
    },

    /** Sign out: clears the session cookie. */
    async logout(): Promise<void> {
      const res = await fetch(`${API_BASE_URL}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) throw new Error("Logout failed");
    },
  },

  async fetchFeed() {
    const res = handleUnauthorized(
      await fetch(`${API_BASE_URL}/alerts/feed`, {
        method: "GET",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      })
    );
    if (!res.ok) throw new Error("Failed to fetch monitoring feed");
    return res.json();
  },

  async fetchGraphNetwork() {
    const res = handleUnauthorized(
      await fetch(`${API_BASE_URL}/graph/network`, {
        method: "GET",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      })
    );
    if (!res.ok) throw new Error("Failed to fetch graph network");
    return res.json();
  },

  async fetchGraphNeighborhood(entityId: string, depth: number = 2) {
    const res = handleUnauthorized(
      await fetch(`${API_BASE_URL}/graph/explore/${encodeURIComponent(entityId)}?depth=${depth}`, {
        method: "GET",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      })
    );
    if (!res.ok) throw new Error("Failed to fetch entity neighborhood");
    return res.json();
  },

  alerts: {
    async fetchAll(status: string = 'OPEN', limit: number = 100) {
      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/alerts/?status=${status}&limit=${limit}`, {
          method: "GET",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        })
      );
      if (!res.ok) throw new Error("Failed to fetch alerts");
      return res.json();
    },

    async assign(alertId: string) {
      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/alerts/${encodeURIComponent(alertId)}/assign`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        })
      );
      if (!res.ok) throw new Error("Failed to assign alert");
      return res.json();
    },

    async proposeClose(alertId: string, notes: string) {
      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/alerts/${encodeURIComponent(alertId)}/propose-close?notes=${encodeURIComponent(notes)}`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        })
      );
      if (!res.ok) throw new Error("Failed to propose alert closure");
      return res.json();
    },

    async approve(alertId: string) {
      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/alerts/${encodeURIComponent(alertId)}/approve`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        })
      );
      if (!res.ok) throw new Error("Failed to approve alert");
      return res.json();
    },

    async reject(alertId: string, notes: string) {
      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/alerts/${encodeURIComponent(alertId)}/reject?notes=${encodeURIComponent(notes)}`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        })
      );
      if (!res.ok) throw new Error("Failed to reject alert");
      return res.json();
    },
  },

  cases: {
    async fetchAll() {
      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/cases/`, {
          method: "GET",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        })
      );
      if (!res.ok) throw new Error("Failed to fetch cases");
      return res.json();
    },

    async fetchOne(caseId: string) {
      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}`, {
          method: "GET",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        })
      );
      if (!res.ok) throw new Error("Failed to fetch case detail");
      return res.json();
    },

    async create(alertId: string) {
      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/cases/`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ alert_id: alertId }),
        })
      );
      if (!res.ok) throw new Error("Failed to create case");
      return res.json();
    },

    async submitAction(caseId: string, action: string, notes?: string) {
      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/action`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action, notes }),
        })
      );
      if (!res.ok) throw new Error("Failed to submit action on case");
      return res.json();
    },
  },

  reports: {
    async getDailyKPIs() {
      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/reports/kpis`, {
          method: "GET",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        })
      );
      if (!res.ok) throw new Error("Failed to fetch daily KPIs");
      return res.json();
    },
  },

  strs: {
    async fetchAll() {
      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/str/`, {
          method: "GET",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        })
      );
      if (!res.ok) throw new Error("Failed to fetch STRs");
      return res.json();
    },

    async fetchOne(strId: string) {
      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/str/${encodeURIComponent(strId)}`, {
          method: "GET",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        })
      );
      if (!res.ok) throw new Error("Failed to fetch STR detail");
      return res.json();
    },

    async create(caseId?: string) {
      const body: any = {};
      if (caseId) body.case_id = caseId;

      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/str/`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        })
      );
      if (!res.ok) throw new Error("Failed to create STR");
      return res.json();
    },

    async update(strId: string, payload: {
      case_id?: string;
      triggering_factors?: string;
      subject_background?: string;
      digital_footprints?: string;
      transaction_summary?: string;
    }) {
      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/str/${encodeURIComponent(strId)}`, {
          method: "PUT",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        })
      );
      if (!res.ok) throw new Error("Failed to update STR");
      return res.json();
    },

    async submit(strId: string) {
      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/str/${encodeURIComponent(strId)}/submit`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        })
      );
      if (!res.ok) throw new Error("Failed to submit STR to JFIU");
      return res.json();
    },
  },

  onboarding: {
    /** Issue a single-use address-control challenge. */
    async challenge(walletAddress: string, blockchain: string = "ETHEREUM") {
      const res = handleUnauthorized(
        await fetch(
          `${API_BASE_URL}/onboarding/challenge?wallet_address=${encodeURIComponent(walletAddress)}&blockchain=${encodeURIComponent(blockchain)}`,
          { method: "GET", credentials: "include" }
        )
      );
      if (!res.ok) throw new Error("Failed to issue challenge");
      return res.json();
    },

    /** Verify a KYC/KYB credential against the identity provider. */
    async verifyCredential(credential: string, includeClaims: boolean = false) {
      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/onboarding/verify`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ credential, include_claims: includeClaims }),
        })
      );
      if (!res.ok) throw new Error("Failed to verify credential");
      return res.json();
    },

    /** Register a wallet authorization (maker step). */
    async registerWallet(payload: Record<string, unknown>) {
      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/onboarding/wallets`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        })
      );
      if (!res.ok) throw new Error("Failed to register wallet");
      return res.json();
    },

    /** Approve a proposed authorization (checker step). */
    async approveWallet(instrumentId: string) {
      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/onboarding/wallets/${encodeURIComponent(instrumentId)}/approve`, {
          method: "POST",
          credentials: "include",
        })
      );
      if (!res.ok) throw new Error("Failed to approve wallet");
      return res.json();
    },

    /** Revoke an authorization. */
    async revokeWallet(instrumentId: string) {
      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/onboarding/wallets/${encodeURIComponent(instrumentId)}/revoke`, {
          method: "POST",
          credentials: "include",
        })
      );
      if (!res.ok) throw new Error("Failed to revoke wallet");
      return res.json();
    },

    /** List wallet authorizations (masked per role server-side). */
    async listWallets(onlyAuthorized: boolean = false) {
      const res = handleUnauthorized(
        await fetch(`${API_BASE_URL}/onboarding/wallets?only_authorized=${onlyAuthorized}`, {
          method: "GET",
          credentials: "include",
        })
      );
      if (!res.ok) throw new Error("Failed to list wallets");
      return res.json();
    },
  },
};
