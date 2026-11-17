import { useCallback, useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import {  HardDrive, Search, ShieldAlert, ListChecks, FileText, AlertCircle, Radar, Download, CheckCircle2, Circle, RefreshCw } from 'lucide-react'
import { Sidebar, type ViewId } from './components/Sidebar'
import { TopBar } from './components/TopBar'
import { StatCard } from './components/StatCard'
import { ScanInput } from './components/ScanInput'
import { FindingsView } from './components/FindingsView'
import { EmptyState } from './components/EmptyState'
import { StatCardSkeleton, FindingsSkeleton } from './components/Skeleton'
import { HealthIndicator } from './components/HealthIndicator'
import { RevivePanel } from './components/RevivePanel'
import { OverviewHero } from './components/OverviewHero'
import { ApiError, getConfig, scanRepository, createScanFromGitHub,  updateTask, getReport, type ScanResult, type RecoveryTask, type ReviveResult } from './api/client'
import './App.css'

const VIEW_LABELS: Record<ViewId,string> = { overview:'Overview', scanner:'Repository Scanner', findings:'Findings', checklist:'Recovery Checklist', reports:'Revival Reports', settings:'Settings' }
type ScanStatus = 'idle'|'scanning'|'success'|'error'
const priorityRank: Record<string,number> = { critical:0, high:1, medium:2, low:3, info:4 }
type Vitality = { key: 'flatline' | 'faint' | 'stirring' | 'risen'; title: string; line: string }

/** Maps the heuristic score to a spooky-but-honest status. Thresholds mirror the score bands. */
function vitality(total: number): Vitality {
  if (total >= 80) return { key: 'risen', title: 'Ready to revive', line: 'Healthy signals across the project. A few manual items remain.' }
  if (total >= 55) return { key: 'stirring', title: 'Stirring', line: 'Signs of life, but important pieces are still missing.' }
  if (total >= 25) return { key: 'faint', title: 'Faint pulse', line: 'Barely alive. Start with the high-priority recovery tasks.' }
  return { key: 'flatline', title: 'Flatlining', line: 'Critical recovery needed. Little in this project is ready to run.' }
}

function App() {
  const [activeView,setActiveView]=useState<ViewId>('overview')
  const [scanState,setScanState]=useState<ScanStatus>('idle')
  const [result,setResult]=useState<ScanResult|null>(null)
  const [error,setError]=useState<string|null>(null)
  const [repoPath,setRepoPath]=useState('')
  const [lastPath,setLastPath]=useState('demo')
  const [githubUrl,setGitHubUrl]=useState('')
  const [lastGitHubUrl,setLastGitHubUrl]=useState<string|null>(null)
  const [healthStatus,setHealthStatus]=useState<'online'|'offline'|'checking'>('checking')
  const [mobileSidebar,setMobileSidebar]=useState(false)
  const [taskBusy,setTaskBusy]=useState<string|null>(null)
  const [report,setReport]=useState<string|null>(null)
  const [reportError,setReportError]=useState<string|null>(null)
  const [reviveSummary,setReviveSummary]=useState<{scanId:string;before:number;after:number;files:number}|null>(null)

  const [demoMode,setDemoMode]=useState(false)

  // Hosted-demo flag. Any failure or unexpected shape silently keeps local mode (false).
  useEffect(()=>{let cancelled=false;getConfig().then(cfg=>{if(!cancelled&&cfg&&cfg.demo_mode===true)setDemoMode(true)}).catch(()=>{});return()=>{cancelled=true}},[])

  useEffect(()=>{let cancelled=false;async function check(){try{const r=await fetch('/health');if(!cancelled)setHealthStatus(r.ok?'online':'offline')}catch{if(!cancelled)setHealthStatus('offline')}}check();const timer=setInterval(check,30000);return()=>{cancelled=true;clearInterval(timer)}},[])

  const handleScan=useCallback(async(path:string)=>{setScanState('scanning');setError(null);setReport(null);setReportError(null);setLastPath(path);setLastGitHubUrl(null);try{const data=await scanRepository(path);setResult(data);setScanState('success')}catch(e){setError(e instanceof ApiError?e.message:'Unexpected error');setScanState('error')}},[])
  const handleScanGitHub=useCallback(async(url:string)=>{setScanState('scanning');setError(null);setReport(null);setReportError(null);setLastGitHubUrl(url);try{const data=await createScanFromGitHub(url);setResult(data);setScanState('success')}catch(e){setError(e instanceof ApiError?e.message:'Unexpected error');setScanState('error')}},[])
  const handleDemo=useCallback(()=>handleScan('demo'),[handleScan])
  const handleRescan=useCallback(()=>lastGitHubUrl?handleScanGitHub(lastGitHubUrl):handleScan(lastPath),[handleScan,handleScanGitHub,lastPath,lastGitHubUrl])
  // const reloadScan=useCallback(async()=>{if(!result)return;try{const fresh=await getScan(result.scan_id);setResult(fresh)}catch(e){setError(e instanceof Error?e.message:'Could not reload scan')}},[result])
  const toggleTask=useCallback(async(task:RecoveryTask)=>{if(!result||taskBusy)return;setTaskBusy(task.task_id);try{const updated=await updateTask(result.scan_id,task.task_id,!task.completed);setResult(prev=>prev?{...prev,tasks:prev.tasks.map(t=>t.task_id===updated.task_id?updated:t)}:prev)}catch(e){setError(e instanceof Error?e.message:'Could not update task')}finally{setTaskBusy(null)}},[result,taskBusy])
  const loadReport=useCallback(async()=>{if(!result)return;setReportError(null);try{const data=await getReport(result.scan_id);setReport(data.markdown)}catch(e){setReportError(e instanceof Error?e.message:'Could not load report')}},[result])
  const downloadReport=()=>{if(!report)return;const blob=new Blob([report],{type:'text/markdown;charset=utf-8'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`${result?.repo_name??'reviveops'}-revival-report.md`;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url)}
  const isScanning=scanState==='scanning'
  const fetchingNotice=isScanning&&lastGitHubUrl?<p className="scan-input__fetching" role="status"><RefreshCw size={16} className="spin-icon" /> Fetching from GitHub…</p>:null
  const isRevived=!!result?.label?.startsWith('revived from')
  const banner=reviveSummary&&result&&reviveSummary.scanId===result.scan_id?reviveSummary:null
  const criticalHigh=result?.findings.filter(f=>f.severity==='critical'||f.severity==='high').length??0
  const tasks=result?.tasks??[]
  const done=tasks.filter(t=>t.completed).length
  const sortedTasks=useMemo(()=>[...tasks].sort((a,b)=>(priorityRank[a.priority.toLowerCase()]??9)-(priorityRank[b.priority.toLowerCase()]??9)),[tasks])

  const scoreCard = result && (
    <div className={`revive-score-panel vitality-${vitality(result.score.total).key}`}>
      <div className="revive-score-ring" key={result.scan_id} style={{ '--score': result.score.total } as CSSProperties}>
        <div><strong>{result.score.total}</strong><span>/ 100</span></div>
      </div>
      <div className="revive-score-copy">
        <span className="eyebrow">PROJECT REVIVAL SCORE · {result.score.label}</span>
        <h2>{vitality(result.score.total).title}</h2>
        <p className="vitality-line">{vitality(result.score.total).line}</p>
        <p>Heuristic readiness score based on repository signals—not a guarantee that the project builds.</p>
      </div>
      <div className="score-dimensions">
        {result.score.dimensions.map((dimension) => (
          <div className="score-dimension" key={dimension.name}>
            <div><span>{dimension.name}</span><b>{dimension.score}/{dimension.max_points}</b></div>
            <div className="score-track"><i style={{ width: `${dimension.max_points ? Math.min(100, dimension.score / dimension.max_points * 100) : 0}%` }} /></div>
          </div>
        ))}
        {(result.score.penalty ?? 0) > 0 && (
          <div className="score-dimension score-penalty" title={result.score.penalty_reason}>
            <div><span>Code quality penalty</span><b>−{result.score.penalty}</b></div>
          </div>
        )}
      </div>
    </div>
  )

  const checklist = result && (
    <section className="phase3-section">
      <div className="phase3-heading">
        <div><span className="eyebrow">RECOVERY PLAN</span><h2>Resurrection checklist</h2><p>{done} of {tasks.length} tasks completed</p></div>
        <div className="progress-pill">{tasks.length ? Math.round(done / tasks.length * 100) : 0}%</div>
      </div>
      <div className="task-progress"><i style={{ width: `${tasks.length ? done / tasks.length * 100 : 0}%` }} /></div>
      {sortedTasks.length ? sortedTasks.map((task) => (
        <article className={`recovery-task ${task.completed ? 'is-done' : ''}`} key={task.task_id}>
          <button className="task-check" aria-label={task.completed ? 'Mark incomplete' : 'Mark complete'} disabled={taskBusy !== null} onClick={() => toggleTask(task)}>
            {taskBusy === task.task_id ? <RefreshCw size={17} className="spin-icon" /> : task.completed ? <CheckCircle2 size={19} /> : <Circle size={19} />}
          </button>
          <div className="task-main">
            <div className="task-title-row"><h3>{task.title}</h3><span className={`priority-tag priority-${task.priority.toLowerCase()}`}>{task.priority}</span></div>
            <p>{task.rationale}</p>
            <div className="task-evidence"><b>Evidence:</b> {task.evidence}</div>
            <div className="task-action"><b>Recommended action:</b> {task.recommended_action}</div>
          </div>
        </article>
      )) : <div className="phase3-empty">No recovery tasks generated for this scan.</div>}
    </section>
  )


  return (
    <div className="app-layout">
      <Sidebar
        activeView={activeView}
        onViewChange={setActiveView}
        healthStatus={healthStatus}
        mobileOpen={mobileSidebar}
        onMobileClose={() => setMobileSidebar(false)}
      />
      <div className="app-main">
        <TopBar
          viewLabel={VIEW_LABELS[activeView]}
          repoName={result?.repo_name ?? null}
          badge={isRevived ? 'Revived copy' : null}
          scanStatus={scanState}
          onRescan={handleRescan}
          onToggleSidebar={() => setMobileSidebar((value) => !value)}
        />
        <div className="app-content">
          {activeView === 'overview' && (
            <div className="view">
              {scanState !== 'idle' && (
                <div className="view__header">
                  <h1 className="view__title">Overview</h1>
                  <p className="view__tagline">Bring dead repos back to life.</p>
                </div>
              )}
              {scanState === 'idle' && (
                <OverviewHero demoMode={demoMode}>
                  <ScanInput onScan={handleScan} onScanGitHub={handleScanGitHub} githubUrl={githubUrl} setGitHubUrl={setGitHubUrl} onDemo={handleDemo} isScanning={isScanning} repoPath={repoPath} setRepoPath={setRepoPath} demoMode={demoMode} />
                </OverviewHero>
              )}
              {scanState === 'scanning' && <>{fetchingNotice}<div className="loading-skeletons"><StatCardSkeleton /><FindingsSkeleton /></div></>}
              {scanState === 'error' && error && (
                <div role="alert"><EmptyState icon={AlertCircle} title="Scan failed" description={error}
                  action={<button className="retry-btn" onClick={() => setScanState('idle')}>Try again</button>} /></div>
              )}
              {result && scanState === 'success' && (
                <>
                  <div className="section-label">Project intelligence</div>
                  {scoreCard}
                  {banner && (
                    <div className="revive-banner">
                      <strong>Revived copy</strong>
                      <span>Score {banner.before} → {banner.after} · {banner.files} file(s) added · original repository untouched</span>
                    </div>
                  )}
                  <RevivePanel key={result.scan_id} scanId={result.scan_id} isRevived={isRevived} onRevived={(scan, outcome: ReviveResult) => { setReviveSummary({ scanId: scan.scan_id, before: outcome.score_before, after: outcome.score_after, files: outcome.files_written.length }); setResult(scan); setReport(null) }} />
                  <div className="stat-grid">
                    <StatCard icon={HardDrive} label="Files scanned" value={result.file_count} />
                    <StatCard icon={Search} label="Total findings" value={result.findings.length} />
                    <StatCard icon={ShieldAlert} label="Critical / High" value={criticalHigh} />
                    <StatCard icon={ListChecks} label="Recovery tasks" value={tasks.length} accentColor="var(--accent)" />
                  </div>
                  {checklist}
                  <div className="section-label">Latest findings</div>
                  <FindingsView findings={result.findings.slice(0, 5)} />
                </>
              )}
            </div>
          )}

          {activeView === 'scanner' && (
            <div className="view">
              <div className="section-label">Repository scan</div>
              <ScanInput onScan={handleScan} onScanGitHub={handleScanGitHub} githubUrl={githubUrl} setGitHubUrl={setGitHubUrl} onDemo={handleDemo} isScanning={isScanning} repoPath={repoPath} setRepoPath={setRepoPath} demoMode={demoMode} />
              {scanState === 'idle' && <EmptyState icon={Radar} title="Ready to scan" description="Start a scan from the Overview page, or use the box above. Full findings appear here." />}
              {scanState === 'scanning' && <>{fetchingNotice}<FindingsSkeleton /></>}
              {scanState === 'error' && error && <div role="alert"><EmptyState icon={AlertCircle} title="Scan failed" description={error} /></div>}
              {result && (
                <>
                  <div className="section-label">Scan results · {result.file_count} files</div>
                  <FindingsView findings={result.findings} />
                </>
              )}
            </div>
          )}

          {activeView === 'findings' && (
            <div className="view">
              <div className="view__header">
                <h1 className="view__title">Findings</h1>
                <p className="view__subtitle">{result ? `${result.findings.length} findings in ${result.repo_name}` : 'Run a scan to view findings.'}</p>
              </div>
              {result ? <FindingsView findings={result.findings} /> : <EmptyState icon={Search} title="No findings yet" description="Run a repository scan first." />}
            </div>
          )}

          {activeView === 'checklist' && (
            <div className="view">
              <div className="view__header">
                <h1 className="view__title">Recovery checklist</h1>
                <p className="view__subtitle">Track the steps to bring this repository back to life.</p>
              </div>
              {result ? checklist : <EmptyState icon={ListChecks} title="No recovery plan yet" description="Run a repository scan to generate a prioritized checklist." />}
            </div>
          )}

          {activeView === 'reports' && (
            <div className="view">
              <div className="view__header">
                <h1 className="view__title">Revival reports</h1>
                <p className="view__subtitle">Generate and export a Markdown report for the latest scan.</p>
              </div>
              {result ? (
                <div className="report-panel">
                  <div className="report-toolbar">
                    <div><FileText size={18} /><strong>{result.repo_name}-revival-report.md</strong></div>
                    <button className="primary-action" onClick={loadReport}>Generate preview</button>
                  </div>
                  {reportError && <p className="inline-error">{reportError}</p>}
                  {report && (
                    <>
                      <pre className="report-preview">{report}</pre>
                      <button className="primary-action" onClick={downloadReport}><Download size={16} /> Download Markdown</button>
                    </>
                  )}
                </div>
              ) : <EmptyState icon={FileText} title="No report yet" description="Run a repository scan before generating its report." />}
            </div>
          )}

          {activeView === 'settings' && (
            <div className="view">
              <div className="view__header">
                <h1 className="view__title">Settings</h1>
                <p className="view__subtitle">Local backend connection and application status.</p>
              </div>
              <HealthIndicator />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
export default App
