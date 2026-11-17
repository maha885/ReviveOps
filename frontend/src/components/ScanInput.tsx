/**
 * ScanInput — repository path input with Scan and Demo buttons.
 *
 * State-less: the parent (App) owns the scan logic and passes callbacks.
 * This component is purely presentational with a controlled text input.
 */

import { FolderOpen, Zap, Loader2, Sparkles, Github } from 'lucide-react'
import { githubUrlHint } from '../utils/githubUrl'
import './ScanInput.css'

interface ScanInputProps {
  onScan: (path: string) => void
  /** When provided, a GitHub URL input is shown. */
  onScanGitHub?: (url: string) => void
  githubUrl?: string
  setGitHubUrl?: (url: string) => void
  onDemo: () => void
  isScanning: boolean
  repoPath: string
  setRepoPath: (path: string) => void
  /** Hosted demo: only the bundled demo repository can be scanned. */
  demoMode?: boolean
}

export function ScanInput({
  onScan,
  onScanGitHub,
  githubUrl = '',
  setGitHubUrl,
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

  const hint = githubUrlHint(githubUrl)
  function handleGitHubSubmit(e: React.FormEvent) {
    e.preventDefault()
    const url = githubUrl.trim()
    if (!url || isScanning || !onScanGitHub) return
    onScanGitHub(url)
  }

  const githubBlock = onScanGitHub && setGitHubUrl ? (
    <div className="scan-input__github">
      <form className="scan-input__form" onSubmit={handleGitHubSubmit}>
        <div className="scan-input__field">
          <Github size={18} className="scan-input__icon" />
          <input
            type="text"
            className="scan-input__text"
            placeholder="https://github.com/owner/repo"
            value={githubUrl}
            onChange={(e) => setGitHubUrl(e.target.value)}
            disabled={isScanning}
            aria-label="GitHub repository URL"
            aria-invalid={hint ? true : undefined}
            autoComplete="off"
            spellCheck={false}
          />
        </div>
        <button
          type="submit"
          className="scan-input__btn-scan"
          disabled={isScanning || !githubUrl.trim()}
        >
          {isScanning ? (
            <Loader2 size={16} className="scan-input__spin" />
          ) : (
            <Zap size={16} />
          )}
          Scan GitHub Repo
        </button>
      </form>
      {hint && <p className="scan-input__hint" role="status">{hint}</p>}
      <p className="scan-input__github-note">
        Public repositories only. The default branch is downloaded and scanned; nothing from it is executed.
      </p>
    </div>
  ) : null

  if (demoMode) {
    return (
      <div className="scan-input">
        {githubBlock}
        {githubBlock && (
          <div className="scan-input__divider">
            <span>or</span>
          </div>
        )}
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
          The hosted app can scan a public GitHub repository or the bundled
          demo repository. Scanning local folders requires running ReviveOps
          locally; setup instructions are in the README.
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

      {githubBlock && (
        <>
          <div className="scan-input__divider">
            <span>or</span>
          </div>
          {githubBlock}
        </>
      )}
    </div>
  )
}
