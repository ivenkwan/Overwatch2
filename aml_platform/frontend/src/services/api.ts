const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export const api = {
  async fetchFeed() {
    const res = await fetch(`${API_BASE_URL}/alerts/feed`, {
      method: "GET",
      headers: { "Content-Type": "application/json" }
    });
    if (!res.ok) throw new Error("Failed to fetch monitoring feed");
    return res.json();
  },

  async fetchGraphNetwork() {
    const res = await fetch(`${API_BASE_URL}/graph/network`, {
      method: "GET",
      headers: { "Content-Type": "application/json" }
    });
    if (!res.ok) throw new Error("Failed to fetch graph network");
    return res.json();
  },

  async fetchGraphNeighborhood(entityId: string, depth: number = 2) {
    const res = await fetch(`${API_BASE_URL}/graph/explore/${encodeURIComponent(entityId)}?depth=${depth}`, {
      method: "GET",
      headers: { 
        "Content-Type": "application/json",
      }
    });
    if (!res.ok) throw new Error("Failed to fetch entity neighborhood");
    return res.json();
  },

  alerts: {
    async fetchAll(status: string = 'OPEN', limit: number = 100) {
      const res = await fetch(`${API_BASE_URL}/alerts/?status=${status}&limit=${limit}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      });
      if (!res.ok) throw new Error("Failed to fetch alerts");
      return res.json();
    },

    async assign(alertId: string) {
      const res = await fetch(`${API_BASE_URL}/alerts/${encodeURIComponent(alertId)}/assign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      if (!res.ok) throw new Error("Failed to assign alert");
      return res.json();
    },

    async proposeClose(alertId: string, notes: string) {
      const res = await fetch(`${API_BASE_URL}/alerts/${encodeURIComponent(alertId)}/propose-close?notes=${encodeURIComponent(notes)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      if (!res.ok) throw new Error("Failed to propose alert closure");
      return res.json();
    },

    async approve(alertId: string) {
      const res = await fetch(`${API_BASE_URL}/alerts/${encodeURIComponent(alertId)}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      if (!res.ok) throw new Error("Failed to approve alert");
      return res.json();
    },

    async reject(alertId: string, notes: string) {
      const res = await fetch(`${API_BASE_URL}/alerts/${encodeURIComponent(alertId)}/reject?notes=${encodeURIComponent(notes)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      if (!res.ok) throw new Error("Failed to reject alert");
      return res.json();
    }
  },

  cases: {
    async fetchAll() {
      const res = await fetch(`${API_BASE_URL}/cases/`, {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      });
      if (!res.ok) throw new Error("Failed to fetch cases");
      return res.json();
    },

    async fetchOne(caseId: string) {
      const res = await fetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      });
      if (!res.ok) throw new Error("Failed to fetch case detail");
      return res.json();
    },

    async create(alertId: string) {
      const res = await fetch(`${API_BASE_URL}/cases/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ alert_id: alertId })
      });
      if (!res.ok) throw new Error("Failed to create case");
      return res.json();
    },

    async submitAction(caseId: string, action: string, notes?: string) {
      const res = await fetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, notes })
      });
      if (!res.ok) throw new Error("Failed to submit action on case");
      return res.json();
    }
  },

  reports: {
    async getDailyKPIs() {
      const res = await fetch(`${API_BASE_URL}/reports/kpis`, {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      });
      if (!res.ok) throw new Error("Failed to fetch daily KPIs");
      return res.json();
    }
  },

  strs: {
    async fetchAll() {
      const res = await fetch(`${API_BASE_URL}/str/`, {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      });
      if (!res.ok) throw new Error("Failed to fetch STRs");
      return res.json();
    },

    async fetchOne(strId: string) {
      const res = await fetch(`${API_BASE_URL}/str/${encodeURIComponent(strId)}`, {
        method: "GET",
        headers: { "Content-Type": "application/json" }
      });
      if (!res.ok) throw new Error("Failed to fetch STR detail");
      return res.json();
    },

    async create(caseId?: string) {
      const body: any = {};
      if (caseId) body.case_id = caseId;
      
      const res = await fetch(`${API_BASE_URL}/str/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
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
      const res = await fetch(`${API_BASE_URL}/str/${encodeURIComponent(strId)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Failed to update STR");
      return res.json();
    },

    async submit(strId: string) {
      const res = await fetch(`${API_BASE_URL}/str/${encodeURIComponent(strId)}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      if (!res.ok) throw new Error("Failed to submit STR to JFIU");
      return res.json();
    }
  }
};
