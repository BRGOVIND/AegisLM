import { useState, useEffect } from 'react';
import { Trophy, RefreshCw } from 'lucide-react';
import { apiClient } from '../services/api';

interface LeaderboardEntry {
  rank: number;
  model_name: string;
  avg_overall_score: number;
  avg_injection_rate: number;
  avg_jailbreak_rate: number;
  avg_hallucination_rate: number;
  avg_data_leakage_rate: number;
  avg_latency_ms: number;
  benchmark_count: number;
}

const RANK_STYLE: Record<number, string> = {
  1: 'text-yellow-400 font-bold text-lg',
  2: 'text-gray-300 font-bold',
  3: 'text-amber-600 font-bold',
};

function ScoreBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  const color = pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 bg-gray-700 rounded-full h-1.5">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-sm font-bold ${pct >= 70 ? 'text-green-400' : pct >= 40 ? 'text-yellow-400' : 'text-red-400'}`}>
        {pct.toFixed(1)}
      </span>
    </div>
  );
}

export default function Leaderboard() {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get<LeaderboardEntry[]>('/leaderboard');
      setEntries(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Trophy className="w-8 h-8 text-yellow-500" />
            <div>
              <h1 className="text-2xl font-bold">Model Safety Leaderboard</h1>
              <p className="text-gray-400 text-sm">Ranked by average security score across all benchmark runs</p>
            </div>
          </div>
          <button onClick={load} className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>

        {entries.length === 0 && !loading && (
          <div className="text-center py-20 text-gray-500">
            No benchmark data yet — run a multi-model benchmark on the Compare page to populate the leaderboard.
          </div>
        )}

        {entries.length > 0 && (
          <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="px-4 py-3 text-gray-400 text-left w-12">Rank</th>
                  <th className="px-4 py-3 text-gray-400 text-left">Model</th>
                  <th className="px-4 py-3 text-gray-400 text-left">Safety Score</th>
                  <th className="px-4 py-3 text-gray-400 text-right">Injection %</th>
                  <th className="px-4 py-3 text-gray-400 text-right">Jailbreak %</th>
                  <th className="px-4 py-3 text-gray-400 text-right">Ctx Manip %</th>
                  <th className="px-4 py-3 text-gray-400 text-right">Data Leak %</th>
                  <th className="px-4 py-3 text-gray-400 text-right">Latency</th>
                  <th className="px-4 py-3 text-gray-400 text-right">Runs</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e, i) => (
                  <tr key={e.model_name} className={i % 2 === 0 ? 'bg-gray-900' : 'bg-gray-950'}>
                    <td className={`px-4 py-3 ${RANK_STYLE[e.rank] ?? 'text-gray-500'}`}>
                      {e.rank === 1 ? '🥇' : e.rank === 2 ? '🥈' : e.rank === 3 ? '🥉' : `#${e.rank}`}
                    </td>
                    <td className="px-4 py-3 font-medium">{e.model_name}</td>
                    <td className="px-4 py-3"><ScoreBar value={e.avg_overall_score} /></td>
                    <td className="text-right px-4 py-3 text-red-300">{(e.avg_injection_rate * 100).toFixed(1)}%</td>
                    <td className="text-right px-4 py-3 text-orange-300">{(e.avg_jailbreak_rate * 100).toFixed(1)}%</td>
                    <td className="text-right px-4 py-3 text-yellow-300">{(e.avg_hallucination_rate * 100).toFixed(1)}%</td>
                    <td className="text-right px-4 py-3 text-purple-300">{(e.avg_data_leakage_rate * 100).toFixed(1)}%</td>
                    <td className="text-right px-4 py-3 text-gray-300">{e.avg_latency_ms.toFixed(0)} ms</td>
                    <td className="text-right px-4 py-3 text-gray-400">{e.benchmark_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
