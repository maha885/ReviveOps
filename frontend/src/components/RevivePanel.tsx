import { useState } from 'react'
import { Sparkles, FilePlus2, ArrowRight } from 'lucide-react'
import { getRevivalPlan, reviveRepository, type RevivalPlan, type ReviveResult, type ScanResult } from '../api/client'
import './RevivePanel.css'

interface Props {
  scanId: string
  onRevived: (scan: ScanResult) => void
}

/** Preview and apply the revival plan. Applying writes to a copy, never the original. */
export function RevivePanel({ scanId, onRevived }: Props) {
  const [plan, setPlan] = useState<RevivalPlan | null>(null)
  const [outcome, setOutcome] = useState<ReviveResult | null>(null)
  const [busy, setBusy] = useState<'plan' | 'revive' | null>(null)
  const [error, setError] = useState<string | null>(null)

  const run = async (kind: 'plan' | 'revive') => {
    setBusy(kind); setError(null)
    try {
      if (kind === 'plan') setPlan(await getRevivalPlan(scanId))
      else setOutcome(await reviveRepository(scanId))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong')
    } finally { setBusy(null) }
  }

  return (
    <section className="revive-panel">
      <div className="revive-panel__head">
        <div>
          <span className="eyebrow">REVIVAL</span>
          <h2>Bring it back to life</h2>
          <p>Generate starter files for what is missing. They are applied to a <b>copy</b> — your repository is never changed.</p>
        </div>
        <div className="revive-panel__actions">
          <button className="retry-btn" disabled={busy !== null} onClick={() => run('plan')}>
            {busy === 'plan' ? 'Loading…' : 'Preview changes'}
          </button>
          <button className="revive-btn" disabled={busy !== null} onClick={() => run('revive')}>
            <Sparkles size={15} /> {busy === 'revive' ? 'Reviving…' : 'Revive a copy'}
          </button>
        </div>
      </div>

      {error && <p className="revive-panel__error">{error}</p>}

      {outcome && (
        <div className="revive-panel__result">
          <div className="revive-panel__scores">
            <strong>{outcome.score_before}</strong><ArrowRight size={18} /><strong className="after">{outcome.score_after}</strong>
            <span>/ 100 revival score</span>
          </div>
          <p>{outcome.files_written.length} file(s) added: {outcome.files_written.join(', ') || 'none'}</p>
          <button className="retry-btn" onClick={() => onRevived(outcome.revived_scan)}>View revived scan</button>
        </div>
      )}

      {plan && !outcome && (
        <ul className="revive-panel__files">
          {plan.files.length === 0 && <li>No starter files can be generated for this project.</li>}
          {plan.files.map((f) => (
            <li key={f.path}><FilePlus2 size={14} /> <code>{f.path}</code><span>{f.rationale}</span></li>
          ))}
          {plan.manual_steps.map((s) => <li key={s} className="manual">Manual step: {s}</li>)}
        </ul>
      )}
    </section>
  )
}
