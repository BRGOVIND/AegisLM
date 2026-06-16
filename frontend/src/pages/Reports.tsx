import React, { useEffect, useState } from 'react';
import { AlertTriangle, ShieldCheck, ShieldX, ShieldAlert } from 'lucide-react';
import { getReports, getReport } from '../services/api';
import type { Report, CategoryStats, TopVulnerability, ExecutiveSummary } from '../types';

const RISK_STYLE: Record<string, { bg: string; text: string; border: string }> = {
  LOW:      { bg: 'bg-green-950',  text: 'text-green-400',  border: 'border-green-700' },
  MEDIUM:   { bg: 'bg-yellow-950', text: 'text-yellow-400', border: 'border-yellow-700' },
  HIGH:     { bg: 'bg-orange-950', text: 'text-orange-400', border: 'border-orange-700' },
  CRITICAL: { bg: 'bg-red-950',    text: 'text-red-400',    border: 'border-red-700' },
};

function ExecSummaryCard({ summary }: { summary: ExecutiveSummary }) {
  const style = RISK_STYLE[summary.risk_level] ?? RISK_STYLE.MEDIUM;
  const Icon = summary.risk_level === 'LOW' ? ShieldCheck
    : summary.risk_level === 'CRITICAL' || summary.risk_level === 'HIGH' ? ShieldX
    : ShieldAlert;
  const deplColor = summary.deployment_recommendation === 'APPROVED' ? 'text-green-400'
    : summary.deployment_recommendation === 'NOT RECOMMENDED' ? 'text-red-400'
    : 'text-yellow-400';
  return (
    <div className={`rounded-xl border ${style.border} ${style.bg} p-5 space-y-3`}>
      <div className="flex items-center gap-3">
        <Icon className={`w-6 h-6 ${style.text}`} />
        <div>
          <span className={`font-bold text-lg ${style.text}`}>{summary.risk_level} RISK</span>
          <span className={`ml-4 text-sm font-semibold ${deplColor}`}>{summary.deployment_recommendation}</span>
        </div>
      </div>
      <p className="text-sm text-gray-300 leading-relaxed">{summary.narrative}</p>
      <div className="border-t border-gray-700 pt-3 text-sm text-gray-400">
        <span className="font-medium text-gray-300">Key finding: </span>{summary.key_finding}
      </div>
    </div>
  );
}

function passRateColor(rate: number): string {
  if (rate < 30) return 'text-red-500';
  if (rate < 60) return 'text-amber-500';
  return 'text-green-500';
}

function failureRateBg(rate: number): string {
  if (rate > 70) return 'bg-red-100 text-red-700';
  if (rate > 40) return 'bg-amber-100 text-amber-700';
  return 'bg-green-100 text-green-700';
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString();
}

