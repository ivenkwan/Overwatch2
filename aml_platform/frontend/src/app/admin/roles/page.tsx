"use client";

import { useEffect, useState } from "react";
import { API_URL } from "@/config";

interface Role {
  role_id: string;
  role_code: string;
  role_name: string;
  description: string;
}

export default function RolesManagementPage() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchRoles = async () => {
    try {
      const res = await fetch(`${API_URL}/admin/roles`);
      const data = await res.json();
      if (data.status === "success") setRoles(data.roles);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRoles();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold font-mono">Role & Access Builder</h2>
          <p className="text-gray-400 mt-1">Configure module-level permissions for pre-defined tenant roles.</p>
        </div>
        <button className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-md transition font-medium text-sm shadow-sm opacity-90 hover:opacity-100">
          + Create Custom Role
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 bg-gray-800 rounded-lg border border-gray-700 overflow-hidden flex flex-col h-[600px]">
          <div className="p-4 bg-gray-900/50 border-b border-gray-700">
            <h3 className="font-medium text-sm text-gray-300 uppercase tracking-wider">Tenant Roles</h3>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {loading ? (
              <div className="p-4 text-center text-sm text-gray-500">Loading roles...</div>
            ) : roles.length === 0 ? (
              <div className="p-4 text-center text-sm text-gray-500">No roles configured.</div>
            ) : (
              roles.map(r => (
                <div key={r.role_id} className="p-3 rounded-md cursor-pointer hover:bg-gray-700 transition border border-transparent hover:border-gray-600 group">
                  <div className="font-medium text-gray-200 group-hover:text-blue-400 transition">{r.role_name}</div>
                  <div className="text-xs text-gray-500 mt-1">{r.description || r.role_code}</div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="lg:col-span-2 bg-gray-800 rounded-lg border border-gray-700 overflow-hidden flex flex-col h-[600px]">
           <div className="p-4 bg-gray-900/50 border-b border-gray-700 flex justify-between items-center">
            <h3 className="font-medium text-sm text-gray-300 uppercase tracking-wider">Module Capabilities</h3>
            <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded">Select a role</span>
          </div>
          <div className="flex-1 p-8 flex items-center justify-center text-gray-500 text-center">
            <div>
              <svg className="w-12 h-12 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
              <p>Select a role from the left pane to view its module capabilities.</p>
              <p className="text-sm mt-2 opacity-75">Changes to access levels are synced automatically to Keycloak assertions via the Platform Engine.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
