/**
 * StatCard — reusable analytics card with an icon, value, and optional
 * subtitle. The icon sits in a tinted circle matching the accent colour.
 */

import type { LucideIcon } from 'lucide-react'
import './StatCard.css'

interface StatCardProps {
  icon: LucideIcon
  label: string
  value: string | number
  subtitle?: string
  accentColor?: string
  children?: React.ReactNode
}

export function StatCard({
  icon: Icon,
  label,
  value,
  subtitle,
  accentColor = 'var(--accent)',
  children,
}: StatCardProps) {
  return (
    <div className="stat-card">
      <div className="stat-card__header">
        <div
          className="stat-card__icon"
          style={{ color: accentColor, backgroundColor: `${accentColor}1a` }}
        >
          <Icon size={18} strokeWidth={2} />
        </div>
        <span className="stat-card__label">{label}</span>
      </div>
      <div className="stat-card__body">
        <span className="stat-card__value">{value}</span>
        {subtitle && <span className="stat-card__subtitle">{subtitle}</span>}
      </div>
      {children}
    </div>
  )
}
