export const storageKey = 'pending-personal-invitation'
export function captureInvitation() {
  const token = new URLSearchParams(location.hash.slice(1)).get('invite')
  if (token && /^[A-Za-z0-9_-]{40,100}$/.test(token)) {
    try { sessionStorage.setItem(storageKey, token) } catch { /* Keep the token in the URL if storage is unavailable. */ return token }
    history.replaceState(null, '', location.pathname + location.search)
    return token
  }
  try { return sessionStorage.getItem(storageKey) || '' } catch { return '' }
}
