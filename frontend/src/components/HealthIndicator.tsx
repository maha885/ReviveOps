/**
 * HealthIndicator — polls GET /health and displays the backend status.
 *
 * Three states are handled:
 *   loading  → pulsing dot / spinner (initial check only)
 *   ok       → green dot + service details
 *   error    → red dot + message + hint to start the backend
 *
 * Pass `compact` to render a small badge for the header bar.
 */

import { useEffect, useState } from 'react'
import {
  ApiError,
  checkHealth,
  type HealthResponse,
} from '../api/client'
import './HealthIndicator.css'

type HealthState = 'loading' | 'ok' | 'error'

interface HealthIndicatorProps {
  /** Compact mode = small badge for the header. Full mode = status card. */
  compact?: boolean
}

export function HealthIndicator({ compact = false }: HealthIndicatorProps) {
  const [state, setState] = useState<HealthState>('loading')
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [latencyMs, setLatencyMs] = useState<number | null>(null)

  useEffect(() => {
    let cancelled = false
    let firstRun = true

    async function check() {
      // Only show the loading spinner on the very first check to avoid
      // flicker when the 30-second auto-refresh fires.
      if (firstRun) {
        setState('loading')
        firstRun = false
      }

      const start = performance.now()
      try {
        const data = await checkHealth()
        if (cancelled) return
        setHealth(data)
        setLatencyMs(Math.round(performance.now() - start))
        setError(null)
        setState('ok')
      } catch (e) {
        if (cancelled) return
        setHealth(null)
        setLatencyMs(null)
        setError(e instanceof ApiError ? e.message : 'Unknown error')
        setState('error')
      }
    }

    check()
    const interval = setInterval(check, 30_000) // auto-refresh every 30s

    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  // ── Compact badge (header bar) ──────────────────────────────────────
  if (compact) {
    return (
      <div
        className={`health-badge health-badge--${state}`}
        role="status"
        aria-live="polite"
      >
        <span className="health-dot" aria-hidden="true" />
        <span className="health-badge__label">
          {state === 'loading' && 'Checking…'}
          {state === 'ok' && 'Backend Online'}
          {state === 'error' && 'Backend Offline'}
        </span>
      </div>
    )
  }

  // ── Full status card ─────────────────────────────────────────────────
  return (
    <div
      className={`health-card health-card--${state}`}
      role="status"
      aria-live="polite"
    >
      <div className="health-card__header">
        <span className="health-dot health-dot--lg" aria-hidden="true" />
        <h2 className="health-card__title">Backend Status</h2>
      </div>

      {state === 'loading' && (
        <div className="health-card__loading">
          <span className="health-spinner" aria-hidden="true" />
          <span>Checking backend health…</span>
        </div>
      )}

      {state === 'ok' && health && (
        <div className="health-card__body">
          <p className="health-card__status health-card__status--ok">Online</p>
          <dl className="health-card__details">
            <dt>Service</dt>
            <dd>{health.app}</dd>
            <dt>Version</dt>
            <dd>{health.version}</dd>
            <dt>Latency</dt>
            <dd>{latencyMs !== null ? `${latencyMs} ms` : '—'}</dd>
          </dl>
        </div>
      )}

      {state === 'error' && (
        <div className="health-card__body">
          <p className="health-card__status health-card__status--error">
            Offline
          </p>
          <p className="health-card__error">{error}</p>
          <p className="health-card__hint">
            Start the backend with:{' '}
            <code>uvicorn app.main:app --reload --port 8000</code>
          </p>
        </div>
      )}
    </div>
  )
}
