/**
 * Client-side hint for GitHub URLs. Mirrors the server rule but is advisory
 * only: the server is authoritative and makes the final decision.
 */
const NAME = '[A-Za-z0-9._-]+'
const PATTERN = new RegExp(`^https://github\\.com/(${NAME})/(${NAME})(?:/tree/[^\\s?#]+)?/?$`)

export function looksLikeGitHubUrl(input: string): boolean {
  const url = input.trim()
  if (url.includes('..')) return false
  const match = PATTERN.exec(url)
  if (!match) return false
  return !/^\.+$/.test(match[1]) && !/^\.+$/.test(match[2])
}

/** Returns a short hint for an obviously invalid URL, or null if it looks fine or is empty. */
export function githubUrlHint(input: string): string | null {
  const url = input.trim()
  if (!url || looksLikeGitHubUrl(url)) return null
  return 'Use a URL like https://github.com/owner/repo (https only, no query or fragment).'
}
