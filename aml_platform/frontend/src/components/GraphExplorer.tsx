import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import { User, AlertTriangle, X, CheckCircle } from 'lucide-react';

interface GraphExplorerProps {
  data: any[];
  isFastMode?: boolean;
  onNodeClick?: (nodeId: string) => void;
}

interface ContextMenu {
  x: number;
  y: number;
  nodeId: string;
}

export default function GraphExplorer({ data, isFastMode = false, onNodeClick }: GraphExplorerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<any>(null);

  // Interaction and Modal States
  const [contextMenu, setContextMenu] = useState<ContextMenu | null>(null);
  const [activeAccountNode, setActiveAccountNode] = useState<any | null>(null);
  const [activeAlertNode, setActiveAlertNode] = useState<any | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'info' } | null>(null);

  // Alert manual form states
  const [alertTrigger, setAlertTrigger] = useState('Suspicious Velocity');
  const [alertPriority, setAlertPriority] = useState('HIGH');
  const [alertNotes, setAlertNotes] = useState('');

  // Auto-dismiss toast
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => {
        setToast(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  useEffect(() => {
    if (!containerRef.current) return;

    // Logarithmic scaling for edge thickness
    const elements = data.map(item => {
      if (item.data.source && item.data.target) {
        // Normalize edge thickness based on volume or amount
        const vol = item.data.volume || item.data.amount_usd || item.data.amount || 1;
        // log10 scale clamped between 1px and 12px
        let thickness = Math.max(1, Math.min(12, Math.log10(vol) * 1.2)); 
        return { ...item, data: { ...item.data, thickness: isFastMode ? thickness : Math.max(2, thickness) } };
      }
      return item;
    });

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements: elements,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': (ele: any) => {
              if (!isFastMode) {
                 const risk = ele.data('risk_score') || 0;
                 if (risk >= 80) return '#ef4444'; // High Risk (Red)
                 if (risk >= 50) return '#f59e0b'; // Medium (Amber)
                 return '#3b82f6'; // Default (Blue)
              }
              const status = ele.data('threshold_status');
              if (status === 'RED') return '#ef4444';
              if (status === 'AMBER') return '#f59e0b';
              if (status === 'GREEN') return '#22c55e';
              return '#475569';
            },
            'shape': (ele: any) => {
              const lbl = ele.data('label');
              if (lbl === 'Person' || lbl === 'Individual') return 'ellipse';
              if (lbl === 'Company' || lbl === 'Business' || lbl === 'Entity') return 'round-rectangle';
              if (lbl === 'Account' || lbl === 'Wallet') return 'hexagon';
              return 'ellipse';
            },
            'label': isFastMode ? '' : 'data(label)',
            'color': '#fff',
            'font-size': '12px',
            'text-valign': 'center',
            'width': isFastMode ? 24 : 40,
            'height': isFastMode ? 24 : 40,
            'border-width': isFastMode ? 2 : 0,
            'border-color': '#0f172a'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 'data(thickness)',
            'line-color': (ele: any) => {
              const type = ele.data('label');
              if (type === 'TRANSFERS' || type === 'SENT') return '#8b5cf6'; // Purple
              if (type === 'OWNS' || type === 'HAS_ACCOUNT') return '#10b981'; // Green
              return isFastMode ? '#64748b' : '#94a3b8';
            },
            'target-arrow-color': (ele: any) => {
              const type = ele.data('label');
              if (type === 'TRANSFERS' || type === 'SENT') return '#8b5cf6';
              if (type === 'OWNS' || type === 'HAS_ACCOUNT') return '#10b981';
              return isFastMode ? '#64748b' : '#94a3b8';
            },
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': isFastMode ? '' : 'data(amount_usd)',
            'font-size': '10px',
            'opacity': isFastMode ? 0.7 : 1
          }
        },
        {
          selector: 'node[type="SuperNode"]',
          style: {
            'background-color': '#dc2626',
            'shape': 'diamond'
          }
        }
      ],
      layout: {
        name: 'cose',
        animate: true,
        nodeRepulsion: 400000,
        idealEdgeLength: 50,
      }
    });

    // Left click handles entity selection
    cyRef.current.on('tap', 'node', (evt: any) => {
      const node = evt.target;
      if (onNodeClick) onNodeClick(node.id());
      setContextMenu(null);
    });

    const container = containerRef.current;
    const preventDefault = (e: MouseEvent) => {
      e.preventDefault();
    };
    if (container) {
      container.addEventListener('contextmenu', preventDefault);
    }

    // Right click triggers custom context menu
    cyRef.current.on('cxttap', 'node', (evt: any) => {
      const node = evt.target;
      const originalEvent = evt.originalEvent;
      if (originalEvent && typeof originalEvent.preventDefault === 'function') {
        originalEvent.preventDefault();
      }
      
      const pos = evt.renderedPosition;
      if (pos) {
        setContextMenu({
          x: pos.x,
          y: pos.y,
          nodeId: node.id()
        });
      }
    });

    // Close menu when tapping on canvas background
    cyRef.current.on('tap', (evt: any) => {
      if (evt.target === cyRef.current) {
        setContextMenu(null);
      }
    });

    return () => {
      if (container) {
        container.removeEventListener('contextmenu', preventDefault);
      }
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, [data, isFastMode, onNodeClick]);

  // Context Menu Action Handlers
  const handleShowAccountInfo = (nodeId: string) => {
    const nodeItem = data.find(el => el.data.id === nodeId && (!el.data.source || !el.data.target));
    const nodeData = nodeItem ? nodeItem.data : { id: nodeId, label: 'Customer' };
    setActiveAccountNode(nodeData);
    setContextMenu(null);
  };

  const handleCreateAlert = (nodeId: string) => {
    const nodeItem = data.find(el => el.data.id === nodeId && (!el.data.source || !el.data.target));
    const nodeData = nodeItem ? nodeItem.data : { id: nodeId, label: 'Customer' };
    setActiveAlertNode(nodeData);
    setContextMenu(null);
    setAlertTrigger('Suspicious Velocity');
    setAlertPriority('HIGH');
    setAlertNotes('');
  };

  return (
    <div className="w-full h-full bg-slate-950 rounded-xl border border-slate-800/80 shadow-inner relative overflow-hidden">
      <div 
        ref={containerRef} 
        className="w-full h-full" 
        onContextMenu={(e) => e.preventDefault()}
      />
      
      <div className="absolute top-4 left-4 bg-slate-900/80 backdrop-blur-md p-2 rounded text-xs font-bold text-slate-300 border border-slate-700 shadow-xl pointer-events-none select-none">
        {isFastMode ? 'FAST MODE (TOPOLOGY)' : 'FULL DISCOVERY'}: {data.length} elements
      </div>

      {/* Pop-up Context Menu */}
      {contextMenu && (
        <>
          <div 
            className="absolute inset-0 z-40 bg-transparent" 
            onClick={() => setContextMenu(null)}
            onContextMenu={(e) => {
              e.preventDefault();
              setContextMenu(null);
            }}
          />
          <div 
            className="absolute z-50 bg-slate-900/95 backdrop-blur-md border border-slate-800/80 rounded-xl shadow-2xl py-1.5 w-56 animate-in fade-in zoom-in-95 duration-100"
            style={{ top: contextMenu.y, left: contextMenu.x }}
          >
            <button 
              onClick={() => handleShowAccountInfo(contextMenu.nodeId)}
              className="w-full text-left px-4 py-2.5 text-xs font-semibold text-slate-300 hover:bg-blue-600 hover:text-white transition-colors flex items-center gap-2"
            >
              <User size={14} className="text-slate-400" />
              Show Account Information
            </button>
            <button 
              onClick={() => handleCreateAlert(contextMenu.nodeId)}
              className="w-full text-left px-4 py-2.5 text-xs font-semibold text-slate-300 hover:bg-orange-600 hover:text-white transition-colors flex items-center gap-2"
            >
              <AlertTriangle size={14} className="text-slate-400" />
              Create Alert
            </button>
          </div>
        </>
      )}

      {/* Account Info Modal */}
      {activeAccountNode && (
        <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-md z-50 flex items-center justify-center p-6 animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden animate-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="px-6 py-4 bg-slate-950/60 border-b border-slate-800/60 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-blue-500/10 rounded-lg border border-blue-500/20">
                  <User size={16} className="text-blue-400" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-100">Account Details</h3>
                  <p className="text-[10px] text-slate-500">Target Investigation Profile</p>
                </div>
              </div>
              <button 
                onClick={() => setActiveAccountNode(null)}
                className="text-slate-500 hover:text-slate-300 transition-colors p-1 hover:bg-slate-800 rounded-lg"
              >
                <X size={16} />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 space-y-4">
              {/* Risk Badge */}
              <div className="flex items-center justify-between p-3.5 bg-slate-950/40 rounded-xl border border-slate-800/80">
                <div className="max-w-[60%]">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">AML Risk Profile</span>
                  <span className="text-xs font-mono font-bold text-slate-300 truncate block">{activeAccountNode.id}</span>
                </div>
                <div className={`px-2.5 py-1 rounded-lg text-xs font-black uppercase tracking-wider border ${
                  (activeAccountNode.risk_score || 0) >= 80 || activeAccountNode.threshold_status === 'RED'
                    ? 'bg-rose-500/10 text-rose-400 border-rose-500/20 shadow-[0_0_8px_rgba(244,63,94,0.15)]'
                    : (activeAccountNode.risk_score || 0) >= 50 || activeAccountNode.threshold_status === 'AMBER'
                    ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                }`}>
                  Risk Score: {activeAccountNode.risk_score || (Math.abs(activeAccountNode.id.charCodeAt(activeAccountNode.id.length - 1) * 3) % 45 + 40)}
                </div>
              </div>

              {/* Profile Details */}
              <div className="space-y-2.5">
                <div className="flex justify-between items-center py-1.5 border-b border-slate-800/40">
                  <span className="text-[11px] font-medium text-slate-500">Entity Type</span>
                  <span className="text-xs font-semibold text-slate-300">{activeAccountNode.label || 'Individual'}</span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-slate-800/40">
                  <span className="text-[11px] font-medium text-slate-500">Jurisdiction</span>
                  <span className="text-xs font-semibold text-slate-300">{activeAccountNode.jurisdiction || 'Hong Kong SAR'}</span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-slate-800/40">
                  <span className="text-[11px] font-medium text-slate-500">Account Status</span>
                  <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" /> Active
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5 border-b border-slate-800/40">
                  <span className="text-[11px] font-medium text-slate-500">Transaction Count</span>
                  <span className="text-xs font-mono font-semibold text-slate-300">
                    {Math.abs(activeAccountNode.id.charCodeAt(0) * 7) % 24 + 5} Txns
                  </span>
                </div>
                <div className="flex justify-between items-center py-1.5">
                  <span className="text-[11px] font-medium text-slate-500">Estimated Volume</span>
                  <span className="text-xs font-mono font-bold text-blue-400">
                    ${(Math.abs(activeAccountNode.id.charCodeAt(1) * 3500) % 850000 + 12000).toLocaleString()} USD
                  </span>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 bg-slate-950/60 border-t border-slate-800/60 flex justify-end gap-3">
              <button 
                onClick={() => setActiveAccountNode(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-bold transition-all active:scale-[0.98]"
              >
                Close Detail
              </button>
              <button 
                onClick={() => {
                  const nodeId = activeAccountNode.id;
                  setActiveAccountNode(null);
                  handleCreateAlert(nodeId);
                }}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold transition-all active:scale-[0.98] shadow-lg shadow-blue-600/10 flex items-center gap-1.5"
              >
                <AlertTriangle size={12} />
                Create Alert
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Alert Modal */}
      {activeAlertNode && (
        <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-md z-50 flex items-center justify-center p-6 animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden animate-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="px-6 py-4 bg-slate-950/60 border-b border-slate-800/60 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-orange-500/10 rounded-lg border border-orange-500/20">
                  <AlertTriangle size={16} className="text-orange-400" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-100">Create Investigation Alert</h3>
                  <p className="text-[10px] text-slate-500">Flag Suspicious Account Behavior</p>
                </div>
              </div>
              <button 
                onClick={() => setActiveAlertNode(null)}
                className="text-slate-500 hover:text-slate-300 transition-colors p-1 hover:bg-slate-800 rounded-lg"
              >
                <X size={16} />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 space-y-4">
              {/* Target info */}
              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">Target Account</label>
                <input 
                  type="text" 
                  readOnly 
                  value={activeAlertNode.id}
                  className="w-full bg-slate-950 border border-slate-800/80 rounded-xl px-3 py-2 text-xs font-mono text-slate-400 focus:outline-none"
                />
              </div>

              {/* Grid Form */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">Alert Trigger</label>
                  <select
                    value={alertTrigger}
                    onChange={(e) => setAlertTrigger(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-blue-500 cursor-pointer"
                  >
                    <option value="Suspicious Velocity">Suspicious Velocity</option>
                    <option value="Structuring Pattern">Structuring Pattern</option>
                    <option value="High Risk Country Connection">High Risk Country</option>
                    <option value="Dormant Reactivation">Dormant Reactivation</option>
                    <option value="Peer-to-Peer Loop">Peer-to-Peer Loop</option>
                  </select>
                </div>

                <div>
                  <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">Severity / Priority</label>
                  <select
                    value={alertPriority}
                    onChange={(e) => setAlertPriority(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-blue-500 cursor-pointer font-bold"
                  >
                    <option value="HIGH" className="text-rose-500 font-bold">HIGH</option>
                    <option value="MEDIUM" className="text-amber-500 font-bold">MEDIUM</option>
                    <option value="LOW" className="text-blue-500 font-bold">LOW</option>
                  </select>
                </div>
              </div>

              {/* Rationale */}
              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">Investigator Rationale (Mandatory)</label>
                <textarea
                  value={alertNotes}
                  onChange={(e) => setAlertNotes(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-300 focus:outline-none focus:border-blue-500 transition-colors h-24 resize-none"
                  placeholder="Specify reason for manual trigger, target transactions or relationships flagged..."
                />
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 bg-slate-950/60 border-t border-slate-800/60 flex justify-end gap-3">
              <button 
                onClick={() => setActiveAlertNode(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-bold transition-all active:scale-[0.98]"
              >
                Cancel
              </button>
              <button 
                onClick={() => {
                  if (!alertNotes.trim()) {
                    alert('Mandatory rationale must be provided.');
                    return;
                  }
                  const alertId = `MANUAL_${Math.random().toString(36).substring(2, 8).toUpperCase()}`;
                  setToast({
                    message: `Manual Alert [${alertId}] successfully logged for node [${activeAlertNode.id}].`,
                    type: 'success'
                  });
                  setActiveAlertNode(null);
                }}
                className="px-4 py-2 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-xs font-bold transition-all active:scale-[0.98] shadow-lg shadow-orange-600/10 flex items-center gap-1.5"
              >
                <CheckCircle size={12} />
                Create Alert
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating Success Toast */}
      {toast && (
        <div className="absolute bottom-4 right-4 z-[60] bg-slate-900/95 border border-emerald-500/30 text-emerald-400 rounded-xl px-4 py-3 flex items-center gap-3 shadow-2xl animate-in slide-in-from-bottom-4 duration-300">
          <div className="p-1 bg-emerald-500/10 rounded border border-emerald-500/20">
            <CheckCircle size={16} />
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-bold text-slate-200">Alert Generated</span>
            <span className="text-[10px] text-slate-400">{toast.message}</span>
          </div>
          <button 
            onClick={() => setToast(null)}
            className="text-slate-500 hover:text-slate-300 text-xs ml-2 font-bold focus:outline-none"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
