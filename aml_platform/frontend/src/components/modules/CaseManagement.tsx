'use client';
import React, { useState, useEffect } from 'react';
import { Briefcase, Link as LinkIcon, Calendar, History, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { api } from '@/services/api';
import { Case } from '@/types/models';

export default function CaseManagement() {
  const [cases, setCases] = useState<Case[]>([]);
  const [activeCase, setActiveCase] = useState<Case | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadCases();
  }, []);

  const loadCases = async () => {
    try {
      setLoading(true);
      const data = await api.cases.fetchAll();
      setCases(data);
      if (data.length > 0) {
        loadCaseDetails(data[0].case_id);
      } else {
        setLoading(false);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load cases");
      setLoading(false);
    }
  };

  const loadCaseDetails = async (caseId: string) => {
    try {
      setLoading(true);
      const data = await api.cases.fetchOne(caseId);
      setActiveCase(data);
    } catch (err: any) {
      setError(err.message || "Failed to load case details");
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (action: string) => {
    if (!activeCase) return;
    try {
      setActionLoading(true);
      await api.cases.submitAction(activeCase.case_id, action, `Action ${action} submitted from UI`);
      // Reload logic
      loadCaseDetails(activeCase.case_id);
    } catch (err: any) {
      alert("Error submitting action: " + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading && !activeCase) {
    return <div className="flex-1 flex items-center justify-center h-full"><Loader2 className="animate-spin text-indigo-500" /></div>;
  }

  if (error) {
    return <div className="flex-1 flex items-center justify-center h-full text-red-500 font-bold">{error}</div>;
  }

  if (!activeCase) {
    return <div className="flex-1 flex items-center justify-center h-full text-slate-500">No cases available. Please trigger an alert escalation.</div>;
  }

  const isMakerTask = activeCase?.activeTask?.taskDefinitionKey === 'makerTask';
  const isCheckerTask = activeCase?.activeTask?.taskDefinitionKey === 'checkerTask';

  return (
    <div className="flex-1 p-6 relative z-20 flex flex-col pointer-events-auto h-full overflow-y-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-indigo-500/20 rounded-lg border border-indigo-500/30">
          <Briefcase size={20} className="text-indigo-400" />
        </div>
        <h2 className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">Case Management (Network Investigation)</h2>
      </div>

      <div className="grid grid-cols-4 gap-6 h-full">
        {/* Main Case Info */}
        <div className="col-span-3 space-y-6">
           <div className="bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800 p-6 shadow-xl flex flex-col gap-6">
              <div className="flex justify-between items-center pb-4 border-b border-slate-800">
                 <div>
                   <h3 className="text-2xl font-bold text-slate-100">{activeCase.case_number || activeCase.case_id}</h3>
                   <span className="text-sm text-slate-500 flex items-center gap-2"><Calendar size={14}/> Opened: {new Date(activeCase.created_at).toLocaleString()}</span>
                 </div>
                 <div className="px-4 py-2 bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 font-bold rounded-lg uppercase tracking-wider text-sm flex items-center gap-2">
                   {activeCase.status}
                 </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                 <div className="bg-slate-950/50 p-5 rounded-xl border border-slate-800/60">
                   <h4 className="text-xs text-slate-500 font-black uppercase tracking-widest mb-3 flex items-center gap-2"><LinkIcon size={12}/> Linked Network Entities</h4>
                   <div className="space-y-2">
                     <span className="inline-block px-2 py-1 bg-orange-500/10 border border-orange-500/20 text-orange-400 text-[10px] font-mono rounded mr-2">Alert ID: {activeCase.source_alert_id || 'N/A'}</span>
                   </div>
                   <button className="mt-4 text-[10px] font-bold text-slate-400 hover:text-white uppercase tracking-widest border border-slate-800 px-3 py-1.5 rounded-md w-full transition-colors">Add Network Link</button>
                 </div>

                 <div className="bg-slate-950/50 p-5 rounded-xl border border-slate-800/60 flex flex-col justify-between">
                   <div>
                     <h4 className="text-xs text-slate-500 font-black uppercase tracking-widest mb-3">Workflow State</h4>
                     <p className="text-xs text-slate-400 leading-relaxed">
                       {activeCase.activeTask ? `Active Task: ${activeCase.activeTask.name}` : `Workflow Completed.`}
                     </p>
                   </div>
                   <div className="flex gap-2 mt-4">
                      {isMakerTask ? (
                         <div className="flex-1 bg-indigo-600 rounded-lg p-2 text-center text-[10px] font-bold text-white uppercase tracking-wider">Maker Phase Active</div>
                      ) : (
                         <div className="flex-1 bg-slate-800 rounded-lg p-2 text-center text-[10px] font-bold text-slate-500 uppercase tracking-wider">Maker: Completed</div>
                      )}
                      
                      {isCheckerTask ? (
                         <div className="flex-1 bg-orange-600 rounded-lg p-2 text-center text-[10px] items-center justify-center font-bold text-white uppercase tracking-wider flex">Checker Approval</div>
                      ) : activeCase.status === 'closed' || activeCase.status === 'approved' ? (
                         <div className="flex-1 bg-emerald-600/20 border border-emerald-500/30 rounded-lg p-2 text-center text-[10px] font-bold text-emerald-400 uppercase tracking-wider flex items-center justify-center">Approved</div>
                      ) : (
                         <div className="flex-1 bg-slate-900 border border-slate-800 rounded-lg p-2 text-center text-[10px] items-center justify-center font-bold text-slate-500 uppercase tracking-wider border-dashed flex">Pending Checker</div>
                      )}
                   </div>
                 </div>
              </div>
           </div>
           
           {/* Timeline */}
           <div className="bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800 p-6 shadow-xl flex-1 border-l-4 border-l-indigo-500">
             <h4 className="text-xs text-slate-500 font-black uppercase tracking-widest mb-6 flex items-center gap-2"><History size={14}/> Investigation Timeline</h4>
             <div className="space-y-4">
               {/* Timeline data normally comes from API, simplified for display */}
               <div className="text-xs text-slate-400">Timeline events load here...</div>
             </div>
           </div>
        </div>

        {/* Action Panel */}
        <div className="col-span-1 flex flex-col gap-4">
          {actionLoading && <div className="text-center text-xs text-slate-400 animate-pulse">Processing Action...</div>}
          
          {isMakerTask && (
            <button onClick={() => handleAction('submit')} disabled={actionLoading} className="w-full py-4 bg-emerald-600/20 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-600/30 rounded-2xl font-black uppercase tracking-widest transition-all shadow-lg flex flex-col items-center gap-2 disabled:opacity-50">
              Submit Case for Review
            </button>
          )}

          {isCheckerTask && (
            <>
              <button onClick={() => handleAction('approve')} disabled={actionLoading} className="w-full py-4 bg-emerald-600/20 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-600/30 rounded-2xl font-black uppercase tracking-widest transition-all shadow-lg flex flex-col items-center gap-2 disabled:opacity-50">
                <CheckCircle size={20} />
                Approve Case
              </button>
              <button onClick={() => handleAction('reject')} disabled={actionLoading} className="w-full py-4 bg-red-600/20 border border-red-500/30 text-red-400 hover:bg-red-600/30 rounded-2xl font-black uppercase tracking-widest transition-all shadow-lg flex flex-col items-center gap-2 disabled:opacity-50">
                <XCircle size={20} />
                Reject Case
              </button>
            </>
          )}

          {!isMakerTask && !isCheckerTask && activeCase.status !== 'closed' && (
            <p className="text-xs text-slate-500 text-center p-4 border border-slate-800 border-dashed rounded-xl">No active workflow tasks for your role.</p>
          )}

          <hr className="border-slate-800 my-2" />
          
          <button className="w-full py-4 bg-slate-800/50 border border-slate-700/50 text-slate-300 hover:bg-slate-800 rounded-2xl font-bold uppercase tracking-wider text-xs transition-all">
            Generate Network PDF Report
          </button>
        </div>
      </div>
    </div>
  );
}
