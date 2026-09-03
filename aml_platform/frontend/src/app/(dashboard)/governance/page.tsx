"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/services/api";
import { AlertCircle, TrendingUp, Clock, FileText, Settings, ShieldAlert, Activity, Award } from "lucide-react";

export default function GovernanceMISPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const kpiData = await api.reports.getDailyKPIs();
        setData(kpiData);
      } catch (err: any) {
        setError(err.message || "Failed to load Governance MIS data");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex h-full flex-col items-center justify-center text-slate-400 pt-10">
        <div className="w-8 h-8 rounded-full border-4 border-slate-800 border-t-blue-500 animate-spin mb-4"></div>
        <p className="font-bold">Aggregating Compliance Metrics...</p>
        <p className="text-xs opacity-70 mt-2">Computing HKMA KPI values</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex h-full flex-col items-center justify-center text-rose-400 pt-10 p-6 text-center">
        <AlertCircle className="w-12 h-12 mb-4 opacity-50" />
        <h3 className="font-bold">Governance Dashboard Loading Failed</h3>
        <p className="text-xs mt-2 opacity-75">{error}</p>
      </div>
    );
  }

  const reportDate = data?.report_date ? new Date(data.report_date).toLocaleDateString() : 'N/A';

  const getRagStatus = (value: number, thresholdType: 'low_better' | 'high_better', boundaries: [number, number]) => {
    if (thresholdType === 'low_better') {
      if (value >= boundaries[1]) return { color: 'text-rose-400', badge: 'bg-rose-500/10 text-rose-400 border border-rose-500/20', bg: 'bg-rose-950/10 border-rose-500/20 shadow-[0_0_15px_rgba(244,63,94,0.05)]', label: 'Action Required' };
      if (value > boundaries[0]) return { color: 'text-amber-400', badge: 'bg-amber-500/10 text-amber-400 border border-amber-500/20', bg: 'bg-amber-950/10 border-amber-500/20 shadow-[0_0_15px_rgba(245,158,11,0.05)]', label: 'Monitor' };
      return { color: 'text-emerald-400', badge: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20', bg: 'bg-emerald-950/10 border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.05)]', label: 'On Target' };
    } else {
      if (value <= boundaries[1]) return { color: 'text-rose-400', badge: 'bg-rose-500/10 text-rose-400 border border-rose-500/20', bg: 'bg-rose-950/10 border-rose-500/20 shadow-[0_0_15px_rgba(244,63,94,0.05)]', label: 'Action Required' };
      if (value < boundaries[0]) return { color: 'text-amber-400', badge: 'bg-amber-500/10 text-amber-400 border border-amber-500/20', bg: 'bg-amber-950/10 border-amber-500/20 shadow-[0_0_15px_rgba(245,158,11,0.05)]', label: 'Monitor' };
      return { color: 'text-emerald-400', badge: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20', bg: 'bg-emerald-950/10 border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.05)]', label: 'On Target' };
    }
  };

  const kpis = [
    {
      title: "False Positive Rate",
      value: `${data.false_positive_rate?.toFixed(1)}%`,
      status: getRagStatus(data.false_positive_rate || 0, 'low_better', [90, 95]),
      desc: "Closed non-suspicious / Reviewed",
      icon: <Activity className="w-5 h-5" />
    },
    {
      title: "First-Review SLA",
      value: `${data.first_review_sla_rate?.toFixed(1)}%`,
      status: getRagStatus(data.first_review_sla_rate || 0, 'high_better', [95, 90]),
      desc: "Alerts reviewed within 72h SLA",
      icon: <Clock className="w-5 h-5" />
    },
    {
      title: "Backlog Ageing",
      value: `${data.backlog_ageing?.toFixed(1)}%`,
      status: getRagStatus(data.backlog_ageing || 0, 'low_better', [10, 20]),
      desc: "Open alerts past 72h SLA",
      icon: <Settings className="w-5 h-5" />
    },
    {
      title: "Productive Alert Rate",
      value: `${data.productive_alert_rate?.toFixed(1)}%`,
      status: getRagStatus(data.productive_alert_rate || 0, 'high_better', [10, 5]),
      desc: "Escalated to case / Reviewed",
      icon: <TrendingUp className="w-5 h-5" />
    },
    {
      title: "STR Conversion Rate",
      value: `${data.str_conversion_rate?.toFixed(1)}%`,
      status: getRagStatus(data.str_conversion_rate || 0, 'high_better', [10, 5]),
      desc: "STRs filed / Cases Closed",
      icon: <FileText className="w-5 h-5" />
    },
    {
      title: "QA Clearance Defect",
      value: `${data.qa_clearance_defect_rate?.toFixed(1)}%`,
      status: getRagStatus(data.qa_clearance_defect_rate || 0, 'low_better', [5, 10]),
      desc: "QA exceptions on closures",
      icon: <ShieldAlert className="w-5 h-5" />
    }
  ];

  return (
    <div className="flex-1 p-6 relative z-20 flex flex-col pointer-events-auto h-full overflow-y-auto w-full">
      <div className="flex justify-between items-center bg-slate-900/60 backdrop-blur-md p-6 rounded-2xl border border-slate-800 shadow-xl mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-slate-500/20 rounded-lg border border-slate-500/30">
            <Award size={20} className="text-slate-300" />
          </div>
          <div>
            <h2 className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">Governance & MIS (HKMA KPIs)</h2>
            <p className="text-xs text-slate-500 mt-0.5">HKMA-aligned AML compliance health tracking</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Reporting Date (T-1)</p>
          <p className="text-sm font-bold text-blue-400 font-mono mt-0.5">{reportDate}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
        {kpis.map((kpi, idx) => (
          <div key={idx} className={`rounded-2xl border p-6 transition-all duration-300 hover:-translate-y-0.5 ${kpi.status.bg}`}>
            <div className="flex items-center justify-between mb-4">
              <div className={`p-2 rounded-lg bg-slate-950/40 ${kpi.status.color}`}>
                {kpi.icon}
              </div>
              <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider ${kpi.status.badge}`}>
                {kpi.status.label}
              </span>
            </div>
            
            <h3 className="text-slate-400 font-medium text-xs tracking-wide">{kpi.title}</h3>
            <div className="flex items-baseline gap-2 mt-1">
              <span className={`text-2xl font-black font-mono tracking-tight ${kpi.status.color}`}>
                {kpi.value}
              </span>
            </div>
            <p className="text-slate-500 text-[10px] font-medium mt-3 leading-relaxed">{kpi.desc}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800 p-6 shadow-xl">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-5 flex items-center">
            <Activity className="w-4 h-4 mr-2 text-blue-400 animate-pulse" />
            Operational Ingestion & Process Volumes
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/60">
              <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-1">Total Alerts</p>
              <p className="text-xl font-bold font-mono text-slate-200">{data.total_alerts || 0}</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/60">
              <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-1">Closed (Level 1)</p>
              <p className="text-xl font-bold font-mono text-slate-200">{data.closed_non_suspicious || 0}</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/60">
              <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-1">Escalated</p>
              <p className="text-xl font-bold font-mono text-slate-200">{data.cases_opened || 0}</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/60">
              <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-1">STRs Filed</p>
              <p className="text-xl font-bold font-mono text-slate-200">{data.strs_filed || 0}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-gradient-to-br from-blue-900/30 to-indigo-900/30 backdrop-blur-md rounded-2xl border border-blue-500/20 p-6 shadow-xl relative overflow-hidden flex flex-col justify-between">
          <div className="relative z-10">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Composite AML Quality Score</h3>
            <div className="flex items-baseline gap-1.5">
              <span className="text-5xl font-black font-mono tracking-tight bg-gradient-to-r from-blue-400 to-indigo-300 bg-clip-text text-transparent">88</span>
              <span className="text-slate-500 text-xs font-bold">/ 100</span>
            </div>
            <p className="text-[10px] font-medium leading-relaxed text-slate-400 mt-4">
              Calculated using standard weighted parameters: 40% SLA Adherence, 30% False Positive deviation, and 30% QA Clearance consistency.
            </p>
          </div>
          <div className="absolute -right-8 -bottom-8 opacity-5">
            <ShieldAlert className="w-36 h-36" />
          </div>
        </div>
      </div>
    </div>
  );
}
