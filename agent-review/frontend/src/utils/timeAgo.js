/**
 * Format a timestamp as relative time (e.g. "2 minutes ago")
 */
export function timeAgo(ts) {
  if (!ts) return '-'
  const date = new Date(ts)
  if (isNaN(date.getTime())) return String(ts)
  const now = new Date()
  const sec = Math.floor((now - date) / 1000)
  if (sec < 60) return 'just now'
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`
  if (sec < 604800) return `${Math.floor(sec / 86400)}d ago`
  return date.toLocaleDateString()
}
