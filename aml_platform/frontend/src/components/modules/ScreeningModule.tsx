import React from 'react';
import { Target, Search, XCircle, AlertCircle } from 'lucide-react';

export default function ScreeningModule() {
  return (
    <div className="flex-1 p-6 relative z-20 flex flex-col pointer-events-auto h-full overflow-y-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-purple-500/20 rounded-lg border border-purple-500/30">
          <Target size={20} className="text-purple-400" />
        </div>
        <h2 className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">Sanctions & Watchlist Screening</h2>
      </div>

      <div className="bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800 shadow-xl p-6 h-full flex flex-col">
         <div className="flex justify-between items-center mb-6">
            <h3 className="text-sm font-bold text-slate-300">Overnight Batch Queue - OFAC & HKMA Lists</h3>
            <div className="flex bg-slate-950/80 rounded-lg border border-slate-800 p-1">
               <button className="px-4 py-1.5 rounded-md bg-purple-600 text-white text-[10px] font-bold uppercase tracking-wider shadow">Awaiting Review (3)</button>
               <button className="px-4 py-1.5 rounded-md text-slate-400 hover:text-slate-200 text-[10px] font-bold uppercase tracking-wider">Cleared</button>
            </div>
         </div>

         <div className="flex-1 flex gap-6">
            {/* List */}
            <div className="w-1/3 flex flex-col gap-3">
               {[
                 { id: 'SCR-101', name: 'John Doe Ltd.', match: 'OFAC SDN', score: '99%', type: 'CORPORATE' },
                 { id: 'SCR-102', name: 'Al-Barakat Exchange', match: 'HKMA Terrorist Financing', score: '85%', type: 'ENTITY' },
                 { id: 'SCR-103', name: '0xabc...123 (Wallet)', match: 'DPRK Linked Cluster', score: '100%', type: 'CRYPTO' }
               ].map((hit, idx) => (
                 <div key={idx} className={`p-4 rounded-xl border cursor-pointer border-slate-800 transition-colors ${idx === 0 ? 'bg-slate-800/80 border-purple-500/40 shadow-lg' : 'bg-slate-950/50 hover:bg-slate-900'}`}>
                    <div className="flex justify-between items-center mb-2">
                       <span className="text-sm font-bold text-slate-200">{hit.name}</span>
                       <span className={`text-[10px] font-black px-1.5 py-0.5 rounded ${parseFloat(hit.score) > 90 ? 'bg-red-500/20 text-red-400' : 'bg-orange-500/20 text-orange-400'}`}>{hit.score}</span>
                    </div>
                    <div className="text-[10px] text-slate-400 flex justify-between">
                       <span className="font-mono text-purple-400">{hit.match}</span>
                       <span className="bg-slate-800 px-1 rounded">{hit.type}</span>
                    </div>
                 </div>
               ))}
            </div>

            {/* Profile Comparison */}
            <div className="w-2/3 bg-slate-950/80 rounded-xl border border-slate-800 p-6 flex flex-col">
               <h4 className="text-xs text-slate-500 font-black uppercase tracking-widest mb-4 flex items-center gap-2"><Search size={14}/> Match Resolution: John Doe Ltd.</h4>
               <div className="grid grid-cols-2 gap-4 flex-1">
                  <div className="border border-slate-800 rounded-xl p-4 bg-slate-900/40">
                     <div className="text-[10px] bg-slate-800 text-slate-400 inline-block px-2 py-1 rounded font-bold uppercase mb-4">Internal Customer Data</div>
                     <div className="space-y-3 text-sm">
                       <div className="flex justify-between"><span className="text-slate-500">Name:</span><span className="text-slate-200 font-bold">John Doe Ltd.</span></div>
                       <div className="flex justify-between"><span className="text-slate-500">Reg #:</span><span className="text-slate-300">10928374-HK</span></div>
                       <div className="flex justify-between"><span className="text-slate-500">Address:</span><span className="text-slate-300 text-right">Unit 14, Tower 2,<br/>Central, Hong Kong</span></div>
                     </div>
                  </div>
                  <div className="border border-red-500/30 rounded-xl p-4 bg-red-950/10">
                     <div className="text-[10px] bg-red-500/20 text-red-400 inline-block px-2 py-1 rounded font-bold uppercase mb-4">Watchlist Profile (OFAC SDN)</div>
                     <div className="space-y-3 text-sm">
                       <div className="flex justify-between"><span className="text-slate-500">Name:</span><span className="text-red-300 font-bold">John Doe Ltd.</span></div>
                       <div className="flex justify-between"><span className="text-slate-500">Reg #:</span><span className="text-slate-300">10928374-HK</span></div>
                       <div className="flex justify-between"><span className="text-slate-500">Address:</span><span className="text-slate-300 text-right">Central, Hong Kong</span></div>
                       <div className="flex justify-between"><span className="text-slate-500">Remarks:</span><span className="text-red-400 font-bold">Sanctions Evasion</span></div>
                     </div>
                  </div>
               </div>
               <div className="mt-6 flex gap-4">
                  <button className="flex-1 py-3 border border-slate-700 bg-slate-800 hover:bg-slate-700 rounded-xl text-xs font-bold text-slate-300 uppercase flex justify-center items-center gap-2 transition-colors">
                     <XCircle size={16}/> False Positive
                  </button>
                  <button className="flex-1 py-3 border border-red-500/30 bg-red-600/20 hover:bg-red-600/30 rounded-xl text-xs font-bold text-red-400 uppercase flex justify-center items-center gap-2 transition-colors">
                     <AlertCircle size={16}/> True Match (Freeze & Escalate)
                  </button>
               </div>
            </div>
         </div>
      </div>
    </div>
  );
}
