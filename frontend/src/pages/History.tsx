import { useState, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { Clock, RefreshCw } from 'lucide-react';
import { apiClient } from '../services/api';

interface ScorePoint {
  benchmark_id: number;
  benchmark_name: string;
  timestamp: string;
  overall_score: number;
  injection_rate: number;
  jailbreak_rate: number;
  hallucination_rate: number;
  data_leakage_rate: number;
  avg_latency_ms: number;
}

interface ModelHistory {
  model_name: string;
  data_points: ScorePoint[];
}

const LINE_COLORS = ['#EF4444', '#3B82F6', '#22C55E', '#F97316', '#8B5CF6', '#EC4899'];

export default function History() {
  const [histories, setHistories] = useState<ModelHistory[]>([]);
  const [modelInput, setModelInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [metric, setMetric] = useState<'overall_score' | 'injection_rate' | 'jailbreak_rate' | 'hallucination_rate' | 'data_leakage_rate'>('overall_score');

  const load = async () => {
    setLoading(true);
    try {
      const params = modelInput.trim() ? `?models=${encodeURIComponent(modelInput.trim())}` : '';
      const res = await apiClient.get<ModelHistory[]>(`/history${params}`);
      setHistories(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  // Build chart data: merge all models onto shared timeline
  const allTimestamps = [
    ...new Set(histories.flatMap(h => h.data_points.map(p => p.timestamp)))
  ].sort();

  const chartData = allTimestamps.map(ts => {
    const point: Record<string, number | string> = { ts: new Date(ts).toLocaleDateString() };
    histories.forEach(h => {
      const dp = h.data_points.find(p => p.timestamp === ts);
      if (dp) point[h.model_name] = metric === 'overall_score' ? dp.overall_score : dp[metric] * 100;
    });
    return point;
  });

  const METRIC_LABELS: Record<string, string> = {
    overall_score: 'Safety Score (0–100, higher = safer)',
    injection_rate: 'Injection Fail Rate (%)',
    jailbreak_rate: 'Jailbreak Fail Rate (%)',
    hallucination_rate: 'Ctx Manipulation Fail Rate (%)',
    data_leakage_rate: 'Data Leakage Fail Rate (%)',
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex items-center gap-3">
          <Clock className="w-8 h-8 text-red-500" />
          <div>
            <h1 className="text-2xl font-bold">Historical Tracking</h1>
            <p className="text-gray-400 text-sm">Security score trends over benchmark runs</p>
          </div>
        </div>

        {/* Controls */}
        <div className="bg-gray-900 rounded-xl p-5 border border-gray-800 flex flex-wrap gap-4 items-end">
          <div className="flex-1 min-w-48">
            <label className="block text-xs text-gray-400 mb-1">Filter models (comma-separated, blank = all)</label>
            <input value={modelInput} onChange={e => setModelInput(e.target.value)}
              placeholder="llama3.2, mistral"
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-red-500" />
          </div>
          <div className="flex-1 min-w-48">
            <label className="block text-xs text-gray-400 mb-1">Metric</label>
            <select value={metric} onChange={e => setMetric(e.target.value as typeof metric)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-red-500">
              <option value="overall_score">Overall Safety Score</option>
              <option value="injection_rate">Prompt Injection Rate</option>
              <option value="jailbreak_rate">Jailbreak Rate</option>
              <option value="hallucination_rate">Context Manipulation Rate</option>
              <option value="data_leakage_rate">Data Leakage Rate</option>
            </select>
          </div>
          <button onClick={load} className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded-lg text-sm transition-colors">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Load
          </button>
        </div>

        {/* Chart */}
        {chartData.length > 0 ? (
          <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
            <h2 className="text-sm font-medium text-gray-400 mb-4">{METRIC_LABELS[metric]}</h2>
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="ts" tick={{ fill: '#9CA3AF', fontSize: 11 }} />
                <YAxis domain={metric === 'overall_score' ? [0, 100] : [0, 100]} tick={{ fill: '#9CA3AF', fontSize: 11 }}
                  unit={metric === 'overall_score' ? '' : '%'} />
                <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151' }}
                  formatter={(v: number) => metric === 'overall_score' ? v.toFixed(1) : `${v.toFixed(1)}%`} />
                <Legend />
                {histories.map((h, i) => (
                  <Line key={h.model_name} type="monotone" dataKey={h.model_name}
                    stroke={LINE_COLORS[i % LINE_COLORS.length]} strokeWidth={2}
                    dot={{ r: 4 }} activeDot={{ r: 6 }} connectNulls />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : !loading ? (
          <div className="text-center py-20 text-gray-500">
            No historical data yet — complete some benchmark runs first.
          </div>
        ) : null}

        {/* Per-model summary table */}
        {histories.length > 0 && (
          <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left px-4 py-3 text-gray-400">Model</th>
                  <th className="text-right px-4 py-3 text-gray-400">Benchmarks</th>
                  <th className="text-right px-4 py-3 text-gray-400">Latest Score</th>
                  <th className="text-right px-4 py-3 text-gray-400">Best Score</th>
                  <th className="text-right px-4 py-3 text-gray-400">Trend</th>
                </tr>
              </thead>
              <tbody>
                {histories.map((h, i) => {
                  const scores = h.data_points.map(p => p.overall_score);
                  const latest = scores[scores.length - 1] ?? 0;
                  const best = Math.max(...scores);
                  const trend = scores.length >= 2 ? latest - scores[scores.length - 2] : 0;
                  return (
                    <tr key={h.model_name} className={i % 2 === 0 ? 'bg-gray-900' : 'bg-gray-950'}>
                      <td className="px-4 py-3 font-medium">{h.model_name}</td>
                      <td className="text-right px-4 py-3 text-gray-400">{h.data_points.length}</td>
                      <td className="text-right px-4 py-3">
                        <span className={latest >= 70 ? 'text-green-400' : latest >= 40 ? 'text-yellow-400' : 'text-red-400'}>
                          {latest.toFixed(1)}
                        </span>
                      </td>
                      <td className="text-right px-4 py-3 text-blue-400">{best.toFixed(1)}</td>
                      <td className="text-right px-4 py-3">
                        <span className={trend > 0 ? 'text-green-400' : trend < 0 ? 'text-red-400' : 'text-gray-400'}>
                          {trend > 0 ? `+${trend.toFixed(1)}` : trend < 0 ? trend.toFixed(1) : '—'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
