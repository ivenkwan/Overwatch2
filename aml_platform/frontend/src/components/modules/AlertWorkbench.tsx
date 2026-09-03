import React, { useState, useEffect } from 'react';
import { AlertTriangle, User, ShieldAlert, CheckCircle2, Loader2, Save } from 'lucide-react';
import { api } from '@/services/api';

export default function AlertWorkbench() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [activeAlert, setActiveAlert] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [notes, setNotes] = useState('');
  const [validationError, setValidationError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    setIsLoading(true);
    try {
      const data = await api.alerts.fetchAll('OPEN', 50);
      setAlerts(data);
      if (data.length > 0) setActiveAlert(data[0]);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAction = async (actionType: 'ESC' | 'CLOSE') => {
    if (!notes || notes.trim().length < 5) {
      setValidationError('Mandatory rationale must be at least 5 characters.');
      return;
    }
    setValidationError('');
    setIsSubmitting(true);
    
    try {
      if (actionType === 'ESC') {
        await api.alerts.proposeClose(activeAlert.txn_hash, notes);
      } else {
        await api.alerts.assign(activeAlert.txn_hash); // Assuming direct triage/closure assigned
      }
      // Re-fetch or remove from current queue
      await fetchAlerts();
      setNotes('');
    } catch (e) {
      setValidationError('Failed to update alert state.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-slate-400 h-full w-full">
        <Loader2 className="w-12 h-12 animate-spin text-orange-500 mb-4" />
        <p className="font-bold">Loading Work Queue...</p>
      </div>
    );
  }

  if (!alerts.length) {
    return (
      <div className="flex-1 p-6 flex flex-col items-center justify-center h-full">
        <AlertTriangle className="w-16 h-16 text-slate-600 mb-4" />
        <h3 className="text-xl font-bold text-slate-400">Zero Pending Alerts</h3>
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 relative z-20 flex flex-col pointer-events-auto h-full overflow-y-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-orange-500/20 rounded-lg border border-orange-500/30">
          <AlertTriangle size={20} className="text-orange-400" />
        </div>
        <h2 className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">Alert Workbench (L1 / L2)</h2>
      </div>

      <div className="grid grid-cols-3 gap-6 h-full">
        {/* Alerts Queue */}
        <div className="col-span-1 bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800 p-4 overflow-y-auto shadow-xl">
          <h3 className="text-xs font-black text-slate-500 uppercase tracking-widest mb-4">Pending Queue</h3>
          <div className="space-y-3">
            {alerts.map(alert => (
              <div key={alert.txn_hash} onClick={() => {setActiveAlert(alert); setNotes(''); setValidationError('');}} className={`p-4 rounded-xl border cursor-pointer transition-all ${activeAlert?.txn_hash === alert.txn_hash ? 'bg-slate-800 border-orange-500/50 shadow-lg' : 'bg-slate-950/50 border-slate-800/60 hover:border-slate-700'}`}>
                <div className="flex justify-between items-start mb-2">
                  <span className="text-sm font-bold text-slate-200 truncate">{alert.txn_hash.substring(0, 16)}...</span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded font-black uppercase bg-orange-500/20 text-orange-400`}>HIGH</span>
                </div>
                <div className="text-xs text-slate-400 line-clamp-1">{alert.txn_type}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Selected Alert Details */}
        {activeAlert && (
          <div className="col-span-2 flex flex-col space-y-6">
            <div className="bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800 p-6 shadow-xl relative">
              {isSubmitting && (
                 <div className="absolute inset-0 bg-slate-950/50 backdrop-blur-sm z-50 flex items-center justify-center rounded-2xl">
                    <Loader2 className="w-12 h-12 animate-spin text-orange-500" />
                 </div>
              )}
              <div className="flex justify-between items-start mb-6 border-b border-slate-800 pb-4">
                <div>
                  <h3 className="text-lg font-bold text-slate-100">{activeAlert.txn_hash}</h3>
                  <span className="text-sm text-slate-500">Trigger: {activeAlert.cdi_code || 'TRANSACTIONAL_ANOMALY'}</span>
                </div>
                <div className="px-3 py-1.5 bg-orange-500/10 border border-orange-500/20 rounded-lg text-orange-400 font-bold text-xs uppercase tracking-wider flex items-center gap-2">
                  <ShieldAlert size={14} /> Risk Score: {activeAlert.txn_amount_in_hkd > 100000 ? 98 : 75}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-6 mb-6">
                <div className="space-y-4">
                  <h4 className="text-xs text-slate-500 font-black uppercase tracking-widest flex items-center gap-2"><User size={12}/> Subject Profile</h4>
                  <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800/60 space-y-2">
                    <div className="flex justify-between text-sm"><span className="text-slate-400">Customer ID:</span><span className="font-mono text-blue-400 font-bold">{activeAlert.customer_num}</span></div>
                    <div className="flex justify-between text-sm"><span className="text-slate-400">Risk Rating:</span><span className="text-red-400 font-bold">HIGH</span></div>
                    <div className="flex justify-between text-sm"><span className="text-slate-400">Amount:</span><span className="text-slate-200">{activeAlert.txn_amount_in_hkd} HKD</span></div>
                  </div>
                </div>

                <div className="space-y-4">
                  <h4 className="text-xs text-slate-500 font-black uppercase tracking-widest">Metadata / Footprint</h4>
                  <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800/60 space-y-2">
                    <div className="flex justify-between text-sm"><span className="text-slate-400">Counterparty:</span><span className="font-mono text-slate-200">{activeAlert.counterparty_id}</span></div>
                    <div className="flex justify-between text-sm"><span className="text-slate-400">Location:</span><span className="text-slate-200">{activeAlert.txn_country}</span></div>
                    <div className="flex justify-between text-sm"><span className="text-slate-400">Date:</span><span className="font-mono text-slate-200">{new Date(activeAlert.txn_date).toLocaleDateString()}</span></div>
                  </div>
                </div>
              </div>

              {/* Disposition Panel */}
              <div className="border-t border-slate-800 pt-6">
                 <h4 className="text-xs text-slate-500 font-black uppercase tracking-widest mb-4">Disposition Decision (Mandatory Rationale)</h4>
                 {validationError && <div className="mb-2 text-xs font-bold text-red-500 bg-red-500/10 p-2 rounded border border-red-500/20">{validationError}</div>}
                 <textarea 
                   value={notes}
                   onChange={(e) => setNotes(e.target.value)}
                   className="w-full bg-slate-950/50 border border-slate-800 rounded-xl p-4 text-sm text-slate-300 focus:outline-none focus:border-blue-500 transition-colors h-24" 
                   placeholder="Document source-of-funds analysis, CDD references, and justification for closure or escalation here..."
                 />
                 <div className="flex gap-4 mt-4">
                   <button 
                     onClick={() => handleAction('ESC')}
                     disabled={isSubmitting}
                     className="flex-1 bg-red-600/20 text-red-400 border border-red-500/30 hover:bg-red-600/30 py-3 rounded-xl font-bold uppercase tracking-wider text-xs transition-colors flex items-center justify-center gap-2">
                     <ShieldAlert size={16}/> Escalate to L2 / Case
                   </button>
                   <button 
                     onClick={() => handleAction('CLOSE')}
                     disabled={isSubmitting}
                     className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 py-3 rounded-xl font-bold uppercase tracking-wider text-xs transition-colors flex items-center justify-center gap-2">
                     <CheckCircle2 size={16}/> Close Alert (False Positive)
                   </button>
                 </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
