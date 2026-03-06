import { useState } from 'react';
import { LayoutDashboard, Plus, Trash2, Wifi, WifiOff, Sparkles, X, AlertTriangle, ArrowRight, Flag, Loader2 } from 'lucide-react';
import { useBoardStore } from '../../store/boardStore.ts';
import { ColorPicker } from '../ui/ColorPicker.tsx';
import { TAG_COLORS } from '../../types/index.ts';

interface InsightsResult {
  insights: string | string[];
  suggested_next: string[];
  risk_flags: string[];
  summary: string;
  model?: string;
}

export function Sidebar() {
  const { projects, activeProjectId, isGlobalOverview, serverAvailable,
          setActiveProject, setGlobalOverview, createProject, deleteProject } = useBoardStore();
  const [creating, setCreating]   = useState(false);
  const [newName, setNewName]     = useState('');
  const [newColor, setNewColor]   = useState(TAG_COLORS[6]); // indigo

  const [insightsOpen, setInsightsOpen]   = useState(false);
  const [insightsData, setInsightsData]   = useState<InsightsResult | null>(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [insightsError, setInsightsError] = useState<string | null>(null);

  const handleCreate = () => {
    if (!newName.trim()) return;
    createProject(newName.trim(), newColor);
    setNewName('');
    setCreating(false);
  };

  const handleInsights = async () => {
    setInsightsOpen(true);
    setInsightsData(null);
    setInsightsError(null);
    setInsightsLoading(true);
    try {
      const res = await fetch('/api/insights', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ message: `HTTP ${res.status}` }));
        throw new Error(err.message ?? err.error ?? `HTTP ${res.status}`);
      }
      const data = await res.json();
      setInsightsData(data);
    } catch (e: unknown) {
      setInsightsError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setInsightsLoading(false);
    }
  };

  return (
    <aside className="w-56 flex-shrink-0 bg-white border-r border-gray-100 flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-gray-100">
        <h2 className="text-lg font-bold text-gray-900 tracking-tight">OmniBoard</h2>
        <div className="flex items-center gap-1 mt-0.5">
          {serverAvailable
            ? <Wifi size={10} className="text-green-500" />
            : <WifiOff size={10} className="text-amber-400" />}
          <span className="text-[10px] text-gray-400">{serverAvailable ? 'Synced' : 'Offline (localStorage)'}</span>
        </div>
      </div>

      {/* Global Overview */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        <button
          onClick={() => setGlobalOverview(true)}
          className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
            isGlobalOverview
              ? 'bg-indigo-50 text-indigo-700'
              : 'text-gray-600 hover:bg-gray-50'
          }`}
        >
          <LayoutDashboard size={15} />
          Global Overview
        </button>

        <div className="pt-3 pb-1">
          <span className="px-3 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">Projects</span>
        </div>

        {projects.map(project => (
          <div key={project.id} className="flex items-center gap-1 group">
            <button
              onClick={() => setActiveProject(project.id)}
              className={`flex-1 flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                activeProjectId === project.id && !isGlobalOverview
                  ? 'bg-indigo-50 text-indigo-700 font-medium'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              <span
                className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: project.color }}
              />
              <span className="truncate">{project.name}</span>
            </button>
            <button
              onClick={() => {
                if (confirm(`Delete "${project.name}" and all its cards?`)) {
                  deleteProject(project.id);
                }
              }}
              className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-opacity"
            >
              <Trash2 size={12} />
            </button>
          </div>
        ))}

        {/* New project */}
        {creating ? (
          <div className="px-2 py-2 space-y-2">
            <input
              className="w-full px-2 py-1.5 text-sm border border-indigo-300 rounded-lg outline-none bg-white"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleCreate(); if (e.key === 'Escape') setCreating(false); }}
              placeholder="Project name"
              autoFocus
            />
            <ColorPicker value={newColor} onChange={setNewColor} />
            <div className="flex gap-2">
              <button
                onClick={handleCreate}
                className="flex-1 py-1 text-xs bg-indigo-500 text-white rounded-lg hover:bg-indigo-600"
              >
                Create
              </button>
              <button
                onClick={() => setCreating(false)}
                className="flex-1 py-1 text-xs text-gray-500 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setCreating(true)}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-indigo-600 hover:bg-gray-50 rounded-lg transition-colors"
          >
            <Plus size={14} /> New project
          </button>
        )}
      </nav>

      {/* Footer */}
      <div className="px-3 py-3 border-t border-gray-100 space-y-2">
        <button
          onClick={handleInsights}
          disabled={!serverAvailable}
          title={serverAvailable ? 'Get AI insights on your board' : 'Server offline — start the API server first'}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-colors bg-indigo-50 text-indigo-700 hover:bg-indigo-100 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Sparkles size={14} />
          AI Insights
        </button>
        <p className="text-[10px] text-gray-400 px-1">HideItEquorperated · OmniBoard</p>
      </div>

      {/* AI Insights panel */}
      {insightsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[80vh] flex flex-col">
            {/* Panel header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-indigo-500" />
                <h3 className="font-semibold text-gray-900">AI Board Insights</h3>
                {insightsData?.model && (
                  <span className="text-[10px] text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">{insightsData.model}</span>
                )}
              </div>
              <button onClick={() => setInsightsOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X size={16} />
              </button>
            </div>

            <div className="overflow-y-auto flex-1 px-5 py-4 space-y-5">
              {insightsLoading && (
                <div className="flex flex-col items-center justify-center py-12 text-gray-400 gap-3">
                  <Loader2 size={28} className="animate-spin text-indigo-400" />
                  <p className="text-sm">Analysing your board with Ollama…</p>
                  <p className="text-xs text-gray-300">This may take 10–30 seconds on first run</p>
                </div>
              )}

              {insightsError && (
                <div className="rounded-xl bg-red-50 border border-red-100 p-4 text-sm text-red-700 space-y-2">
                  <p className="font-medium">Could not get insights</p>
                  <p className="text-xs text-red-500 font-mono break-all">{insightsError}</p>
                  {insightsError.toLowerCase().includes('ollama') || insightsError.includes('503') || insightsError.includes('connect') ? (
                    <p className="text-xs text-red-500 pt-1">Make sure Ollama is running: <code className="bg-red-100 px-1 rounded">ollama serve</code> and pull a model: <code className="bg-red-100 px-1 rounded">ollama pull llama3.2</code></p>
                  ) : null}
                </div>
              )}

              {insightsData && (
                <>
                  {/* Summary */}
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Summary</p>
                    <p className="text-sm text-gray-700 leading-relaxed">{insightsData.summary}</p>
                  </div>

                  {/* Full insights */}
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Analysis</p>
                    {Array.isArray(insightsData.insights) ? (
                      <ul className="space-y-1.5">
                        {insightsData.insights.map((item, i) => (
                          <li key={i} className="text-sm text-gray-700 leading-relaxed flex items-start gap-2">
                            <span className="text-indigo-300 mt-1 flex-shrink-0">•</span>{item}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{insightsData.insights}</p>
                    )}
                  </div>

                  {/* Suggested next actions */}
                  {insightsData.suggested_next?.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Suggested Next Actions</p>
                      <ul className="space-y-1.5">
                        {insightsData.suggested_next.map((action, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                            <ArrowRight size={13} className="text-indigo-400 mt-0.5 flex-shrink-0" />
                            {action}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Risk flags */}
                  {insightsData.risk_flags?.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Risk Flags</p>
                      <ul className="space-y-1.5">
                        {insightsData.risk_flags.map((flag, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-amber-700">
                            <AlertTriangle size={13} className="text-amber-400 mt-0.5 flex-shrink-0" />
                            {flag}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Panel footer */}
            <div className="px-5 py-3 border-t border-gray-100 flex justify-between items-center">
              <p className="text-[10px] text-gray-400">Powered by Ollama · runs 100% locally</p>
              <div className="flex gap-2">
                {insightsData && (
                  <button
                    onClick={handleInsights}
                    className="px-3 py-1.5 text-xs text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors flex items-center gap-1"
                  >
                    <Flag size={11} /> Refresh
                  </button>
                )}
                <button
                  onClick={() => setInsightsOpen(false)}
                  className="px-3 py-1.5 text-xs bg-gray-100 text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
