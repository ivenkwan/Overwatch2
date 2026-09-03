"use client";

import React, { Suspense } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  AlertTriangle, 
  Activity, 
  BarChart3, 
  Search,
  Settings,
  Bell,
  User,
  Briefcase,
  FileText,
  Target,
  Share2,
  Loader2
} from 'lucide-react';
import ErrorBoundary from '@/components/ErrorBoundary';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  const getIsActive = (path: string) => {
    return pathname?.startsWith(path);
  };

  return (
    <main className="flex h-screen flex-col bg-slate-950 text-slate-100 font-sans overflow-hidden">
      {/* Top Navigation */}
      <header className="flex items-center justify-between border-b border-slate-800/50 px-8 py-3 bg-slate-900/40 backdrop-blur-xl shrink-0 z-50">
        <div className="flex items-center gap-8">
          <Link href="/network" className="flex items-center gap-2">
            <div className="h-8 w-8 bg-blue-600 rounded-lg flex items-center justify-center font-black italic text-white shadow-lg shadow-blue-500/20">OW</div>
            <h1 className="text-lg font-bold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">OVERWATCH <span className="text-blue-500">AML</span></h1>
          </Link>
          
          <nav className="flex items-center gap-6">
            <Link href="/network" className={`text-xs font-semibold pb-4 -mb-4 ${getIsActive('/network') || getIsActive('/alerts') ? 'text-blue-400 border-b-2 border-blue-500' : 'text-slate-500 hover:text-slate-300 transition-colors'}`}>Investigations</Link>
            <Link href="/reports" className="text-xs font-semibold text-slate-500 hover:text-slate-300 transition-colors">Reports</Link>
            <Link href="/admin" className="text-xs font-semibold text-slate-500 hover:text-slate-300 transition-colors">System Health</Link>
          </nav>
        </div>

        <div className="flex items-center gap-6">
          <div className="relative group">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-blue-400 transition-colors" />
            <input 
              type="text" 
              placeholder="Search Entities / Tx Hashes..." 
              className="bg-slate-800/50 border border-slate-700/50 rounded-full py-1.5 pl-10 pr-4 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500/50 transition-all w-64"
            />
          </div>
          <div className="flex items-center gap-3 border-l border-slate-800 pl-6">
             <Bell size={18} className="text-slate-400 cursor-pointer hover:text-blue-400 transition-colors" />
             <Settings size={18} className="text-slate-400 cursor-pointer hover:text-blue-400 transition-colors" />
             <div className="h-8 w-8 rounded-full bg-slate-800 flex items-center justify-center border border-slate-700 cursor-pointer hover:border-blue-500 transition-all">
               <User size={16} className="text-slate-400" />
             </div>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Unified Workspace Sidebar */}
        <aside className="w-16 border-r border-slate-800 bg-slate-950 flex flex-col items-center py-6 gap-4 z-50 shrink-0">
           <Link href="/network" className={`p-3 rounded-xl transition-colors ${getIsActive('/network') ? 'bg-blue-600/20 text-blue-400' : 'text-slate-500 hover:text-slate-300 hover:bg-slate-900'}`} title="Network Graph">
             <Share2 size={22}/>
           </Link>
           <Link href="/monitoring" className={`p-3 rounded-xl transition-colors ${getIsActive('/monitoring') ? 'bg-blue-600/20 text-blue-400' : 'text-slate-500 hover:text-slate-300 hover:bg-slate-900'}`} title="Monitoring Feed">
             <Activity size={22}/>
           </Link>
           <Link href="/alerts" className={`p-3 rounded-xl transition-colors ${getIsActive('/alerts') ? 'bg-orange-500/20 text-orange-400' : 'text-slate-500 hover:text-slate-300 hover:bg-slate-900'}`} title="Alerts Workbench">
             <AlertTriangle size={22}/>
           </Link>
           <Link href="/cases" className={`p-3 rounded-xl transition-colors ${getIsActive('/cases') ? 'bg-indigo-500/20 text-indigo-400' : 'text-slate-500 hover:text-slate-300 hover:bg-slate-900'}`} title="Case Management">
             <Briefcase size={22}/>
           </Link>
           <Link href="/str" className={`p-3 rounded-xl transition-colors ${getIsActive('/str') ? 'bg-emerald-500/20 text-emerald-400' : 'text-slate-500 hover:text-slate-300 hover:bg-slate-900'}`} title="STR Reporting">
             <FileText size={22}/>
           </Link>
           <Link href="/screening" className={`p-3 rounded-xl transition-colors ${getIsActive('/screening') ? 'bg-purple-500/20 text-purple-400' : 'text-slate-500 hover:text-slate-300 hover:bg-slate-900'}`} title="Screening">
             <Target size={22}/>
           </Link>
           <Link href="/governance" className={`p-3 rounded-xl transition-colors ${getIsActive('/governance') ? 'bg-slate-500/20 text-slate-300' : 'text-slate-500 hover:text-slate-300 hover:bg-slate-900'}`} title="Governance MIS">
             <BarChart3 size={22}/>
           </Link>
        </aside>

        {/* Main Content Workspace */}
        <section className="flex-1 flex flex-col bg-slate-950 relative overflow-hidden py-4">
          <div className="flex-1 mx-4 relative z-10 bg-slate-900/20 rounded-[2rem] border border-slate-800/80 shadow-2xl overflow-hidden group flex flex-col">
            {/* Subtle Grid Background */}
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none z-0" />
            
            <div className="relative z-10 w-full h-full flex flex-col">
              <ErrorBoundary fallback={
                <div className="flex-1 flex items-center justify-center flex-col text-red-400">
                  <AlertTriangle className="w-12 h-12 mb-4 opacity-50 text-red-500" />
                  <p className="font-bold">Module Encountered a Critical Error</p>
                  <p className="text-xs opacity-70 mt-2">Try refreshing the page or navigating back.</p>
                </div>
              }>
                <Suspense fallback={
                  <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
                    <Loader2 className="w-12 h-12 animate-spin text-blue-500 mb-4" />
                    <p className="font-bold">Loading Workspace Module...</p>
                    <p className="text-xs opacity-70 mt-2">Connecting to Backend API</p>
                  </div>
                }>
                  {children}
                </Suspense>
              </ErrorBoundary>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
