import { useState, useEffect, useRef, useCallback } from 'react';
import { Bot, Play, RefreshCw, ChevronDown, ChevronUp, CheckCircle, AlertCircle, Clock } from 'lucide-react';
import { apiClient } from '../services/api';

interface AgentFinding {
  id: number;
  round_number: number;
  attack_prompt: string;
  model_response: string | null;
  verdict: string | null;
  score: number | null;
  escalated: number;
  created_at: string;
}

interface AgentRunOut {
  id: number;
  model_name: string;
  target_category: string | null;
  max_rounds: number;
  status: string;
  rounds_completed: number;
  created_at: string;
  completed_at: string | null;
  findings: AgentFinding[];
}

const CATEGORIES = ['PROMPT_INJECTION', 'JAILBREAK', 'CONTEXT_MANIPULATION', 'DATA_LEAKAGE'];
const VERDICT_COLOR: Record<string, string> = {
  FAIL: 'text-red-400',
  PASS: 'text-green-400',
  UNCERTAIN: 'text-yellow-400',
};

function StatusBadge({ status }: { status: string }) {
  if (status === 'completed') return <span className="flex items-center gap-1 text-green-400 text-xs"><CheckCircle className="w-3 h-3" />Completed</span>;
  if (status === 'running' || status === 'pending') return <span className="flex items-center gap-1 text-yellow-400 text-xs animate-pulse"><Clock className="w-3 h-3" />{status}</span>;
  if (status === 'failed') return <span className="flex items-center gap-1 text-red-400 text-xs"><AlertCircle className="w-3 h-3" />Failed</span>;
  return <span className="text-gray-400 text-xs">{status}</span>;
}

export default function RedTeamAgent() {
  const [modelName, setModelName] = useState('');
  const [category, setCategory] = useState('PROMPT_INJECTION');
  const [maxRounds, setMaxRounds] = useState(3);
  const [generatorModel, setGeneratorModel] = useState('llama3.2');
  const [judgeModel, setJudgeModel] = useState('llama3.2');
  const [pastRuns, setPastRuns] = useState<AgentRunOut[]>([]);
  const [activeRun, setActiveRun] = useState<AgentRunOut | null>(null);
  const [expandedFinding, setExpandedFinding] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  }, []);

  const startPolling = useCallback((runId: number) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const full = await apiClient.get<AgentRunOut>(`/agent/${runId}`).then(r => r.data);
        setActiveRun(full);
        if (full.status === 'completed' || full.status === 'failed') {
          stopPolling();
          setPastRuns(prev => [full, ...prev.filter(r => r.id !== full.id)]);
        }
      } catch { stopPolling(); }
    }, 4000);
  }, [stopPolling]);

  useEffect(() => {
    apiClient.get<AgentRunOut[]>('/agent').then(r => setPastRuns(r.data)).catch(() => {});
    return () => stopPolling();
  }, [stopPolling]);

  const handleStart = async () => {
    if (!modelName.trim()) { setError('Enter a model name.'); return; }
    setError(null);
    setLoading(true);
    try {
      const run = await apiClient.post<AgentRunOut>('/agent', {
        model_name: modelName.trim(),
        target_category: category,
        max_rounds: maxRounds,
        generator_model: generatorModel,
        judge_model: judgeModel,
      }).then(r => r.data);
      setActiveRun(run);
      startPolling(run.id);
    } catch {
      setError('Failed to start agent run.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-5xl mx-auto space-y-8">
        <div className="flex items-center gap-3">
          <Bot className="w-8 h-8 text-red-500" />
          <div>
            <h1 className="text-2xl font-bold">Recursive Red Team Agent</h1>
            <p className="text-gray-400 text-sm">Autonomous adversarial probing that escalates attacks when the model resists</p>
          </div>
        </div>

        {/* Config */}
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 space-y-4">
          <h2 className="text-sm font-semibold text-gray-300">New Agent Run</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Target Model</label>
              <input value={modelName} onChange={e => setModelName(e.target.value)} placeholder="e.g. llama3.2"
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-red-500" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Attack Category</label>
              <select value={category} onChange={e => setCategory(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-red-500">
                {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Generator Model</label>
              <input value={generatorModel} onChange={e => setGeneratorModel(e.target.value)} placeholder="llama3.2"
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-red-500" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Judge Model</label>
              <input value={judgeModel} onChange={e => setJudgeModel(e.target.value)} placeholder="llama3.2"
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-red-500" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Max Rounds (1–10)</label>
              <input type="number" min={1} max={10} value={maxRounds} onChange={e => setMaxRounds(Number(e.target.value))}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-red-500" />
            </div>
          </div>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <button onClick={handleStart} disabled={loading || !modelName.trim()}
            className="flex items-center gap-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 px-5 py-2 rounded-lg text-sm font-medium transition-colors">
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {loading ? 'Starting…' : 'Launch Agent'}
          </button>
        </div>

        {/* Active run */}
        {activeRun && (
          <div className="bg-gray-900 rounded-xl p-5 border border-gray-800 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-semibold">{activeRun.model_name} — {activeRun.target_category}</h2>
                <p className="text-xs text-gray-500">Round {activeRun.rounds_completed}/{activeRun.max_rounds}</p>
              </div>
              <StatusBadge status={activeRun.status} />
            </div>

            {activeRun.findings.length > 0 && (
              <div className="space-y-2">
                {activeRun.findings.map((f, i) => (
                  <div key={f.id} className="bg-gray-800 rounded-lg overflow-hidden">
                    <button onClick={() => setExpandedFinding(expandedFinding === i ? null : i)}
                      className="w-full flex items-center justify-between px-4 py-2.5 text-left">
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-gray-500">Round {f.round_number}</span>
                        <span className={`text-sm font-bold ${VERDICT_COLOR[f.verdict ?? ''] ?? 'text-gray-400'}`}>{f.verdict ?? '…'}</span>
                        {f.escalated ? <span className="text-xs text-orange-400">↑ Escalated</span> : null}
                      </div>
                      {expandedFinding === i ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
                    </button>
                    {expandedFinding === i && (
                      <div className="px-4 pb-4 space-y-2">
                        <p className="text-xs text-gray-500 uppercase tracking-wide">Attack prompt</p>
                        <pre className="bg-gray-900 rounded p-3 text-xs text-gray-300 whitespace-pre-wrap font-mono max-h-32 overflow-auto">{f.attack_prompt}</pre>
                        {f.model_response && <>
                          <p className="text-xs text-gray-500 uppercase tracking-wide">Model response</p>
                          <pre className="bg-gray-900 rounded p-3 text-xs text-gray-300 whitespace-pre-wrap font-mono max-h-32 overflow-auto">{f.model_response}</pre>
                        </>}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Past runs */}
        {pastRuns.filter(r => r.id !== activeRun?.id).length > 0 && (
          <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
            <h2 className="text-sm font-medium text-gray-400 mb-3">Past Runs</h2>
            <div className="space-y-2">
              {pastRuns.filter(r => r.id !== activeRun?.id).map(run => (
                <button key={run.id} onClick={() => setActiveRun(run)}
                  className="w-full flex items-center justify-between px-4 py-3 bg-gray-800 hover:bg-gray-700 rounded-lg text-left transition-colors">
                  <div>
                    <p className="text-sm font-medium">{run.model_name} — {run.target_category}</p>
                    <p className="text-xs text-gray-500">{run.rounds_completed}/{run.max_rounds} rounds · {new Date(run.created_at).toLocaleString()}</p>
                  </div>
                  <StatusBadge status={run.status} />
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
