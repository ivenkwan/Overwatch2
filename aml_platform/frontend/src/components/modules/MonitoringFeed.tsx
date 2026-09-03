import React, { useEffect, useState } from 'react';
import { Activity, ArrowRight, ArrowDownLeft, ArrowUpRight, Loader2, AlertCircle } from 'lucide-react';
import { api } from '../../services/api';

export default function MonitoringFeed() {
  const [payments, setPayments] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    
    api.fetchFeed()
      .then(data => {
        if (isMounted) {
          setPayments(data);
          setIsLoading(false);
        }
      })
      .catch(err => {
        if (isMounted) {
          setError(err.message);
          setIsLoading(false);
        }
      });

    return () => { isMounted = false; };
  }, []);

  return (
    <div className="flex-1 p-6 relative z-20 flex flex-col pointer-events-auto h-full overflow-y-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-blue-500/20 rounded-lg border border-blue-500/30">
          <Activity size={20} className="text-blue-400" />
        </div>
        <h2 className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">Real-Time Core Ledger Feed</h2>
      </div>

      <div className="bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800 shadow-xl overflow-hidden flex-1 flex flex-col">
        {isLoading ? (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-400 pt-10">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500 mb-4" />
            <p>Hydrating ledger streaming pipeline...</p>
          </div>
        ) : error ? (
          <div className="flex-1 flex flex-col items-center justify-center text-rose-400 pt-10 p-6 text-center">
            <AlertCircle className="w-12 h-12 mb-4 opacity-50" />
            <p className="font-bold">Backend Connection Failed</p>
            <p className="text-xs mt-2 opacity-75">{error}</p>
          </div>
        ) : (
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-950/50 text-xs text-slate-400 border-b border-slate-800 uppercase tracking-wider">
              <th className="p-4 font-black">Txn Hash</th>
              <th className="p-4 font-black">Date</th>
              <th className="p-4 font-black">Flow</th>
              <th className="p-4 font-black">Counterparty</th>
              <th className="p-4 font-black text-right">Amount</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {payments.map((p) => (
              <tr key={p.txn_hash} className="hover:bg-slate-800/40 transition-colors">
                <td className="p-4 text-xs font-mono text-slate-500 truncate max-w-[150px]">
                  {p.txn_hash}
                </td>
                <td className="p-4 text-xs font-mono text-slate-400">
                  {new Date(p.txn_date).toLocaleDateString()}
                </td>
                <td className="p-4">
                  <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase ${p.cdi_code === 'D' ? 'bg-rose-500/10 text-rose-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
                    {p.cdi_code === 'D' ? 'DEBIT' : 'CREDIT'}
                  </span>
                </td>
                <td className="p-4 text-sm font-bold text-slate-200">
                  {p.counterparty_id}
                </td>
                <td className="p-4 text-right">
                  <span className="text-sm font-bold text-slate-200">
                    ${p.txn_amount_in_hkd.toLocaleString()} 
                    <span className="text-[10px] ml-1 text-slate-500 font-normal">HKD</span>
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        )}
      </div>
    </div>
  );
}
