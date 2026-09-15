import { useEffect, useRef, useState } from 'react'
import { api, errorMessage } from './api'

import { storageKey } from './invitationStorage'

export default function InvitationGate({ token, profile, onDone }) {
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const lock = useRef(false)
  useEffect(() => {
    let active = true
    api.post('/invitations/preview', { token }).then(data => { if (active) { setPreview(data); setError('') } }).catch(failure => { if (active) setError(errorMessage(failure)) })
    return () => { active = false }
  }, [token, attempt])
  function finish() {
    try { sessionStorage.removeItem(storageKey) } catch { /* The current view still clears. */ }
    if (location.hash.startsWith('#invite=')) history.replaceState(null, '', location.pathname + location.search)
    onDone()
  }
  async function accept() {
    if (lock.current) return
    lock.current = true; setPending(true); setError('')
    try { await api.post('/invitations/accept', { token }); finish() }
    catch (failure) { setError(errorMessage(failure)) }
    finally { lock.current = false; setPending(false) }
  }
  return <main className="auth-shell"><h1>Invitación personal</h1><p>Has iniciado sesión como {profile.email}.</p>
    {preview ? <><p>Te invitaron a <strong>{preview.trip}</strong> como <strong>{preview.person}</strong>.</p><p>Al aceptar podrás consultar este viaje. Quien organiza podrá darte permiso para registrar gastos.</p><button className="primary" disabled={pending} onClick={accept}>{pending ? 'Aceptando…' : 'Aceptar invitación'}</button></> : !error && <p role="status">Consultando invitación…</p>}
    {error && <p className="alert error" role="alert">{error}</p>}
    <div className="form-actions">{error && <button className="secondary" disabled={pending} onClick={() => setAttempt(n => n + 1)}>Reintentar consulta</button>}<button className="secondary" disabled={pending} onClick={finish}>Continuar sin aceptar</button></div>
  </main>
}
