/**
 * EmptyState — centered illustration with icon, title, description, and
 * optional action button. Used when no scan has been run yet, when a
 * scan has no findings, or for upcoming-phase placeholders.
 */

import type { LucideIcon } from 'lucide-react'
import { Radar } from 'lucide-react'
import './EmptyState.css'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description: string
  action?: React.ReactNode
}

export function EmptyState({
  icon: Icon = Radar,
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div className="empty-state__icon">
        <Icon size={36} strokeWidth={1.5} />
      </div>
      <h3 className="empty-state__title">{title}</h3>
      <p className="empty-state__description">{description}</p>
      {action}
    </div>
  )
}
