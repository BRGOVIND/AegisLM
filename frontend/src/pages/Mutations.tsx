import { useState, useEffect } from 'react';
import { Shuffle, Play, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';
import { getAttacks, apiClient } from '../services/api';
import type { Attack } from '../types';

interface Strategy {
  name: string;
  description: string;
}

interface MutatedPrompt {
  strategy: string;
  description: string;
  prompt: string;
}

interface MutationRunResult {
  strategy: string;
  prompt: string;
  response: string;
  verdict: string;
  score: number;
  latency_ms: number;
}

const VERDICT_COLOR: Record<string, string> = {
  PASS: 'text-green-400',
  FAIL: 'text-red-400',
  UNCERTAIN: 'text-yellow-400',
};

export default function Mutations() {
  const [attacks, setAttacks] = useState<Attack[]>([]);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedAttack, setSelectedAttack] = useState<number | null>(null);
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([]);
  const [modelName, setModelName] = useState('');
  const [mutations, setMutations] = useState<MutatedPrompt[]>([]);
  const [runResults, setRunResults] = useState<MutationRunResult[]>([]);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAttacks().then(res => {
      const all: Attack[] = Object.values(res.categories).flat();
      setAttacks(all);
    }).catch(() => {});
    apiClient.get<Strategy[]>('/mutations/strategies').then(r => setStrategies(r.data)).catch(() => {});
  }, []);

  const toggleStrategy = (name: string) => {
    setSelectedStrategies(prev =>
      prev.includes(name) ? prev.filter(s => s !== name) : [...prev, name]
    );
  };

  const handleGenerate = async () => {
    if (!selectedAttack) { setError('Select an attack first.'); return; }
    setError(null);
    setLoading(true);
    setRunResults([]);
    try {
      const res = await apiClient.post<MutatedPrompt[]>('/mutations/generate', {
        attack_id: selectedAttack,
        strategies: selectedStrategies.length ? selectedStrategies : undefined,
      });
      setMutations(res.data);
    } catch {
      setError('Failed to generate mutations.');
    } finally {
      setLoading(false);
    }
  };

  const handleRun = async () => {
    if (!selectedAttack || !modelName.trim()) { setError('Select an attack and enter a model name.'); return; }
    setError(null);
    setRunning(true);
    try {
      const res = await apiClient.post<MutationRunResult[]>('/mutations/run', {
        attack_id: selectedAttack,
        model_name: modelName.trim(),
        strategies: selectedStrategies.length ? selectedStrategies : undefined,
      });
      setRunResults(res.data);
      setMutations([]);
    } catch {
      setError('Failed to run mutations — ensure Ollama is running.');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-5xl mx-auto space-y-8">
        <div className="flex items-center gap-3">
          <Shuffle className="w-8 h-8 text-red-500" />
          <div>
            <h1 className="text-2xl font-bold">Prompt Mutation Engine</h1>
            <p className="text-gray-400 text-sm">Generate and test obfuscated variants of attack prompts</p>
          </div>
        </div>

        {/* Config */}
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Attack</label>
              <select
                value={selectedAttack ?? ''}
                onChange={e => setSelectedAttack(Number(e.target.value) || null)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-red-500"
              >
                <option value="">Select an attack…</option>
                {attacks.map(a => (
                  <option key={a.id} value={a.id}>{a.name} ({a.category})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Model (for Run)</label>
              <input
                type="text"
                value={modelName}
                onChange={e => setModelName(e.target.value)}
                placeholder="e.g. llama3.2"
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-red-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-2">Mutation Strategies (all if none selected)</label>
            <div className="flex flex-wrap gap-2">
              {strategies.map(s => (
                <button
                  key={s.name}
                  onClick={() => toggleStrategy(s.name)}
                  title={s.description}
                  className={`px-3 py-1.5 rounded-full text-xs border transition-colors ${
                    selectedStrategies.includes(s.name)
                      ? 'bg-red-600 border-red-500 text-white'
                      : 'bg-gray-800 border-gray-700 text-gray-300 hover:border-gray-500'
                  }`}
                >
                  {s.name.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <div className="flex gap-3">
            <button
              onClick={handleGenerate}
              disabled={loading || !selectedAttack}
              className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 px-4 py-2 rounded-lg text-sm transition-colors"
            >
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Shuffle className="w-4 h-4" />}
              Preview Mutations
            </button>
            <button
              onClick={handleRun}
              disabled={running || !selectedAttack || !modelName.trim()}
              className="flex items-center gap-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 px-4 py-2 rounded-lg text-sm transition-colors"
            >
              {running ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Run Against Model
            </button>
          </div>
        </div>

        {/* Preview */}
        {mutations.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-sm font-medium text-gray-400">Generated Mutations ({mutations.length})</h2>
            {mutations.map((m, i) => (
              <div key={i} className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
                <button
                  onClick={() => setExpandedIdx(expandedIdx === i ? null : i)}
                  className="w-full flex items-center justify-between px-4 py-3 text-left"
                >
                  <div>
                    <span className="font-medium text-sm">{m.strategy.replace('_', ' ')}</span>
                    <span className="ml-3 text-xs text-gray-500">{m.description}</span>
                  </div>
                  {expandedIdx === i ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
                </button>
                {expandedIdx === i && (
                  <div className="px-4 pb-4">
                    <pre className="bg-gray-800 rounded p-3 text-xs text-gray-300 whitespace-pre-wrap font-mono overflow-auto max-h-48">{m.prompt}</pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Run results */}
        {runResults.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-sm font-medium text-gray-400">Run Results</h2>
            {runResults.map((r, i) => (
              <div key={i} className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
                <button
                  onClick={() => setExpandedIdx(expandedIdx === i ? null : i)}
                  className="w-full flex items-center justify-between px-4 py-3"
                >
                  <div className="flex items-center gap-4">
                    <span className="font-medium text-sm">{r.strategy.replace('_', ' ')}</span>
                    <span className={`text-sm font-bold ${VERDICT_COLOR[r.verdict] ?? 'text-gray-400'}`}>{r.verdict}</span>
                    <span className="text-xs text-gray-500">{r.latency_ms}ms</span>
                  </div>
                  {expandedIdx === i ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
                </button>
                {expandedIdx === i && (
                  <div className="px-4 pb-4 space-y-2">
                    <p className="text-xs text-gray-500 uppercase tracking-wide">Prompt sent</p>
                    <pre className="bg-gray-800 rounded p-3 text-xs text-gray-300 whitespace-pre-wrap font-mono overflow-auto max-h-32">{r.prompt}</pre>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">Model response</p>
                    <pre className="bg-gray-800 rounded p-3 text-xs text-gray-300 whitespace-pre-wrap font-mono overflow-auto max-h-32">{r.response}</pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
