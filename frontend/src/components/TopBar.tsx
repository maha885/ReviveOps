/**
 * TopBar — sticky header with breadcrumb, repository name, scan status,
 * and a rescan action button.
 */

import { ChevronRight, RefreshCw } from 'lucide-react'
import './TopBar.css'

interface TopBarProps {
  viewLabel: string
  repoName: string | null
  badge?: string | null
  scanStatus: 'idle' | 'scanning' | 'success' | 'error'
  onRescan: () => void
  onToggleSidebar: () => void
}

const STATUS_CONFIG: Record<
  TopBarProps['scanStatus'],
  { label: string; className: string }
> = {
  idle: { label: 'Ready', className: 'topbar__status--idle' },
  scanning: { label: 'Scanning', className: 'topbar__status--scanning' },
  success: { label: 'Complete', className: 'topbar__status--success' },
  error: { label: 'Error', className: 'topbar__status--error' },
}

export function TopBar({
  viewLabel,
  repoName,
  badge,
  scanStatus,
  onRescan,
  onToggleSidebar,
}: TopBarProps) {
  const status = STATUS_CONFIG[scanStatus]

  return (
    <header className="topbar">
      <button
        className="topbar__menu"
        onClick={onToggleSidebar}
        aria-label="Toggle navigation"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>

      {/* Breadcrumb */}
      <div className="topbar__breadcrumb">
        <span className="topbar__crumb">ReviveOps</span>
        <ChevronRight size={14} className="topbar__sep" />
        <span className="topbar__crumb topbar__crumb--active">{viewLabel}</span>
      </div>

      {/* Right side actions */}
      <div className="topbar__actions">
        {repoName && (
          <div className="topbar__repo">
            <span className="topbar__repo-label">Repo</span>
            <span className="topbar__repo-name">{repoName}</span>
          </div>
        )}
        {badge && <span className="topbar__badge">{badge}</span>}
        <div className={`topbar__status ${status.className}`}>
          <span className="topbar__status-dot" />
          {status.label}
        </div>
        {scanStatus === 'success' && (
          <button className="topbar__rescan" onClick={onRescan}>
            <RefreshCw size={14} />
            <span>Rescan</span>
          </button>
        )}
      </div>
    </header>
  )
}
