import React from 'react';
import { BarChart3, TrendingUp, AlertTriangle, Search, Activity, ShieldCheck } from 'lucide-react';
import { KPICard } from '@/components/KPICard';

export default function GovernanceMIS() {
  return (
    <div className="flex-1 p-6 relative z-20 flex flex-col pointer-events-auto h-full overflow-y-auto w-full">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-slate-500/20 rounded-lg border border-slate-500/30">
          <BarChart3 size={20} className="text-slate-400" />
        </div>
        <h2 className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">Governance & MIS (HKMA KPIs)</h2>
      </div>

      <div className="bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800 p-8 shadow-xl mb-6">
        <h3 className="text-sm font-bold text-slate-300 mb-6 flex items-center gap-2"><TrendingUp size={16}/> System Effectiveness & Backlog</h3>
        <div className="grid grid-cols-4 gap-4">
          <KPICard title="Productive Alert Rate" value="14.2%" change="+2.1%" trend="up" icon={Search} color="blue" />
          <KPICard title="False Positive Rate" value="82.5%" change="-5.4%" trend="down" icon={AlertTriangle} color="orange" />
          <KPICard title="STR Conversion Rate" value="3.1%" change="+0.4%" trend="up" icon={ShieldCheck} color="green" />
          <KPICard title="Overdue L1 Alerts" value="0" change="-12" trend="down" icon={Activity} color="slate" />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
         <div className="bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800 p-6 shadow-xl">
           <h3 className="text-sm font-bold text-slate-300 mb-4">Tuning & Coverage Status</h3>
           <div className="space-y-4">
             <div className="flex justify-between items-center py-3 border-b border-slate-800">
               <div>
                  <div className="text-sm font-bold text-slate-200">Annual Scenario Tuning</div>
                  <div className="text-[10px] text-slate-500 mt-1">Due: Oct 2026. Last completed: Oct 2025.</div>
               </div>
               <span className="px-3 py-1 bg-green-500/10 text-green-400 border border-green-500/20 text-[10px] font-bold rounded uppercase">On Track</span>
             </div>
             <div className="flex justify-between items-center py-3 border-b border-slate-800">
               <div>
                  <div className="text-sm font-bold text-slate-200">Stablecoin Typology Coverage</div>
                  <div className="text-[10px] text-slate-500 mt-1">Risk assessment mandated trigger-event review.</div>
               </div>
               <span className="px-3 py-1 bg-yellow-500/10 text-yellow-500 border border-yellow-500/20 text-[10px] font-bold rounded uppercase">Review Needed</span>
             </div>
             <div className="flex justify-between items-center py-3">
               <div>
                  <div className="text-sm font-bold text-slate-200">Data Lineage & Quality</div>
                  <div className="text-[10px] text-slate-500 mt-1">Daily batch completion for FIAT and ONCHAIN sources.</div>
               </div>
               <span className="px-3 py-1 bg-green-500/10 text-green-400 border border-green-500/20 text-[10px] font-bold rounded uppercase">99.9% Success</span>
             </div>
           </div>
         </div>

         <div className="bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800 p-6 shadow-xl">
           <h3 className="text-sm font-bold text-slate-300 mb-4">Alert Volumes by Product</h3>
           <div className="space-y-4">
             <div className="w-full bg-slate-950/50 rounded-xl p-4 border border-slate-800">
                <div className="flex justify-between items-center mb-2">
                   <span className="text-xs font-bold text-slate-400">Fiat Remittance</span>
                   <span className="text-xs font-mono text-slate-200">1,204 Alerts</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-blue-500 h-full" style={{width: '65%'}}></div>
                </div>
             </div>
             <div className="w-full bg-slate-950/50 rounded-xl p-4 border border-slate-800">
                <div className="flex justify-between items-center mb-2">
                   <span className="text-xs font-bold text-slate-400">ERC-20 / Stablecoin</span>
                   <span className="text-xs font-mono text-slate-200">142 Alerts</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-indigo-500 h-full" style={{width: '15%'}}></div>
                </div>
             </div>
             <div className="w-full bg-slate-950/50 rounded-xl p-4 border border-slate-800">
                <div className="flex justify-between items-center mb-2">
                   <span className="text-xs font-bold text-slate-400">Trade Finance</span>
                   <span className="text-xs font-mono text-slate-200">54 Alerts</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-emerald-500 h-full" style={{width: '8%'}}></div>
                </div>
             </div>
           </div>
         </div>
      </div>
    </div>
  );
}
