import React, { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';
import {
  getStrategySuccessRates,
  getFailureReasons,
  getAvgRoundsToCompromise,
  listAgentRuns,
  getAgentRun,
} from '../services/api';
import type {
  StrategySuccessRate,
  FailureReasonEntry,
  AvgRoundsData,
  AgentRun,
  AgentFinding,
} from '../types';

const TIER_COLORS: Record<number, string> = {
  1: '#22c55e',
  2: '#3b82f6',
  3: '#f59e0b',
  4: '#ef4444',
};

const VERDICT_COLOR: Record<string, string> = {
  PASS: '#ef4444',
  FAIL: '#22c55e',
  UNCERTAIN: '#f59e0b',
};

function StatCard({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
      <p className="text-gray-400 text-xs uppercase tracking-wider mb-1">{label}</p>
      <p className="text-2xl font-bold text-white">{value}</p>
    </div>
  );
}

function EscalationTimeline({ findings }: { findings: AgentFinding[] }) {
  const sorted = [...findings].sort((a, b) => a.round_number - b.round_number);
  return (
    <div className="flex flex-wrap gap-2">
      {sorted.map((f, i) => (
        <React.Fragment key={f.id}>
          <div className="flex flex-col items-center">
            <div
              className="rounded-lg px-3 py-2 text-xs font-medium text-white"
              style={{ backgroundColor: TIER_COLORS[f.escalation_tier ?? 1] ?? '#6b7280' }}
            >
              <div className="font-bold">#{f.round_number}</div>
              <div>{f.strategy?.replace(/_/g, ' ') ?? 'unknown'}</div>
              <div className="mt-1 font-semibold" style={{ color: VERDICT_COLOR[f.verdict ?? ''] ?? '#d1d5db' }}>
                {f.verdict === 'FAIL' ? '✓ SUCCESS' : f.verdict === 'PASS' ? '✗ BLOCKED' : '~ UNCERTAIN'}
              </div>
            </div>
            {f.failure_reason && (
              <div className="mt-1 text-gray-400 text-xs max-w-[120px] text-center leading-tight">
                {f.failure_reason.slice(0, 60)}{f.failure_reason.length > 60 ? '…' : ''}
              </div>
            )}
          </div>
          {i < sorted.length - 1 && (
            <div className="flex items-center text-gray-600 text-lg self-start mt-2">→</div>
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

export default function AgentAnalytics() {
  const [strategyRates, setStrategyRates] = useState<StrategySuccessRate[]>([]);
  const [failureReasons, setFailureReasons] = useState<FailureReasonEntry[]>([]);
  const [avgRounds, setAvgRounds] = useState<AvgRoundsData | null>(null);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [selectedRun, setSelectedRun] = useState<AgentRun | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getStrategySuccessRates(),
      getFailureReasons(),
      getAvgRoundsToCompromise(),
      listAgentRuns(),
    ]).then(([s, f, a, r]) => {
      setStrategyRates(s);
      setFailureReasons(f);
      setAvgRounds(a);
      setRuns(r);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selectedRunId !== null) {
      getAgentRun(selectedRunId).then(setSelectedRun).catch(() => setSelectedRun(null));
    }
  }, [selectedRunId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">Loading…</div>
    );
  }

  const strategyChartData = strategyRates.map(r => ({
    name: r.strategy.replace(/_/g, ' '),
    rate: +(r.success_rate * 100).toFixed(1),
    tier: Object.values(
      Object.fromEntries(
        strategyRates.map(s => [s.strategy, 1])
      )
    )[0] ?? 1,
    raw: r,
  }));

  const tierMap: Record<string, number> = {
    direct_override: 1,
    roleplay: 2, authority_framing: 2,
    hypothetical_scenario: 3, multi_step_persuasion: 3,
    context_poisoning: 4, chain_of_thought: 4, encoding_obfuscation: 4,
  };

  return (
    <div className="p-6 space-y-8">
      <h1 className="text-2xl font-bold text-white">Agent Analytics</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          label="Avg Rounds to Compromise"
          value={avgRounds?.avg_rounds != null ? avgRounds.avg_rounds.toFixed(1) : '—'}
        />
        <StatCard
          label="Compromised Sessions"
          value={avgRounds?.sample_size ?? 0}
        />
        <StatCard
          label="Strategies Tracked"
          value={strategyRates.length}
        />
      </div>

      {/* Strategy success rates bar chart */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
        <h2 className="text-lg font-semibold text-white mb-4">Strategy Success Rates</h2>
        {strategyChartData.length === 0 ? (
          <p className="text-gray-500 text-sm">No strategy data yet — run the adaptive agent first.</p>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={strategyChartData} margin={{ top: 5, right: 20, bottom: 60, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="name"
                tick={{ fill: '#9ca3af', fontSize: 11 }}
                angle={-35}
                textAnchor="end"
                interval={0}
              />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} unit="%" domain={[0, 100]} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                formatter={(v: number) => [`${v}%`, 'Success Rate']}
              />
              <Bar dataKey="rate" radius={[4, 4, 0, 0]}>
                {strategyChartData.map((entry) => (
                  <Cell
                    key={entry.name}
                    fill={TIER_COLORS[tierMap[entry.raw.strategy] ?? 1]}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
        <div className="flex gap-4 mt-2 flex-wrap">
          {Object.entries(TIER_COLORS).map(([tier, color]) => (
            <div key={tier} className="flex items-center gap-1 text-xs text-gray-400">
              <span className="inline-block w-3 h-3 rounded-sm" style={{ backgroundColor: color }} />
              Tier {tier}
            </div>
          ))}
        </div>
      </div>

      {/* Failure reason breakdown */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
        <h2 className="text-lg font-semibold text-white mb-4">Failure Reason Breakdown</h2>
        {failureReasons.length === 0 ? (
          <p className="text-gray-500 text-sm">No failure data yet.</p>
        ) : (
          <div className="space-y-2">
            {failureReasons.slice(0, 10).map((r) => (
              <div key={r.failure_reason} className="flex items-center gap-3">
                <span className="text-xs text-gray-400 w-8 text-right shrink-0">{r.count}</span>
                <div className="flex-1 bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-red-500 h-2 rounded-full"
                    style={{ width: `${Math.min(100, (r.count / (failureReasons[0]?.count || 1)) * 100)}%` }}
                  />
                </div>
                <span className="text-xs text-gray-300 flex-1 truncate">{r.failure_reason}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Escalation timeline */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
        <h2 className="text-lg font-semibold text-white mb-4">Escalation Timeline</h2>
        {runs.length === 0 ? (
          <p className="text-gray-500 text-sm">No agent runs yet.</p>
        ) : (
          <>
            <div className="mb-4">
              <label className="text-gray-400 text-sm mr-2">Select session:</label>
              <select
                className="bg-gray-700 text-white text-sm rounded px-3 py-1 border border-gray-600"
                value={selectedRunId ?? ''}
                onChange={e => setSelectedRunId(e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">— pick a run —</option>
                {runs.map(r => (
                  <option key={r.id} value={r.id}>
                    #{r.id} {r.model_name} · {r.target_category} · {r.outcome ?? r.status}
                  </option>
                ))}
              </select>
            </div>
            {selectedRun && selectedRun.findings.length > 0 ? (
              <EscalationTimeline findings={selectedRun.findings} />
            ) : selectedRun ? (
              <p className="text-gray-500 text-sm">No findings for this run (old-style agent or still running).</p>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
