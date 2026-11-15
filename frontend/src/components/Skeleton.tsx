/**
 * Skeleton — loading placeholder components with shimmer animation.
 * Used while a scan is in progress to give the dashboard structure.
 */

import './Skeleton.css'

export function StatCardSkeleton() {
  return (
    <div className="skeleton-card">
      <div className="skeleton-card__header">
        <div className="skeleton-circle" />
        <div className="skeleton-bar skeleton-bar--sm" />
      </div>
      <div className="skeleton-bar skeleton-bar--xl" />
      <div className="skeleton-bar skeleton-bar--sm" />
    </div>
  )
}

export function FindingsSkeleton() {
  return (
    <div className="skeleton-findings">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="skeleton-finding">
          <div className="skeleton-finding__row">
            <div className="skeleton-dot" />
            <div className="skeleton-bar skeleton-bar--md" />
            <div className="skeleton-bar skeleton-bar--sm" />
          </div>
        </div>
      ))}
    </div>
  )
}
