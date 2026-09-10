import { EMAIL_PATTERN } from './validation'
import { useState, useRef } from 'react'
import { api, errorMessage } from './api'

export default function PeopleDirectory({ users, onSaved, onBack, onBusy }) {
  const [editing, setEditing] = useState(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const lock = useRef(false)
  async function save(event) {
    event.preventDefault()
    if (lock.current) return
    const data = new FormData(event.currentTarget)
    lock.current = true; setPending(true); onBusy(true); setError('')
    try {
      const person = await api.put(`/users/${editing.id}`, { name: String(data.get('name')).trim(), email: String(data.get('email')).trim() || null })
      onSaved(person); setEditing(null)
    } catch (failure) { setError(errorMessage(failure)) }
    finally { lock.current = false; setPending(false); onBusy(false) }
  }
  return <div className="management"><button className="secondary" disabled={pending} onClick={onBack}>Volver a Integrantes</button><h2>Personas guardadas</h2><p className="form-help">Este directorio se comparte entre tus viajes. Corregir un nombre o correo lo actualiza en todos ellos.</p>{error && <p role="alert" className="alert error">{error}</p>}
    {editing ? <form className="form" onSubmit={save}><fieldset className="pending-fields" disabled={pending}><label>Nombre<input required name="name" maxLength={100} pattern=".*\S.*" defaultValue={editing.name} /></label><label>Correo electrónico (opcional)<input type="email" maxLength={254} pattern={EMAIL_PATTERN} name="email" defaultValue={editing.email || ''} /></label><div className="form-actions"><button type="button" className="secondary" onClick={() => { setEditing(null); setError('') }}>Cancelar</button><button className="primary">Guardar cambios</button></div></fieldset></form> : <div className="directory">{users.map((person) => <div className="balance" key={person.id}><span>{person.name}{person.email && <small> · {person.email}</small>}</span>{person.can_edit && <button className="expense-toggle" onClick={() => setEditing(person)} aria-label={`Editar ${person.name}`}>Editar</button>}</div>)}{!users.length && <p>Aún no hay personas guardadas. Crea un viaje para comenzar.</p>}</div>}
  </div>
}
