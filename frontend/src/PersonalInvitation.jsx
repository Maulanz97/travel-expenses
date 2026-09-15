import { useRef, useState } from 'react'
import { api, errorMessage } from './api'

export default function PersonalInvitation({ member, groupId, onBusy }) {
  const [link, setLink] = useState('')
  const [pending, setPending] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [active, setActive] = useState(member.invitation_pending)
  const lock = useRef(false)
  const path = `/group-members/group/${groupId}/access/${member.user_id}/invitation`
  async function change(cancel) {
    if (lock.current) return
    lock.current = true; setPending(true); onBusy(true); setError(''); setMessage('')
    try {
      if (cancel) {
        await api.delete(path); setLink(''); setActive(false); setMessage('Invitación cancelada.')
      } else {
        const data = await api.post(path, {})
        setLink(`${location.origin}${location.pathname}#invite=${data.token}`)
        setActive(true); setMessage('Enlace creado. Vence en 7 días; cualquier enlace anterior queda cancelado.')
      }
    } catch (failure) { setError(errorMessage(failure)) }
    finally { lock.current = false; setPending(false); onBusy(false) }
  }
  if (member.account_linked || member.login_email) return null
  return <div className="personal-invitation">
    <p>Invita a {member.name} sin conocer su correo. El enlace es personal, de un solo uso y da acceso de consulta a este viaje.</p>
    <div className="form-actions"><button type="button" className="secondary" disabled={pending} onClick={() => change(false)}>{pending ? 'Espera…' : active ? 'Generar nuevo enlace' : 'Crear enlace personal'}</button>{active && <button type="button" className="secondary" disabled={pending} onClick={() => change(true)}>Cancelar invitación</button>}</div>
    {link && <><label>Enlace para compartir<input readOnly value={link} onFocus={event => event.target.select()} /></label><button type="button" className="secondary" onClick={async () => { try { await navigator.clipboard.writeText(link); setMessage('Enlace copiado.') } catch { setError('Selecciona el enlace y cópialo manualmente.') } }}>Copiar enlace</button><p className="form-help">Compártelo solo con esta persona: quien lo reciba podrá aceptarlo con su cuenta.</p>{['localhost', '127.0.0.1'].includes(location.hostname) && <p className="form-help">Esta dirección solo funciona en esta computadora. Para invitar desde otros dispositivos, publica la app y genera el enlace desde su dirección pública.</p>}</>}
    {message && <p role="status">{message}</p>}{error && <p role="alert" className="alert error">{error}</p>}
  </div>
}
