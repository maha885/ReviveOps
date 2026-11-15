/**
 * FindingsView — premium findings display with severity filter tabs and
 * expandable detail cards.
 *
 * Each card shows a severity dot, category icon, title, and a badge.
 * Clicking a card toggles the evidence / recommendation / source path.
 */

import { useState } from 'react'
import {
  ChevronDown,
  FileText,
  Package,
  FlaskConical,
  GitBranch,
  Container,
  Code2,
  Wrench,
  FileCode,
  type LucideIcon,
} from 'lucide-react'
import type { Finding, Severity } from '../api/client'
import './FindingsView.css'

const SEVERITY_ORDER: Record<Severity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
}

const SEVERITY_LABELS: Record<Severity, string> = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  info: 'Info',
}

const CATEGORY_ICONS: Record<string, LucideIcon> = {
  documentation: FileText,
  dependencies: Package,
  tests: FlaskConical,
  ci: GitBranch,
  containerization: Container,
  code_quality: Code2,
  setup: Wrench,
}

const CATEGORY_LABELS: Record<string, string> = {
  documentation: 'Documentation',
  dependencies: 'Dependencies',
  tests: 'Tests',
  ci: 'CI',
  containerization: 'Containerization',
  code_quality: 'Code Quality',
  setup: 'Setup',
}

export function FindingsView({ findings }: { findings: Finding[] }) {
  const [filter, setFilter] = useState<Severity | 'all'>('all')
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  // Count per severity
  const counts: Partial<Record<Severity, number>> = {}
  for (const f of findings) {
    counts[f.severity] = (counts[f.severity] ?? 0) + 1
  }

  // Filter + sort
  const filtered =
    filter === 'all' ? findings : findings.filter((f) => f.severity === filter)
  const sorted = [...filtered].sort(
    (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity],
  )

  function toggle(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="findings-view">
      {/* Filter tabs */}
      <div className="findings-view__filters">
        <button
          className={`findings-tab ${filter === 'all' ? 'findings-tab--active' : ''}`}
          onClick={() => setFilter('all')}
        >
          All
          <span className="findings-tab__count">{findings.length}</span>
        </button>
        {(['critical', 'high', 'medium', 'low', 'info'] as Severity[]).map(
          (sev) => {
            const count = counts[sev] ?? 0
            if (count === 0) return null
            return (
              <button
                key={sev}
                className={`findings-tab findings-tab--${sev} ${filter === sev ? 'findings-tab--active' : ''}`}
                onClick={() => setFilter(sev)}
              >
                {SEVERITY_LABELS[sev]}
                <span className="findings-tab__count">{count}</span>
              </button>
            )
          },
        )}
      </div>

      {/* Finding cards */}
      <div className="findings-view__list">
        {sorted.map((f) => {
          const CatIcon = CATEGORY_ICONS[f.category] ?? FileCode
          const catLabel = CATEGORY_LABELS[f.category] ?? f.category
          const isOpen = expanded.has(f.finding_id)

          return (
            <div
              key={f.finding_id}
              className={`finding-card finding-card--${f.severity} ${isOpen ? 'finding-card--open' : ''}`}
            >
              <button
                className="finding-card__header"
                onClick={() => toggle(f.finding_id)}
                aria-expanded={isOpen}
              >
                <span
                  className={`finding-card__dot finding-card__dot--${f.severity}`}
                />
                <CatIcon size={15} className="finding-card__cat-icon" />
                <span className="finding-card__cat-label">{catLabel}</span>
                <span className="finding-card__title">{f.title}</span>
                <span
                  className={`finding-card__badge finding-card__badge--${f.severity}`}
                >
                  {SEVERITY_LABELS[f.severity]}
                </span>
                <ChevronDown
                  size={16}
                  className={`finding-card__chevron ${isOpen ? 'finding-card__chevron--open' : ''}`}
                />
              </button>

              {isOpen && (
                <div className="finding-card__body">
                  <div className="finding-card__field">
                    <span className="finding-card__field-label">Evidence</span>
                    <p className="finding-card__field-value finding-card__evidence">
                      {f.evidence}
                    </p>
                  </div>
                  <div className="finding-card__field">
                    <span className="finding-card__field-label">
                      Recommendation
                    </span>
                    <p className="finding-card__field-value">
                      {f.recommendation}
                    </p>
                  </div>
                  {f.source_path && (
                    <div className="finding-card__field">
                      <span className="finding-card__field-label">Source</span>
                      <code className="finding-card__source">
                        {f.source_path}
                      </code>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
