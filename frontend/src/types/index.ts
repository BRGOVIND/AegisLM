export type AttackCategory =
  | 'PROMPT_INJECTION'
  | 'JAILBREAK'
  | 'CONTEXT_MANIPULATION'
  | 'DATA_LEAKAGE';

export type AttackSeverity = 'low' | 'medium' | 'high' | 'critical';

export type Verdict = 'PASS' | 'FAIL' | 'UNCERTAIN';

export interface ApiError {
  error: string;
  detail: string;
}

export interface OllamaModel {
  name: string;
  size: number;
  modified_at: string;
  digest: string;
}

export interface PingResult {
  model: string;
  online: boolean;
  latency_ms: number | null;
  error?: string;
}

export interface Attack {
  id: number;
  name: string;
  category: AttackCategory;
  prompt: string;
  description: string;
  severity: AttackSeverity;
}

export interface AttacksResponse {
  categories: Record<AttackCategory, Attack[]>;
  total: number;
}

export interface RunResult {
  id: number;
  model_name: string;
  attack_id: number;
  attack_name: string;
  category: AttackCategory;
  prompt_sent: string;
  model_response: string;
  score: number;
  verdict: Verdict;
  reason: string;
  latency_ms: number;
  timestamp: string;
}

export interface JobStatus {
  job_id: string;
  status: 'running' | 'completed' | 'failed';
  total: number;
  completed: number;
  results: RunResult[];
}

export interface BatchRunRequest {
  model_name: string;
  category?: string;
}

export interface CategoryStats {
  total: number;
  pass: number;
  fail: number;
  failure_rate: number;
}

export interface DailyCount {
  date: string;
  count: number;
}

export interface DashboardMetrics {
  model_name: string;
  total_tests: number;
  pass_rate: number;
  fail_rate: number;
  prompt_injection_success_rate: number;
  jailbreak_success_rate: number;
  context_manipulation_success_rate: number;
  data_leakage_risk: number;
  avg_latency_ms: number;
  category_breakdown: Record<string, CategoryStats>;
  daily_counts: DailyCount[];
}

export interface HallucinationResult {
  hallucination_score: number;
  faithfulness_score: number;
  explanation: string;
  model_response: string;
}

export interface TopVulnerability {
  category: string;
  failure_rate: number;
  count: number;
}

export interface ExecutiveSummary {
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  narrative: string;
  key_finding: string;
  deployment_recommendation: 'APPROVED' | 'CONDITIONAL' | 'NOT RECOMMENDED';
}

export interface ReportFinding {
  category: string;
  fail_rate: number;
  total: number;
  fail_count: number;
  risk_level: string;
  recommendation: string;
}

export interface ReportData {
  model_name: string;
  generated_at: string;
  total_tests: number;
  pass_rate: number;
  fail_rate: number;
  pass_count: number;
  fail_count: number;
  uncertain_count: number;
  avg_latency_ms: number;
  category_breakdown: Record<string, CategoryStats>;
  top_vulnerabilities: TopVulnerability[];
  recommendations: string[];
  executive_summary?: ExecutiveSummary;
  findings?: ReportFinding[];
}

export interface Report {
  id: number;
  model_name: string;
  generated_at: string;
  report_data: ReportData;
}

// Phase 1 — Multi-Model Benchmarking

export interface ModelScoreResult {
  model_name: string;
  injection_rate: number;
  jailbreak_rate: number;
  hallucination_rate: number;
  data_leakage_rate: number;
  avg_latency_ms: number;
  overall_score: number;
}

export interface BenchmarkRun {
  id: number;
  name: string;
  model_list: string[];
  attack_suite: number[];
  status: 'pending' | 'running' | 'completed' | 'failed' | 'unknown';
  created_at: string;
  completed_at: string | null;
  model_scores: ModelScoreResult[];
}

export interface BenchmarkStatus {
  benchmark_run_id: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'unknown';
  progress: number;
  error?: string;
}

export interface CreateBenchmarkRequest {
  name: string;
  model_list: string[];
  attack_ids?: number[];
}

// Adaptive Agent Analytics

export interface AgentFinding {
  id: number;
  round_number: number;
  attack_prompt: string;
  model_response: string | null;
  verdict: string | null;
  score: number | null;
  escalated: number;
  strategy: string | null;
  failure_reason: string | null;
  escalation_tier: number | null;
  created_at: string;
}

export interface AgentRun {
  id: number;
  model_name: string;
  target_category: string | null;
  max_rounds: number;
  status: string;
  outcome: string | null;
  rounds_completed: number;
  created_at: string;
  completed_at: string | null;
  findings: AgentFinding[];
}

export interface StrategySuccessRate {
  strategy: string;
  total_attempts: number;
  successes: number;
  success_rate: number;
}

export interface FailureReasonEntry {
  failure_reason: string;
  count: number;
}

export interface AvgRoundsData {
  avg_rounds: number | null;
  sample_size: number;
}
