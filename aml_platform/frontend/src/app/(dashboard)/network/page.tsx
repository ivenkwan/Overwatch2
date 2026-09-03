"use client";

import React, { useState, useEffect } from 'react';
import GraphExplorer from '@/components/GraphExplorer';
import { 
  ShieldCheck, 
  BarChart3, 
  Search,
  ExternalLink,
  Loader2,
  AlertCircle
} from 'lucide-react';
import { api } from '@/services/api';

export default function NetworkPage() {
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [searchDepth, setSearchDepth] = useState<number>(2);
  const [isFastMode, setIsFastMode] = useState<boolean>(false);
  const [minNodes, setMinNodes] = useState<number>(0);

  const [graphData, setGraphData] = useState<any[]>([]);
  const [isGraphLoading, setIsGraphLoading] = useState(true);
  const [graphError, setGraphError] = useState<string | null>(null);

  const filteredGraphData = React.useMemo(() => {
    if (minNodes === 0) return graphData;

    // 1. Separate nodes and edges
    const nodes = graphData.filter(el => !el.data.source || !el.data.target);
    const edges = graphData.filter(el => el.data.source && el.data.target);

    // 2. Build adjacency list (treating graph as undirected for components)
    const adj: { [key: string]: string[] } = {};
    nodes.forEach(node => {
      adj[node.data.id] = [];
    });

    edges.forEach(edge => {
      const u = edge.data.source;
      const v = edge.data.target;
      if (adj[u] && adj[v]) {
        adj[u].push(v);
        adj[v].push(u);
      }
    });

    // 3. Find connected components using BFS
    const visited: { [key: string]: boolean } = {};
    const componentIdMap: { [key: string]: number } = {};
    const componentSizes: number[] = [];
    let currentComponentId = 0;

    nodes.forEach(node => {
      const nodeId = node.data.id;
      if (!visited[nodeId]) {
        const comp: string[] = [];
        const queue = [nodeId];
        visited[nodeId] = true;

        while (queue.length > 0) {
          const curr = queue.shift()!;
          comp.push(curr);
          componentIdMap[curr] = currentComponentId;

          const neighbors = adj[curr] || [];
          neighbors.forEach(neighbor => {
            if (!visited[neighbor]) {
              visited[neighbor] = true;
              queue.push(neighbor);
            }
          });
        }

        componentSizes.push(comp.length);
        currentComponentId++;
      }
    });

    // 4. Filter nodes
    const keptNodeIds = new Set<string>();
    nodes.forEach(node => {
      const nodeId = node.data.id;
      const compId = componentIdMap[nodeId];
      if (compId !== undefined && componentSizes[compId] > minNodes) {
        keptNodeIds.add(nodeId);
      }
    });

    // 5. Keep elements
    const filteredNodes = nodes.filter(node => keptNodeIds.has(node.data.id));
    const filteredEdges = edges.filter(edge => keptNodeIds.has(edge.data.source) && keptNodeIds.has(edge.data.target));

    return [...filteredNodes, ...filteredEdges];
  }, [graphData, minNodes]);

  useEffect(() => {
    let isMounted = true;
    setIsGraphLoading(true);
    
    const fetchCall = selectedEntity 
      ? api.fetchGraphNeighborhood(selectedEntity, searchDepth)
      : api.fetchGraphNetwork();

    fetchCall
      .then(res => {
        if (isMounted) {
          setGraphData(res.elements);
          setIsGraphLoading(false);
          setGraphError(null);
        }
      })
      .catch(err => {
        if (isMounted) {
          setGraphError(err.message);
          setIsGraphLoading(false);
        }
      });
    return () => { isMounted = false; };
  }, [selectedEntity, searchDepth]);

  return (
    <>
      <div className={`absolute inset-0 z-0 flex flex-col transition-all duration-500 opacity-100`}>
        {/* Top Workspace Bar */}
        <div className="relative z-20 flex flex-col pointer-events-auto border-b border-slate-800/50 pb-2">
          <div className="px-6 py-4 flex justify-between items-start">
            <div className="flex flex-col items-start shrink-0">
              <div className="flex items-center gap-3 bg-slate-950/80 backdrop-blur-xl border border-slate-800/60 rounded-2xl px-5 py-3 shadow-xl">
                <h3 className="text-lg font-bold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">Graph Network Voyager</h3>
                <div className="h-6 w-[1px] bg-slate-800/80" />
                <select
                  value={minNodes}
                  onChange={(e) => setMinNodes(parseInt(e.target.value))}
                  className="bg-slate-900 border border-slate-700/80 text-slate-300 text-xs rounded-lg px-3 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 font-medium cursor-pointer"
                >
                  <option value={0}>Show All Networks</option>
                  <option value={3}>&gt; 3 nodes</option>
                  <option value={4}>&gt; 4 nodes</option>
                  <option value={5}>&gt; 5 nodes</option>
                </select>
              </div>
              <div className="mt-3 flex items-center gap-2 bg-slate-950/60 backdrop-blur-md px-3 py-1.5 rounded-lg border border-slate-800/50">
                <span className="inline-block h-2 w-2 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.8)] animate-pulse" />
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Visualizing:</span>
                <span className="font-mono text-xs font-bold text-blue-400 truncate max-w-[120px]">{selectedEntity || 'Global Network View'}</span>
              </div>
            </div>
            
            <div className="flex gap-3 bg-slate-950/80 backdrop-blur-xl p-1.5 rounded-2xl border border-slate-800/60 shadow-xl justify-end shrink-0 items-center">
              {/* Depth Control */}
              <div className="flex items-center gap-2 pl-3 pr-2 border-r border-slate-800">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Depth</span>
                <input 
                  type="range" 
                  title="Depth Selection"
                  min="1" 
                  max="5" 
                  value={searchDepth}
                  onChange={(e) => setSearchDepth(parseInt(e.target.value))}
                  disabled={!selectedEntity}
                  className={`w-16 h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer ${!selectedEntity && 'opacity-30 cursor-not-allowed'}`}
                />
                <span className={`text-xs font-bold w-4 text-center ${selectedEntity ? 'text-blue-400' : 'text-slate-500'}`}>{searchDepth}</span>
              </div>

              <div className="flex bg-slate-900/50 p-1 rounded-xl">
                 <button 
                   onClick={() => setIsFastMode(false)}
                   className={`px-5 py-2 rounded-lg text-xs font-bold transition-all shadow-lg ${!isFastMode ? 'bg-blue-600 text-white shadow-blue-500/20' : 'text-slate-400 hover:text-slate-200'}`}
                 >
                   Discovery
                 </button>
                 <button 
                   onClick={() => setIsFastMode(true)}
                   className={`px-4 py-2 rounded-lg text-xs font-bold transition-all shadow-lg ${isFastMode ? 'bg-indigo-600 text-white shadow-indigo-500/20' : 'text-slate-400 hover:text-slate-200'}`}
                 >
                   Fast
                 </button>
              </div>
            </div>
          </div>
        </div>
        
        <div className="flex-1 w-full relative z-10 flex flex-col">
          {isGraphLoading ? (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
              <Loader2 className="w-12 h-12 animate-spin text-blue-500 mb-4" />
              <p className="font-bold">Projecting Network Topology...</p>
              <p className="text-xs opacity-70 mt-2">Loading Apache AGE graph from backend</p>
            </div>
          ) : graphError ? (
            <div className="flex-1 flex flex-col items-center justify-center text-rose-400">
              <AlertCircle className="w-12 h-12 mb-4 opacity-50" />
              <p className="font-bold">Graph Projection Failed</p>
              <p className="text-xs opacity-70 mt-2">{graphError}</p>
            </div>
          ) : (
            <GraphExplorer 
              data={filteredGraphData} 
              isFastMode={isFastMode}
              onNodeClick={(id) => setSelectedEntity(id)}
            />
          )}
        </div>
      </div>

      {/* Contextual Intelligence Sidebar */}
      <aside className={`absolute right-0 top-0 bottom-0 border-l border-slate-800 bg-slate-950/80 backdrop-blur-xl overflow-y-auto transition-all duration-300 w-96 p-8 flex flex-col z-30`}>
        <div className="flex justify-between items-center mb-8">
          <h2 className="text-xs font-bold uppercase tracking-widest text-slate-500">Audit Intelligence</h2>
          <ExternalLink size={14} className="text-slate-600 hover:text-blue-400 cursor-pointer transition-colors" />
        </div>

        {selectedEntity ? (
          <div className="space-y-8 min-w-[280px]">
            <div className="p-6 rounded-2xl bg-gradient-to-br from-blue-600/10 to-transparent border border-blue-500/20 relative overflow-hidden">
              <div className="text-[10px] font-black text-blue-400 mb-2 tracking-widest uppercase">Target Entity</div>
              <div className="text-lg font-mono font-bold leading-none">{selectedEntity}</div>
              <div className="mt-4 flex items-center gap-2">
                 <div className="h-6 w-6 rounded-md bg-blue-500/20 flex items-center justify-center">
                   <ShieldCheck size={14} className="text-blue-500" />
                 </div>
                 <span className="text-[10px] font-bold text-slate-300">Verified Institution</span>
              </div>
              {/* Decorative background logo */}
              <BarChart3 size={120} className="absolute -right-6 -bottom-6 text-blue-500/5 rotate-12" />
            </div>
            
            <div className="space-y-4">
              <div className="text-[10px] text-slate-600 font-black uppercase tracking-widest">Metadata Profile</div>
              <div className="space-y-3">
                {[
                  { label: 'Type', value: 'FIAT_ACCOUNT', color: 'slate' },
                  { label: 'Jurisdiction', value: 'UNITED STATES', color: 'slate' },
                  { label: 'Risk Score', value: '88 / 100', color: 'red' },
                  { label: 'Wallet Count', value: '2 Linked', color: 'blue' },
                ].map(meta => (
                  <div key={meta.label} className="flex justify-between items-center py-2 border-b border-slate-800/50">
                    <span className="text-[11px] font-medium text-slate-500">{meta.label}</span>
                    <span className={`text-[11px] font-bold tracking-tight ${meta.color === 'red' ? 'text-red-500' : meta.color === 'blue' ? 'text-blue-400' : 'text-slate-200'}`}>
                      {meta.value}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex flex-col gap-3">
              <button 
                 className="w-full py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-blue-600/20 active:scale-[0.98]"
                 onClick={() => window.location.href = '/str'}
              >
                PREPARE STR
              </button>
            </div>
          </div>
        ) : (
          <div className="h-[calc(100vh-200px)] flex flex-col items-center justify-center text-slate-700 min-w-[280px]">
            <div className="w-24 h-24 border border-dashed border-slate-800 rounded-2xl mb-6 flex items-center justify-center opacity-40">
              <Search size={32} />
            </div>
            <h4 className="text-sm font-bold text-slate-500 mb-1">No Entity Selected</h4>
            <p className="text-[10px] font-medium max-w-[180px] text-center opacity-60">
              Select a cluster in the graph to begin specific auditing.
            </p>
          </div>
        )}
      </aside>
    </>
  );
}