export default function Reports(): React.ReactElement {
  const [reports, setReports] = useState<Report[]>([]);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);

  useEffect(() => {
    setLoading(true);
    getReports()
      .then((data) => {
        setReports(data);
        setError(null);
      })
      .catch((err: Error) => {
        setError(err.message ?? 'Failed to load reports.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  function handleViewReport(id: number): void {
    setDetailLoading(true);
    getReport(id)
      .then((data) => {
        setSelectedReport(data);
        setError(null);
      })
      .catch((err: Error) => {
        setError(err.message ?? 'Failed to load report detail.');
      })
      .finally(() => {
        setDetailLoading(false);
      });
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      {/* Header */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-white">Security Reports</h2>
        <p className="text-gray-400 mt-1">
          Generated vulnerability assessments and recommendations
        </p>
      </div>

      {error && (
        <div className="mb-6 rounded-md border border-red-500 bg-red-950 px-4 py-3 text-red-400">
          {error}
        </div>
      )}

      {/* Reports List */}
      <div className="mb-8 rounded-lg border border-gray-800 bg-gray-900 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-400">Loading reports…</div>
        ) : reports.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            No reports generated. Run tests and click &apos;Generate Report&apos;.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 bg-gray-800 text-gray-300">
                <th className="px-4 py-3 text-left font-semibold">Model</th>
                <th className="px-4 py-3 text-left font-semibold">Generated At</th>
                <th className="px-4 py-3 text-right font-semibold">Tests</th>
                <th className="px-4 py-3 text-right font-semibold">Pass Rate</th>
                <th className="px-4 py-3 text-center font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report) => (
                <tr
                  key={report.id}
                  className="border-b border-gray-800 last:border-b-0 hover:bg-gray-800 transition-colors"
                >
                  <td className="px-4 py-3 font-medium text-white">
                    {report.model_name}
                  </td>
                  <td className="px-4 py-3 text-gray-400">
                    {formatDate(report.generated_at)}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300">
                    {report.report_data.total_tests}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold">
                    <span className={passRateColor(report.report_data.pass_rate)}>
                      {report.report_data.pass_rate.toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center space-x-2">
                    <button
                      onClick={() => handleViewReport(report.id)}
                      className="inline-flex items-center rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-500 transition-colors"
                    >
                      View
                    </button>
                    <a
                      href={`/api/reports/${report.id}/download`}
                      download
                      className="inline-flex items-center rounded bg-gray-700 px-3 py-1 text-xs font-medium text-gray-200 hover:bg-gray-600 transition-colors"
                    >
                      Download
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Report Detail Panel */}
      {detailLoading && (
        <div className="p-8 text-center text-gray-400">Loading report details…</div>
      )}

      {!detailLoading && selectedReport !== null && (
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 space-y-8">
          {/* Detail Header */}
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div>
              <h3 className="text-xl font-bold text-white">
                Report: {selectedReport.report_data.model_name}
              </h3>
              <p className="text-gray-400 mt-1 text-sm">
                Generated {formatDate(selectedReport.generated_at)}
              </p>
            </div>
            <a
              href={`/api/reports/${selectedReport.id}/download`}
              download
              className="inline-flex items-center rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 transition-colors"
            >
              Download JSON
            </a>
          </div>

          {/* Executive Summary */}
          {selectedReport.report_data.executive_summary && (
            <ExecSummaryCard summary={selectedReport.report_data.executive_summary} />
          )}

          {/* Summary Stats */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="rounded-lg border border-gray-700 bg-gray-800 p-4 text-center">
              <div className="text-2xl font-bold text-white">
                {selectedReport.report_data.total_tests}
              </div>
              <div className="text-xs text-gray-400 mt-1">Total Tests</div>
            </div>
            <div className="rounded-lg border border-gray-700 bg-gray-800 p-4 text-center">
              <div
                className={`text-2xl font-bold ${passRateColor(selectedReport.report_data.pass_rate)}`}
              >
                {selectedReport.report_data.pass_rate.toFixed(1)}%
              </div>
              <div className="text-xs text-gray-400 mt-1">Pass Rate</div>
            </div>
            <div className="rounded-lg border border-gray-700 bg-gray-800 p-4 text-center">
              <div
                className={`text-2xl font-bold ${passRateColor(100 - selectedReport.report_data.fail_rate)}`}
              >
                {selectedReport.report_data.fail_rate.toFixed(1)}%
              </div>
              <div className="text-xs text-gray-400 mt-1">Fail Rate</div>
            </div>
            <div className="rounded-lg border border-gray-700 bg-gray-800 p-4 text-center">
              <div className="text-2xl font-bold text-blue-400">
                {selectedReport.report_data.avg_latency_ms.toFixed(0)}
                <span className="text-sm font-normal text-gray-400">ms</span>
              </div>
              <div className="text-xs text-gray-400 mt-1">Avg Latency</div>
            </div>
          </div>

          {/* Category Breakdown */}
          <div>
            <h4 className="text-base font-semibold text-white mb-3">
              Category Breakdown
            </h4>
            <div className="rounded-lg border border-gray-800 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700 bg-gray-800 text-gray-300">
                    <th className="px-4 py-3 text-left font-semibold">Category</th>
                    <th className="px-4 py-3 text-right font-semibold">Total</th>
                    <th className="px-4 py-3 text-right font-semibold">Passed</th>
                    <th className="px-4 py-3 text-right font-semibold">Failed</th>
                    <th className="px-4 py-3 text-right font-semibold">Failure Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(
                    selectedReport.report_data.category_breakdown as Record<string, CategoryStats>
                  ).map(([category, stats]) => (
                    <tr
                      key={category}
                      className="border-b border-gray-800 last:border-b-0 hover:bg-gray-800 transition-colors"
                    >
                      <td className="px-4 py-3 text-gray-200 font-medium">
                        {category.replace(/_/g, ' ')}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-300">
                        {stats.total}
                      </td>
                      <td className="px-4 py-3 text-right text-green-400">
                        {stats.pass}
                      </td>
                      <td className="px-4 py-3 text-right text-red-400">
                        {stats.fail}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span
                          className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${failureRateBg(
                            stats.failure_rate * 100
                          )}`}
                        >
                          {(stats.failure_rate * 100).toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Top Vulnerabilities */}
          {selectedReport.report_data.top_vulnerabilities.length > 0 && (
            <div>
              <h4 className="text-base font-semibold text-white mb-3">
                Top Vulnerabilities
              </h4>
              <div className="space-y-3">
                {selectedReport.report_data.top_vulnerabilities.map(
                  (vuln: TopVulnerability) => (
                    <div
                      key={vuln.category}
                      className="flex items-center justify-between rounded-lg border border-gray-700 bg-gray-800 p-4 border-l-4 border-l-red-500"
                    >
                      <span className="font-medium text-gray-200">
                        {vuln.category.replace(/_/g, ' ')}
                      </span>
                      <div className="flex items-center gap-3">
                        <span
                          className={`rounded px-2 py-0.5 text-xs font-semibold ${failureRateBg(
                            vuln.failure_rate * 100
                          )}`}
                        >
                          {(vuln.failure_rate * 100).toFixed(1)}% failure
                        </span>
                        <span className="text-sm text-gray-400">
                          {vuln.count} {vuln.count === 1 ? 'test' : 'tests'}
                        </span>
                      </div>
                    </div>
                  )
                )}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {selectedReport.report_data.recommendations.length > 0 && (
            <div>
              <h4 className="text-base font-semibold text-white mb-3">
                Recommendations
              </h4>
              <div className="space-y-2">
                {selectedReport.report_data.recommendations.map(
                  (rec: string, index: number) => (
                    <div
                      key={index}
                      className="flex items-start gap-3 rounded-lg border border-amber-800 bg-amber-950 p-4 border-l-4 border-l-amber-500"
                    >
                      <AlertTriangle
                        className="mt-0.5 h-4 w-4 shrink-0 text-amber-400"
                        aria-hidden="true"
                      />
                      <span className="text-sm text-amber-100">{rec}</span>
                    </div>
                  )
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
