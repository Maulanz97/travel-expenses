import { useRef, useState } from 'react'
import { UserMinus } from 'lucide-react'
import { api, errorMessage } from './api'

export default function RemoveMemberButton({ member, groupId, busy, onBusy, onChanged }) {
  const [confirm, setConfirm] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const lock = useRef(false)
  async function remove() {
    if (lock.current) return
    lock.current = true; setPending(true); onBusy(true); setError('')
    try {
      await api.delete(`/group-members/group/${groupId}/people/${member.user_id}`)
      await onChanged()
    } catch (failure) {
      setError(failure.status ? errorMessage(failure) : 'No pudimos confirmar si se quitó del viaje. Actualiza los integrantes para comprobarlo; puedes volver a intentarlo sin duplicar la operación.')
    } finally {
      lock.current = false; setPending(false); onBusy(false)
    }
  }
  return <div className="member-removal">
    <button type="button" className="secondary member-remove-button" disabled={busy || pending} aria-expanded={confirm} aria-label={`Quitar a ${member.name} del viaje`} onClick={() => { setConfirm(!confirm); setError('') }}><UserMinus size={16} aria-hidden="true" />Quitar del viaje</button>
    {confirm && <div className="member-remove-confirm">
      <p>¿Quitar a <strong>{member.name}</strong> de este viaje? Seguirá en las personas guardadas y en sus otros viajes. Perderá el acceso a este viaje.</p>
      <p className="muted">Solo se puede quitar si no participa en gastos ni pagos, incluidos los anulados.</p>
      {error && <p className="alert error" role="alert">{error}</p>}
      <div className="form-actions"><button type="button" className="secondary" disabled={busy || pending} onClick={() => { setConfirm(false); setError('') }}>Conservar integrante</button><button type="button" className="secondary" disabled={busy || pending} onClick={remove}>{pending ? 'Quitando…' : 'Confirmar retiro'}</button></div>
    </div>}
  </div>
}
