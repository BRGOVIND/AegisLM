import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { TrendingUp, RefreshCw } from 'lucide-react';
import { apiClient } from '../services/api';

interface AttackEffectiveness {
  attack_id: number;
  attack_name: string;
  category: string;
  severity: string;
  total_runs: number;
  fail_count: number;
  uncertain_count: number;
  fail_rate: number;
}

interface HeatmapEntry {
  model_name: string;
  category: string;
  fail_rate: number;
  total: number;
}

const SEV_COLOR: Record<string, string> = {
  critical: '#EF4444',
  high: '#F97316',
  medium: '#EAB308',
  low: '#22C55E',
};

export default function Analytics() {
  const [attacks, setAttacks] = useState<AttackEffectiveness[]>([]);
  const [heatmap, setHeatmap] = useState<HeatmapEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [a, h] = await Promise.all([
        apiClient.get<AttackEffectiveness[]>('/analytics/attacks').then(r => r.data),
        apiClient.get<HeatmapEntry[]>('/analytics/category-heatmap').then(r => r.data),
      ]);
      setAttacks(a);
      setHeatmap(h);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  // Build heatmap grid: rows = models, cols = categories
  const models = [...new Set(heatmap.map(h => h.model_name))];
  const categories = ['PROMPT_INJECTION', 'JAILBREAK', 'CONTEXT_MANIPULATION', 'DATA_LEAKAGE'];

  const getRate = (model: string, cat: string) => {
    const e = heatmap.find(h => h.model_name === model && h.category === cat);
    return e ? e.fail_rate : null;
  };

  const rateColor = (rate: number | null) => {
    if (rate === null) return 'bg-gray-800 text-gray-600';
    if (rate >= 0.75) return 'bg-red-900/80 text-red-200';
    if (rate >= 0.5) return 'bg-orange-900/70 text-orange-200';
    if (rate >= 0.25) return 'bg-yellow-900/60 text-yellow-200';
    return 'bg-green-900/50 text-green-200';
  };

  const barData = attacks.slice(0, 15).map(a => ({
    name: a.attack_name.length > 28 ? a.attack_name.slice(0, 25) + '…' : a.attack_name,
    fail_pct: Math.round(a.fail_rate * 100),
    severity: a.severity,
  }));

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <TrendingUp className="w-8 h-8 text-red-500" />
            <div>
              <h1 className="text-2xl font-bold">Attack Effectiveness</h1>
              <p className="text-gray-400 text-sm">Which attacks succeed most across all tested models</p>
            </div>
          </div>
          <button onClick={load} className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>

        {/* Top attacks bar chart */}
        {barData.length > 0 && (
          <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
            <h2 className="text-sm font-medium text-gray-400 mb-4">Top 15 Most Effective Attacks (fail %)</h2>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={barData} layout="vertical" margin={{ left: 180, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tick={{ fill: '#9CA3AF', fontSize: 11 }} unit="%" />
                <YAxis type="category" dataKey="name" tick={{ fill: '#D1D5DB', fontSize: 11 }} width={180} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151' }}
                  formatter={(v: number) => `${v}%`}
                />
                <Bar dataKey="fail_pct" radius={[0, 3, 3, 0]}>
                  {barData.map((entry, i) => (
                    <Cell key={i} fill={SEV_COLOR[entry.severity] || '#6B7280'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <div className="flex gap-4 mt-2 text-xs text-gray-500">
              {Object.entries(SEV_COLOR).map(([sev, col]) => (
                <span key={sev} className="flex items-center gap-1">
                  <span className="inline-block w-3 h-3 rounded" style={{ background: col }} />{sev}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Category heatmap */}
        {models.length > 0 && (
          <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
            <h2 className="text-sm font-medium text-gray-400 mb-4">Vulnerability Heatmap (model × category)</h2>
            <div className="overflow-x-auto">
              <table className="text-sm w-full">
                <thead>
                  <tr>
                    <th className="text-left px-3 py-2 text-gray-500">Model</th>
                    {categories.map(c => (
                      <th key={c} className="px-3 py-2 text-gray-500 text-center text-xs whitespace-nowrap">{c.replace('_', ' ')}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {models.map(model => (
                    <tr key={model}>
                      <td className="px-3 py-2 font-medium text-gray-300 whitespace-nowrap">{model}</td>
                      {categories.map(cat => {
                        const rate = getRate(model, cat);
                        return (
                          <td key={cat} className={`px-3 py-2 text-center rounded ${rateColor(rate)}`}>
                            {rate !== null ? `${Math.round(rate * 100)}%` : '—'}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Table */}
        {attacks.length > 0 && (
          <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left px-4 py-3 text-gray-400">Attack</th>
                  <th className="px-4 py-3 text-gray-400">Category</th>
                  <th className="px-4 py-3 text-gray-400">Severity</th>
                  <th className="text-right px-4 py-3 text-gray-400">Runs</th>
                  <th className="text-right px-4 py-3 text-gray-400">Fail %</th>
                </tr>
              </thead>
              <tbody>
                {attacks.map((a, i) => (
                  <tr key={a.attack_id} className={i % 2 === 0 ? 'bg-gray-900' : 'bg-gray-950'}>
                    <td className="px-4 py-2.5 font-medium">{a.attack_name}</td>
                    <td className="px-4 py-2.5 text-center text-xs text-gray-400">{a.category}</td>
                    <td className="px-4 py-2.5 text-center">
                      <span style={{ color: SEV_COLOR[a.severity] }} className="text-xs font-semibold uppercase">{a.severity}</span>
                    </td>
                    <td className="text-right px-4 py-2.5 text-gray-400">{a.total_runs}</td>
                    <td className="text-right px-4 py-2.5">
                      <span className={a.fail_rate >= 0.5 ? 'text-red-400 font-bold' : a.fail_rate >= 0.25 ? 'text-yellow-400' : 'text-green-400'}>
                        {Math.round(a.fail_rate * 100)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && attacks.length === 0 && (
          <div className="text-center py-20 text-gray-500">
            No test run data yet — run some attacks first to see effectiveness analytics.
          </div>
        )}
      </div>
    </div>
  );
}
