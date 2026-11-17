/**
 * ReviveOps API client — Phase 3 contract.
 */
export interface HealthResponse { status: string; app: string; version: string }
export class ApiError extends Error {
  constructor(message: string, public readonly statusCode?: number) {
    super(message); this.name = 'ApiError'
  }
}
async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response
  try { response = await fetch(url, init) }
  catch { throw new ApiError('Cannot reach backend. Is FastAPI running on port 8000?') }
  if (!response.ok) {
    let message = `Request failed (HTTP ${response.status})`
    try { const body = await response.json(); if (body.detail) message = body.detail } catch {}
    throw new ApiError(message, response.status)
  }
  return response.json() as Promise<T>
}
export async function checkHealth(): Promise<HealthResponse> { return request('/health') }

export interface AppConfig { demo_mode: boolean }
export async function getConfig(): Promise<AppConfig> { return request('/api/config') }

export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info'
export type Category = 'documentation' | 'dependencies' | 'tests' | 'ci' | 'containerization' | 'code_quality' | 'setup'
export interface Finding {
  finding_id: string; title: string; category: Category; severity: Severity
  evidence: string; recommendation: string; source_path: string | null
}
export interface ScoreDimension {
  name: string; score: number; max_points: number; explanation: string; finding_ids: string[]
}
export interface ScoreBreakdown { total: number; dimensions: ScoreDimension[]; label: string; penalty?: number; penalty_reason?: string }
export interface RecoveryTask {
  task_id: string; title: string; priority: string; rationale: string
  evidence: string; recommended_action: string; completed: boolean
}
export interface ScanResult {
  scan_id: string; repo_name: string; scanned_at: string; findings: Finding[]
  file_count: number; truncated: boolean; errors: string[]; label: string | null
  score: ScoreBreakdown; tasks: RecoveryTask[]
}
export interface ReportResponse { scan_id: string; repo_name: string; scanned_at: string; markdown: string }

export async function scanRepository(path: string): Promise<ScanResult> {
  return request('/api/scans', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({path}) })
}
export async function getScan(scanId: string): Promise<ScanResult> {
  return request(`/api/scans/${encodeURIComponent(scanId)}`)
}
export async function updateTask(scanId: string, taskId: string, completed: boolean): Promise<RecoveryTask> {
  return request(`/api/scans/${encodeURIComponent(scanId)}/tasks/${encodeURIComponent(taskId)}`, {
    method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify({completed})
  })
}
export async function getReport(scanId: string): Promise<ReportResponse> {
  return request(`/api/scans/${encodeURIComponent(scanId)}/report`)
}

export interface ProposedFile { path: string; content: string; finding_id: string; rationale: string }
export interface RevivalPlan { scan_id: string; project_type: string; files: ProposedFile[]; manual_steps: string[] }
export interface ReviveResult {
  source_scan_id: string; files_written: string[]
  score_before: number; score_after: number; revived_scan: ScanResult
}
export async function getRevivalPlan(scanId: string): Promise<RevivalPlan> {
  return request(`/api/scans/${encodeURIComponent(scanId)}/revival-plan`)
}
export async function reviveRepository(scanId: string): Promise<ReviveResult> {
  return request(`/api/scans/${encodeURIComponent(scanId)}/revive`, { method: 'POST' })
}
