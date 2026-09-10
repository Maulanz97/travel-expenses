import { EMAIL_PATTERN } from './validation'
import { useRef, useState } from 'react'
import { api, errorMessage } from './api'

export default function NewMemberForm({ group, onAdded, onBusy }) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [uncertain, setUncertain] = useState(false)
  const lock = useRef(false)
  async function submit(event) {
    event.preventDefault()
    if (lock.current || uncertain) return
    const form = event.currentTarget
    const data = new FormData(form)
    lock.current = true; setPending(true); onBusy(true); setError('')
    try {
      const person = await api.post(`/group-members/group/${group.id}/people`, { name: String(data.get('name')).trim(), email: String(data.get('email')).trim() || null })
      form.reset()
      await onAdded(person)
    } catch (failure) {
      setUncertain(Boolean(failure.uncertain))
      setError(failure.status === 409 ? 'No se pudo agregar. Si el correo ya está registrado, selecciona a la persona en «Agregar persona existente».' : errorMessage(failure))
    } finally { lock.current = false; setPending(false); onBusy(false) }
  }
  return <section className="card"><h3>Nueva persona en este viaje</h3><p className="form-help">Solo necesitas su nombre. Se creará la persona y se agregará a {group.name} en un paso.</p>
    {error && <p className="alert error" role="alert">{error}</p>}
    <form className="form" onSubmit={submit} aria-busy={pending}><fieldset className="pending-fields" disabled={pending || uncertain}>
      <label>Nombre<input required name="name" maxLength={100} pattern=".*\S.*" autoComplete="name" /></label>
      <label>Correo electrónico (opcional)<input name="email" type="email" pattern={EMAIL_PATTERN} autoComplete="email" maxLength={254} /></label>
      <button className="primary">{pending ? 'Agregando…' : 'Crear y agregar al viaje'}</button>
    </fieldset></form>
    {uncertain && <p>Actualiza los integrantes para comprobar si se agregó antes de volver a intentarlo.</p>}
  </section>
}
