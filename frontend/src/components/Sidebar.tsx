/**
 * Sidebar — fixed left navigation with ReviveOps branding.
 *
 * Items marked "disabled" are planned for later phases and show a
 * "Soon" badge instead of being clickable.
 */

import {
  LayoutDashboard,
  Radar,
  AlertTriangle,
  ListChecks,
  FileText,
  Settings,
  type LucideIcon,
} from 'lucide-react'
import './Sidebar.css'

export type ViewId =
  | 'overview'
  | 'scanner'
  | 'findings'
  | 'checklist'
  | 'reports'
  | 'settings'

interface NavItem {
  id: ViewId
  label: string
  icon: LucideIcon
  disabled?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'scanner', label: 'Repository Scanner', icon: Radar },
  { id: 'findings', label: 'Findings', icon: AlertTriangle },
  { id: 'checklist', label: 'Recovery Checklist', icon: ListChecks },
  { id: 'reports', label: 'Revival Reports', icon: FileText },
  { id: 'settings', label: 'Settings', icon: Settings },
]

interface SidebarProps {
  activeView: ViewId
  onViewChange: (view: ViewId) => void
  healthStatus: 'online' | 'offline' | 'checking'
  mobileOpen: boolean
  onMobileClose: () => void
}

export function Sidebar({
  activeView,
  onViewChange,
  healthStatus,
  mobileOpen,
  onMobileClose,
}: SidebarProps) {
  function handleNav(view: ViewId) {
    onViewChange(view)
    onMobileClose()
  }

  return (
    <>
      {mobileOpen && (
        <div className="sidebar-overlay" onClick={onMobileClose} />
      )}
      <aside className={`sidebar ${mobileOpen ? 'sidebar--open' : ''}`}>
        {/* Logo */}
        <div className="sidebar__logo">
          <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
            <path
              d="M16 2 L28 9 L28 23 L16 30 L4 23 L4 9 Z"
              stroke="var(--accent)"
              strokeWidth="1.5"
              fill="rgba(129, 140, 248, 0.08)"
            />
            <path
              d="M9 16 L13 16 L15 12 L17 20 L19 16 L23 16"
              stroke="var(--accent-bright)"
              strokeWidth="1.5"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="sidebar__logo-text">
            Revive<span className="sidebar__logo-accent">Ops</span>
          </span>
        </div>

        {/* Navigation */}
        <nav className="sidebar__nav">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon
            return (
              <button
                key={item.id}
                className={`sidebar__item ${
                  activeView === item.id ? 'sidebar__item--active' : ''
                }`}
                onClick={() => !item.disabled && handleNav(item.id)}
                disabled={item.disabled}
              >
                <Icon size={18} strokeWidth={2} />
                <span className="sidebar__item-label">{item.label}</span>
                {item.disabled && (
                  <span className="sidebar__badge">Soon</span>
                )}
              </button>
            )
          })}
        </nav>

        {/* Footer: health + version */}
        <div className="sidebar__footer">
          <div className="sidebar__health">
            <span
              className={`sidebar__health-dot sidebar__health-dot--${healthStatus}`}
            />
            <span className="sidebar__health-label">
              Backend{' '}
              {healthStatus === 'online'
                ? 'Online'
                : healthStatus === 'offline'
                  ? 'Offline'
                  : 'Checking…'}
            </span>
          </div>
          <div className="sidebar__version">v0.1.0 · Local-first</div>
        </div>
      </aside>
    </>
  )
}
