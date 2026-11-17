/**
 * ScanInput — repository path input with Scan and Demo buttons.
 *
 * State-less: the parent (App) owns the scan logic and passes callbacks.
 * This component is purely presentational with a controlled text input.
 */

import { FolderOpen, Zap, Loader2, Sparkles } from 'lucide-react'
import './ScanInput.css'

interface ScanInputProps {
  onScan: (path: string) => void
  onDemo: () => void
  isScanning: boolean
  repoPath: string
  setRepoPath: (path: string) => void
  /** Hosted demo: only the bundled demo repository can be scanned. */
  demoMode?: boolean
}

export function ScanInput({
  onScan,
  onDemo,
  isScanning,
  repoPath,
  setRepoPath,
  demoMode = false,
}: ScanInputProps) {
  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (repoPath.trim()) onScan(repoPath.trim())
  }

  if (demoMode) {
    return (
      <div className="scan-input">
        <button
          className="scan-input__btn-demo scan-input__btn-demo--primary"
          onClick={onDemo}
          disabled={isScanning}
        >
          {isScanning ? (
            <Loader2 size={16} className="scan-input__spin" />
          ) : (
            <Sparkles size={16} />
          )}
          Use Demo Repository
        </button>
        <p className="scan-input__note" role="note">
          The hosted demo scans the bundled demo repository only. To scan your
          own folders, run ReviveOps locally; setup instructions are in the README.
        </p>
      </div>
    )
  }

  return (
    <div className="scan-input">
      <form className="scan-input__form" onSubmit={handleSubmit}>
        <div className="scan-input__field">
          <FolderOpen size={18} className="scan-input__icon" />
          <input
            type="text"
            className="scan-input__text"
            placeholder="Enter repository path (e.g., C:\projects\my-app)"
            value={repoPath}
            onChange={(e) => setRepoPath(e.target.value)}
            disabled={isScanning}
            aria-label="Repository path"
          />
        </div>
        <button
          type="submit"
          className="scan-input__btn-scan"
          disabled={isScanning || !repoPath.trim()}
        >
          {isScanning ? (
            <Loader2 size={16} className="scan-input__spin" />
          ) : (
            <Zap size={16} />
          )}
          {isScanning ? 'Scanning…' : 'Scan Repository'}
        </button>
      </form>

      <div className="scan-input__divider">
        <span>or</span>
      </div>

      <button
        className="scan-input__btn-demo"
        onClick={onDemo}
        disabled={isScanning}
      >
        <Sparkles size={16} />
        Use Demo Repository
      </button>
    </div>
  )
}
