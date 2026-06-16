import { useState, useEffect } from 'react';
import { Database, Download, RefreshCw } from 'lucide-react';
import { apiClient } from '../services/api';

interface DatasetStats {
  total: number;
  by_verdict: Record<string, number>;
  by_category: Record<string, number>;
  model_count: number;
}

interface DatasetEntry {
  id: number;
  attack_name: string;
  category: string;
  severity: string;
  prompt: string;
  model_name: string;
  model_response: string | null;
  ground_truth_verdict: string;
  source: string;
  created_at: string;
}

const VERDICT_COLOR: Record<string, string> = {
  PASS: 'text-green-400',
  FAIL: 'text-red-400',
  UNCERTAIN: 'text-yellow-400',
};

export default function Dataset() {
  const [stats, setStats] = useState<DatasetStats | null>(null);
  const [entries, setEntries] = useState<DatasetEntry[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);

  const loadAll = async () => {
    try {
      const [s, e] = await Promise.all([
        apiClient.get<DatasetStats>('/dataset/stats').then(r => r.data),
        apiClient.get<DatasetEntry[]>('/dataset?limit=200').then(r => r.data),
      ]);
      setStats(s);
      setEntries(e);
    } catch {}
  };

  useEffect(() => { loadAll(); }, []);

  const handleSync = async () => {
    setSyncing(true);
    setSyncMsg(null);
    try {
      const res = await apiClient.post<{ added: number; message: string }>('/dataset/sync');
      setSyncMsg(res.data.message);
      await loadAll();
    } catch {
      setSyncMsg('Sync failed.');
    } finally {
      setSyncing(false);
    }
  };

  const handleExport = async () => {
    const data = await apiClient.get('/dataset/export').then(r => r.data);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'redforge-dataset.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center gap-3">
          <Database className="w-8 h-8 text-red-500" />
          <div>
            <h1 className="text-2xl font-bold">Benchmark Dataset</h1>
            <p className="text-gray-400 text-sm">Curated attack-response pairs with ground truth labels</p>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Total Entries', value: stats.total },
              { label: 'Models', value: stats.model_count },
              { label: 'FAILs', value: stats.by_verdict['FAIL'] ?? 0 },
              { label: 'PASSes', value: stats.by_verdict['PASS'] ?? 0 },
            ].map(({ label, value }) => (
              <div key={label} className="bg-gray-900 rounded-xl p-4 border border-gray-800 text-center">
                <div className="text-2xl font-bold text-white">{value}</div>
                <div className="text-xs text-gray-400 mt-1">{label}</div>
              </div>
            ))}
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-wrap gap-3">
          <button onClick={handleSync} disabled={syncing}
            className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 px-4 py-2 rounded-lg text-sm transition-colors">
            <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
            {syncing ? 'Syncing…' : 'Sync from Test Runs'}
          </button>
          <button onClick={handleExport}
            className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded-lg text-sm transition-colors">
            <Download className="w-4 h-4" /> Export JSON
          </button>
        </div>
        {syncMsg && <p className="text-sm text-green-400">{syncMsg}</p>}

        {/* Category breakdown */}
        {stats && Object.keys(stats.by_category).length > 0 && (
          <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
            <h2 className="text-sm font-medium text-gray-400 mb-3">By Category</h2>
            <div className="flex flex-wrap gap-3">
              {Object.entries(stats.by_category).map(([cat, count]) => (
                <div key={cat} className="bg-gray-800 px-3 py-2 rounded-lg">
                  <span className="text-xs text-gray-400">{cat}</span>
                  <span className="ml-2 text-sm font-bold">{count}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Table */}
        {entries.length > 0 && (
          <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left px-4 py-3 text-gray-400">Attack</th>
                  <th className="px-4 py-3 text-gray-400">Category</th>
                  <th className="px-4 py-3 text-gray-400">Severity</th>
                  <th className="px-4 py-3 text-gray-400">Model</th>
                  <th className="px-4 py-3 text-gray-400">Verdict</th>
                  <th className="px-4 py-3 text-gray-400">Source</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e, i) => (
                  <tr key={e.id} className={i % 2 === 0 ? 'bg-gray-900' : 'bg-gray-950'}>
                    <td className="px-4 py-2.5 font-medium max-w-xs truncate" title={e.attack_name}>{e.attack_name}</td>
                    <td className="px-4 py-2.5 text-center text-xs text-gray-400">{e.category}</td>
                    <td className="px-4 py-2.5 text-center text-xs text-gray-400">{e.severity}</td>
                    <td className="px-4 py-2.5 text-center text-gray-300 text-xs">{e.model_name}</td>
                    <td className="px-4 py-2.5 text-center">
                      <span className={`font-bold text-sm ${VERDICT_COLOR[e.ground_truth_verdict] ?? 'text-gray-400'}`}>
                        {e.ground_truth_verdict}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-center text-xs text-gray-500">{e.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {entries.length === 0 && (
          <div className="text-center py-16 text-gray-500">
            No dataset entries yet — click "Sync from Test Runs" to auto-populate from existing run results.
          </div>
        )}
      </div>
    </div>
  );
}
