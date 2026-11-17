/**
 * Overview landing content shown before a scan: hero with an animated
 * "vital signs" monitor, the scan card (children), a three-step flow and a
 * breakdown of how the revival score is built.
 */

import type { ReactNode } from 'react'
import { Radar, ListChecks, HeartPulse, ShieldCheck, Copy, Eye } from 'lucide-react'
import './OverviewHero.css'

const STEPS = [
  {
    icon: Radar,
    title: 'Scan',
    text: 'Paste a public GitHub URL or try the bundled demo. Reading only: nothing from the repository is ever run.',
  },
  {
    icon: ListChecks,
    title: 'Understand',
    text: 'Get a 0–100 revival score across five dimensions, with the evidence behind every finding and a prioritized checklist.',
  },
  {
    icon: HeartPulse,
    title: 'Revive',
    text: 'Preview, then add a README, smoke test, CI workflow and Dockerfile to a copy. Rescan and watch the score climb.',
  },
]

const DIMENSIONS = [
  { name: 'Documentation', weight: 20 },
  { name: 'Dependencies', weight: 25 },
  { name: 'Testing', weight: 25 },
  { name: 'CI/CD', weight: 15 },
  { name: 'Containerization', weight: 15 },
]

interface OverviewHeroProps {
  demoMode: boolean
  children: ReactNode
}

export function OverviewHero({ demoMode, children }: OverviewHeroProps) {
  return (
    <div className="ov">
      <section className="ov-hero">
        <div className="ov-hero__copy">
          <span className="ov-eyebrow">Kiroween 2026 · Resurrection</span>
          <h1 className="ov-title">
            Bring dead repos <span className="ov-title__accent">back to life.</span>
          </h1>
          <p className="ov-lead">
            Every developer has inherited a project with no README, no tests and no idea how to
            run it. ReviveOps scans it, tells you exactly why it is flatlining, and revives it
            in one click.
          </p>
          <ul className="ov-trust">
            <li><Eye size={14} /> Nothing is executed</li>
            <li><Copy size={14} /> Works on a copy</li>
            <li><ShieldCheck size={14} /> Explainable score</li>
          </ul>
        </div>

        <aside className="ov-monitor" aria-label="Example: a repository being revived">
          <div className="ov-monitor__top">
            <span className="ov-monitor__dot" />
            <span className="ov-monitor__label">Vital signs · bundled demo repo</span>
          </div>
          <svg className="ov-ecg" viewBox="0 0 400 110" role="img" aria-label="Heartbeat line going from flat to beating">
            <defs>
              <linearGradient id="ov-ecg-grad" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="400" y2="0">
                <stop offset="0" stopColor="#6b7280" />
                <stop offset="0.42" stopColor="#6b7280" />
                <stop offset="0.52" stopColor="#4ade80" />
                <stop offset="1" stopColor="#86efac" />
              </linearGradient>
            </defs>
            <path className="ov-ecg__grid" d="M0 55 H400 M0 20 H400 M0 90 H400" />
            <path
              className="ov-ecg__line"
              pathLength={100}
              d="M0 55 H165 L180 55 L190 55 L200 20 L210 98 L220 8 L230 62 L240 55 H275 L285 40 L295 55 H330 L338 28 L346 84 L354 55 H400"
            />
          </svg>
          <div className="ov-monitor__score">
            <div className="ov-monitor__stat ov-monitor__stat--before">
              <strong>8</strong>
              <span>Flatlining</span>
            </div>
            <span className="ov-monitor__arrow" aria-hidden="true">→</span>
            <div className="ov-monitor__stat ov-monitor__stat--after">
              <strong>80</strong>
              <span>Ready to revive</span>
            </div>
          </div>
          <p className="ov-monitor__caption">One click on the demo repository. The original is never touched.</p>
        </aside>
      </section>

      <section className="ov-scan" aria-label="Scan a repository">
        <div className="ov-section-head">
          <h2>Start a scan</h2>
          <p>
            {demoMode
              ? 'Paste any public GitHub repository, or try the bundled demo.'
              : 'Scan a local folder, a public GitHub repository, or the bundled demo.'}
          </p>
        </div>
        {children}
      </section>

      <section aria-label="How it works">
        <div className="ov-section-head">
          <h2>How it works</h2>
        </div>
        <ol className="ov-steps">
          {STEPS.map((step, i) => (
            <li className="ov-step" key={step.title}>
              <span className="ov-step__num">{i + 1}</span>
              <step.icon size={22} className="ov-step__icon" />
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="ov-score" aria-label="How the score works">
        <div className="ov-section-head">
          <h2>How the revival score works</h2>
          <p>
            Five weighted dimensions add up to 100, minus a small penalty for leftover TODO and
            FIXME markers. It is a heuristic: it estimates readiness, it does not build your
            project.
          </p>
        </div>
        <ul className="ov-bars">
          {DIMENSIONS.map((d) => (
            <li className="ov-bar" key={d.name}>
              <span className="ov-bar__name">{d.name}</span>
              <span className="ov-bar__track">
                <span className="ov-bar__fill" style={{ width: `${d.weight * 4}%` }} />
              </span>
              <span className="ov-bar__weight">{d.weight}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
