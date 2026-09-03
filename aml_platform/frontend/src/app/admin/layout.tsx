import Link from 'next/link';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-gray-900 text-white">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-800 p-6 flex flex-col">
        <div className="mb-8">
          <h2 className="text-xl font-bold text-blue-400 font-mono tracking-wider">OVERWATCH</h2>
          <p className="text-xs text-gray-400 mt-1 uppercase">Admin Console</p>
        </div>
        <nav className="flex-1 space-y-2">
          <Link href="/admin/users" className="block px-4 py-2 rounded-md hover:bg-gray-700 transition">
            User Management
          </Link>
          <Link href="/admin/roles" className="block px-4 py-2 rounded-md hover:bg-gray-700 transition">
            Role & Access Builder
          </Link>
          <Link href="/" className="block px-4 py-2 mt-8 rounded-md text-gray-500 hover:text-white hover:bg-gray-700 transition">
            ← Back to Platform
          </Link>
        </nav>
        <div className="mt-auto text-xs text-gray-500">
          <p>Auth: Keycloak IDP</p>
          <p>Tenant: Active (System Default)</p>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-gray-800/50 border-b border-gray-700 flex items-center px-8">
          <h1 className="text-lg font-medium text-gray-200">Identity & Access Management</h1>
        </header>
        <div className="flex-1 overflow-auto p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
