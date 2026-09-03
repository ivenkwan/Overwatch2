import React, { useState, useEffect } from "react";
import { FileText, Upload, Save, Send, Plus, Loader2, CheckCircle2, AlertCircle, History } from "lucide-react";
import { api } from "@/services/api";

export default function STRPreparation() {
  const [strs, setStrs] = useState<any[]>([]);
  const [activeStr, setActiveStr] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form Fields
  const [triggeringFactors, setTriggeringFactors] = useState("");
  const [subjectBackground, setSubjectBackground] = useState("");
  const [digitalFootprints, setDigitalFootprints] = useState("");
  const [transactionSummary, setTransactionSummary] = useState("");

  // Status/Alert Feedback
  const [feedbackMsg, setFeedbackMsg] = useState("");
  const [isError, setIsError] = useState(false);

  useEffect(() => {
    loadSTRs();
  }, []);

  const loadSTRs = async (selectId?: string) => {
    setIsLoading(true);
    try {
      const data = await api.strs.fetchAll();
      setStrs(data);
      
      if (data.length > 0) {
        let selected = data[0];
        if (selectId) {
          selected = data.find((s: any) => s.str_id === selectId) || data[0];
        }
        handleSelectSTR(selected);
      } else {
        setActiveStr(null);
        clearFields();
      }
    } catch (err) {
      console.error("Failed to load STRs", err);
      showFeedback("Failed to load reports queue.", true);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectSTR = (report: any) => {
    setActiveStr(report);
    setTriggeringFactors(report.triggering_factors || "");
    setSubjectBackground(report.subject_background || "");
    setDigitalFootprints(report.digital_footprints || "");
    setTransactionSummary(report.transaction_summary || "");
    setFeedbackMsg("");
  };

  const clearFields = () => {
    setTriggeringFactors("");
    setSubjectBackground("");
    setDigitalFootprints("");
    setTransactionSummary("");
  };

  const showFeedback = (msg: string, error: boolean = false) => {
    setFeedbackMsg(msg);
    setIsError(error);
    setTimeout(() => {
      setFeedbackMsg("");
    }, 5000);
  };

  const handleCreateNew = async () => {
    setIsSaving(true);
    try {
      const newDraft = await api.strs.create();
      showFeedback("New STR draft initialized!");
      await loadSTRs(newDraft.str_id);
    } catch (err) {
      console.error(err);
      showFeedback("Failed to initialize new STR.", true);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveDraft = async () => {
    if (!activeStr) return;
    setIsSaving(true);
    try {
      const updated = await api.strs.update(activeStr.str_id, {
        triggering_factors: triggeringFactors,
        subject_background: subjectBackground,
        digital_footprints: digitalFootprints,
        transaction_summary: transactionSummary
      });
      showFeedback("Draft saved successfully!");
      const updatedList = strs.map((s: any) => s.str_id === updated.str_id ? updated : s);
      setStrs(updatedList);
      setActiveStr(updated);
    } catch (err) {
      console.error(err);
      showFeedback("Failed to save draft.", true);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSubmitToJFIU = async () => {
    if (!activeStr) return;
    
    if (!triggeringFactors.trim() || !transactionSummary.trim()) {
      showFeedback("Mandatory triggering factors & transaction summaries are required for submission.", true);
      return;
    }

    setIsSubmitting(true);
    try {
      const finalized = await api.strs.submit(activeStr.str_id);
      showFeedback("STR finalized and successfully submitted to JFIU STREAMS!");
      await loadSTRs(finalized.str_id);
    } catch (err) {
      console.error(err);
      showFeedback("Failed to submit STR report.", true);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isReadOnly = activeStr?.status === "filed";

  return (
    <div className="flex-1 p-6 relative z-20 flex flex-col pointer-events-auto h-full overflow-y-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-500/20 rounded-lg border border-emerald-500/30">
            <FileText size={20} className="text-emerald-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">JFIU STR Reporting Form</h2>
            <p className="text-[10px] text-slate-500">Prepare, review, and file JFIU-compliant Suspicious Transaction Reports.</p>
          </div>
        </div>
        
        <button
          onClick={handleCreateNew}
          disabled={isLoading || isSaving}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold text-xs uppercase tracking-wider rounded-xl flex items-center gap-2 shadow-lg shadow-emerald-600/10 transition-all cursor-pointer"
        >
          <Plus size={14} /> New STR Draft
        </button>
      </div>

      <div className="flex flex-1 gap-6 overflow-hidden h-[calc(100%-80px)] min-h-[500px]">
        {/* Left Side: STR Queue/History Sidebar */}
        <div className="w-80 bg-slate-950/40 border border-slate-900 rounded-2xl p-4 flex flex-col h-full overflow-y-auto">
          <div className="flex items-center gap-2 mb-4 pb-2 border-b border-slate-900">
            <History size={14} className="text-slate-500" />
            <span className="text-[10px] font-black uppercase text-slate-500 tracking-wider">Reports Queue ({strs.length})</span>
          </div>

          {isLoading && strs.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-500">
              <Loader2 className="w-6 h-6 animate-spin text-emerald-500 mb-2" />
              <span className="text-xs font-bold">Loading queue...</span>
            </div>
          ) : strs.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-4 text-slate-600">
              <FileText size={32} className="opacity-30 mb-2" />
              <span className="text-xs font-bold">No reports found</span>
              <p className="text-[9px] mt-1 text-slate-700">Click &quot;New STR Draft&quot; to initialize a suspicious transaction report.</p>
            </div>
          ) : (
            <div className="space-y-2 flex-1 overflow-y-auto pr-1">
              {strs.map((report) => (
                <div
                  key={report.str_id}
                  onClick={() => handleSelectSTR(report)}
                  className={`p-3 rounded-xl border cursor-pointer transition-all ${
                    activeStr?.str_id === report.str_id
                      ? "bg-slate-900/80 border-slate-800 shadow-md"
                      : "bg-slate-950/20 border-slate-950 hover:bg-slate-900/30"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="text-[9px] font-mono text-slate-400 truncate max-w-[120px]">
                      ID: {report.str_id.substring(0, 8)}...
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[8px] font-black uppercase tracking-wider ${
                      report.status === "filed"
                        ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
                        : "bg-yellow-500/10 border border-yellow-500/20 text-yellow-500"
                    }`}>
                      {report.status}
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-500 line-clamp-2 leading-relaxed">
                    {report.triggering_factors || "(Empty Triggering Factors)"}
                  </p>
                  <div className="text-[8px] text-slate-600 mt-2 font-mono flex justify-between">
                    <span>{new Date(report.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Side: Editor Panel */}
        <div className="flex-1 bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800 p-6 flex flex-col h-full overflow-y-auto shadow-xl">
          {activeStr ? (
            <div className="flex flex-col h-full justify-between">
              {/* Report Header Info */}
              <div className="mb-4 pb-4 border-b border-slate-800 flex justify-between items-center">
                <div>
                  <h3 className="text-sm font-bold text-slate-300">
                    Suspicious Transaction Report (STREAMS Prep)
                  </h3>
                  <p className="text-[10px] text-slate-500 mt-1">
                    STR ID: <span className="font-mono text-slate-400">{activeStr.str_id}</span> • Created: {new Date(activeStr.created_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-3 py-1 border rounded text-[10px] font-bold uppercase tracking-wider ${
                    activeStr.status === "filed"
                      ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                      : "bg-yellow-500/10 border border-yellow-500/20 text-yellow-500"
                  }`}>
                    {activeStr.status} Mode
                  </span>
                </div>
              </div>

              {/* Feedback messages */}
              {feedbackMsg && (
                <div className={`p-3 rounded-xl border mb-4 flex items-center gap-2 text-xs font-bold ${
                  isError 
                    ? "bg-red-500/10 border-red-500/20 text-red-400" 
                    : "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                }`}>
                  {isError ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />}
                  {feedbackMsg}
                </div>
              )}

              {/* Form Input fields */}
              <div className="grid grid-cols-2 gap-6 flex-1 overflow-y-auto pr-1 mb-6">
                <div className="space-y-4">
                  <div>
                    <label className="block text-[10px] font-black uppercase text-slate-500 mb-2 tracking-wider">
                      1. Triggering Factors & Intelligence (Mandatory)
                    </label>
                    <textarea
                      disabled={isReadOnly || isSaving}
                      value={triggeringFactors}
                      onChange={(e) => setTriggeringFactors(e.target.value)}
                      className="w-full h-32 bg-slate-950/50 border border-slate-800 rounded-xl p-3 text-xs text-slate-300 focus:border-emerald-500 focus:outline-none disabled:opacity-60 transition-all resize-none"
                      placeholder="E.g., Alerted on circular flow typology, verified adverse news match... Explain the rationale and triggers."
                    ></textarea>
                  </div>
                  
                  <div>
                    <label className="block text-[10px] font-black uppercase text-slate-500 mb-2 tracking-wider">
                      2. Subject Background (CDD)
                    </label>
                    <textarea
                      disabled={isReadOnly || isSaving}
                      value={subjectBackground}
                      onChange={(e) => setSubjectBackground(e.target.value)}
                      className="w-full h-32 bg-slate-950/50 border border-slate-800 rounded-xl p-3 text-xs text-slate-300 focus:border-emerald-500 focus:outline-none disabled:opacity-60 transition-all resize-none"
                      placeholder="E.g., Corporate shell entity incorporated in BVI. Source of wealth stated as consulting..."
                    ></textarea>
                  </div>

                  <div>
                    <label className="block text-[10px] font-black uppercase text-slate-500 mb-2 tracking-wider">
                      3. Digital Footprints (Required for Web3/Crypto)
                    </label>
                    <textarea
                      disabled={isReadOnly || isSaving}
                      value={digitalFootprints}
                      onChange={(e) => setDigitalFootprints(e.target.value)}
                      className="w-full h-32 bg-slate-950/50 border border-slate-800 rounded-xl p-3 text-xs text-slate-300 focus:border-emerald-500 focus:outline-none disabled:opacity-60 transition-all resize-none"
                      placeholder="IP Address: 203.0.113.43 (HK)
Device Hash: MAC-9A-00-B2-CD-11
On-chain Wallet: 0x8b1...a9d"
                    ></textarea>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-[10px] font-black uppercase text-slate-500 mb-2 tracking-wider">
                      4. Transaction Summary & Source of Funds (Mandatory)
                    </label>
                    <textarea
                      disabled={isReadOnly || isSaving}
                      value={transactionSummary}
                      onChange={(e) => setTransactionSummary(e.target.value)}
                      className="w-full h-32 bg-slate-950/50 border border-slate-800 rounded-xl p-3 text-xs text-slate-300 focus:border-emerald-500 focus:outline-none disabled:opacity-60 transition-all resize-none"
                      placeholder="Review period: Jan-Mar 2026. $5M structured inwards and $4.9M outwards to offshore accounts..."
                    ></textarea>
                  </div>
                  
                  <div>
                    <label className="block text-[10px] font-black uppercase text-slate-500 mb-2 tracking-wider">
                      5. Attachments (Editable Schedules)
                    </label>
                    <div className="w-full h-32 bg-slate-950/50 border border-dashed border-slate-800 rounded-xl flex flex-col items-center justify-center cursor-pointer hover:bg-slate-900 transition-colors">
                      <Upload size={20} className="text-slate-600 mb-2" />
                      <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Attach Network Graph PDF & Tx Excel</span>
                      <p className="text-[8px] text-slate-700 mt-1">Accepts PDF, XLSX, and PNG exports up to 10MB.</p>
                    </div>
                  </div>

                  {activeStr.status === "filed" && (
                    <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex flex-col gap-1 text-slate-400 mt-2">
                      <span className="text-[10px] font-black uppercase text-emerald-400 tracking-wider">Submission Summary</span>
                      <p className="text-[10px] leading-relaxed">
                        This STR has been officially finalized and submitted to the JFIU STREAMS node. Writing has been locked to secure the regulatory audit trail.
                      </p>
                      {activeStr.submitted_by && (
                        <p className="text-[8px] text-slate-500 mt-1">
                          Submitted By: <span className="font-mono">{activeStr.submitted_by}</span> • Time: {new Date(activeStr.submitted_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Form actions footer */}
              {!isReadOnly && (
                <div className="pt-4 border-t border-slate-800 flex justify-end gap-4">
                  <button
                    onClick={handleSaveDraft}
                    disabled={isSaving || isSubmitting}
                    className="px-6 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 font-bold text-xs uppercase tracking-wider flex items-center gap-2 transition-colors cursor-pointer"
                  >
                    {isSaving ? <Loader2 size={14} className="animate-spin text-emerald-400" /> : <Save size={14} />} 
                    Save Draft
                  </button>
                  <button
                    onClick={handleSubmitToJFIU}
                    disabled={isSaving || isSubmitting}
                    className="px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-bold text-xs uppercase tracking-wider flex items-center gap-2 shadow-lg shadow-emerald-600/20 transition-all cursor-pointer"
                  >
                    {isSubmitting ? <Loader2 size={14} className="animate-spin text-white" /> : <Send size={14} />} 
                    Finalize & Submit to JFIU
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center text-slate-500 p-8">
              <FileText size={48} className="text-slate-700 mb-4 animate-pulse" />
              <h3 className="text-lg font-bold text-slate-400">No STR Selected</h3>
              <p className="text-xs mt-2 max-w-sm text-slate-600 leading-relaxed">
                Click &quot;New STR Draft&quot; in the header or select an existing report draft from the left queue to begin preparing a regulatory suspicious transaction report.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
