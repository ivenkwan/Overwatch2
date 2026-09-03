"use client";

import { useEffect, useState } from "react";
import { API_URL } from "@/config";

interface User {
  user_id: string;
  username: string;
  email: string;
  full_name: string;
  status: string;
  joined_at: string;
}

export default function UserManagementPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Create user form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [newUser, setNewUser] = useState({ username: '', email: '', first_name: '', last_name: '', password: '' });
  const [submitError, setSubmitError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Default hardcoded tenant ID simulating the logged-in admin's context
  const TENANT_ID = "00000000-0000-0000-0000-000000000000";

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/admin/users`, {
        headers: { "X-Tenant-ID": TENANT_ID }
      });
      const data = await res.json();
      if (data.status === "success") {
        setUsers(data.users);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitError("");
    
    try {
      const res = await fetch(`${API_URL}/admin/users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': TENANT_ID
        },
        body: JSON.stringify(newUser)
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to provision user");
      
      setShowAddForm(false);
      setNewUser({ username: '', email: '', first_name: '', last_name: '', password: '' });
      fetchUsers(); // refresh the list
    } catch (err: any) {
      setSubmitError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold font-mono">User Management</h2>
          <p className="text-gray-400 mt-1">Provision identities in Keycloak and map tenant roles.</p>
        </div>
        <button 
          onClick={() => setShowAddForm(!showAddForm)}
          className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-md transition font-medium text-sm shadow-sm opacity-90 hover:opacity-100"
        >
          + Provision New User
        </button>
      </div>

      {showAddForm && (
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 shadow-xl mb-8">
          <h3 className="text-lg font-medium border-b border-gray-700 pb-2 mb-4">Provision Keycloak Identity</h3>
          
          {submitError && (
             <div className="mb-4 bg-red-900/50 border border-red-500 text-red-200 px-4 py-2 rounded text-sm">
                {submitError}
             </div>
          )}

          <form onSubmit={handleCreateUser} className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Username</label>
              <input required type="text" value={newUser.username} onChange={e => setNewUser({...newUser, username: e.target.value})} className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm focus:border-blue-500 outline-none" placeholder="jdoe" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Email</label>
              <input required type="email" value={newUser.email} onChange={e => setNewUser({...newUser, email: e.target.value})} className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm focus:border-blue-500 outline-none" placeholder="jdoe@example.com" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">First Name</label>
              <input type="text" value={newUser.first_name} onChange={e => setNewUser({...newUser, first_name: e.target.value})} className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm focus:border-blue-500 outline-none" placeholder="John" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Last Name</label>
              <input type="text" value={newUser.last_name} onChange={e => setNewUser({...newUser, last_name: e.target.value})} className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm focus:border-blue-500 outline-none" placeholder="Doe" />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-gray-400 mb-1">Initial Password (Keycloak)</label>
              <input required type="password" value={newUser.password} onChange={e => setNewUser({...newUser, password: e.target.value})} className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm focus:border-blue-500 outline-none" placeholder="••••••••" />
            </div>
            <div className="col-span-2 flex justify-end gap-2 mt-2">
              <button type="button" onClick={() => setShowAddForm(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white">Cancel</button>
              <button disabled={isSubmitting} type="submit" className="px-4 py-2 text-sm bg-green-600 hover:bg-green-500 text-white rounded font-medium disabled:opacity-50">
                {isSubmitting ? 'Provisioning...' : 'Provision & Sync mapping'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Users Table */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-900/50 text-xs uppercase tracking-wider text-gray-400 border-b border-gray-700">
              <th className="p-4 font-medium">User</th>
              <th className="p-4 font-medium">Identity Auth</th>
              <th className="p-4 font-medium">Name</th>
              <th className="p-4 font-medium">Status</th>
              <th className="p-4 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700/50">
            {loading ? (
              <tr><td colSpan={5} className="p-8 text-center text-gray-500">Loading directory...</td></tr>
            ) : users.length === 0 ? (
              <tr><td colSpan={5} className="p-8 text-center text-gray-500">No users found in this tenant.</td></tr>
            ) : (
              users.map(u => (
                <tr key={u.user_id} className="hover:bg-gray-700/20 transition group">
                  <td className="p-4">
                    <div className="font-medium text-gray-200">{u.username}</div>
                    <div className="text-xs text-gray-500">{u.email}</div>
                  </td>
                  <td className="p-4">
                    <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded bg-orange-500/10 text-orange-400 text-[10px] uppercase font-mono tracking-wide border border-orange-500/20">
                      <span className="w-1.5 h-1.5 rounded-full bg-orange-400 animate-pulse"></span>
                      Keycloak IDP
                    </span>
                  </td>
                  <td className="p-4 text-sm text-gray-400">{u.full_name || '-'}</td>
                  <td className="p-4">
                    <span className={`text-xs px-2 py-1 rounded-full border ${u.status === 'active' ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                      {u.status}
                    </span>
                  </td>
                  <td className="p-4 text-right">
                    <button className="text-xs text-blue-400 hover:text-blue-300 mr-3">Manage Roles</button>
                    <button className="text-xs text-gray-500 hover:text-gray-300">Disable</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
