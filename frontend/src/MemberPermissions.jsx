import { useState } from 'react'
import { api, errorMessage } from './api'

function MemberPermission({ member, groupId, onChanged, onBusy }) {
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  async function save(event) {
    event.preventDefault()
    if (pending) return
    const data = new FormData(event.currentTarget)
    setPending(true); onBusy(true); setError('')
    try {
      await api.put(`/group-members/group/${groupId}/access/${member.user_id}`, {
        login_email: member.account_linked ? member.login_email : String(data.get('loginEmail') || '').trim() || null,
        can_register_expenses: data.get('canRegister') === 'on',
      })
      await onChanged(); setOpen(false)
    } catch (failure) { setError(errorMessage(failure)) }
    finally { setPending(false); onBusy(false) }
  }
  return <div className="member-permission"><p><strong>{member.name}</strong> · {member.role === 'owner' ? 'Organiza' : member.can_register_expenses ? 'Puede registrar gastos' : 'Solo consulta'}</p>
    {member.role !== 'owner' && <button type="button" className="secondary" disabled={pending} aria-expanded={open} onClick={() => setOpen(!open)}>Permisos de {member.name}</button>}
    {open && <form className="form" onSubmit={save}><fieldset className="pending-fields" disabled={pending}>
      {member.account_linked ? <p>Cuenta vinculada: {member.login_email}</p> : <label>Correo para acceder<input type="email" name="loginEmail" defaultValue={member.login_email || ''} maxLength={320} /></label>}
      <label className="permission-check"><input type="checkbox" name="canRegister" defaultChecked={member.can_register_expenses} />Puede registrar gastos</label>
      <p className="form-help">Con este permiso puede crear gastos y editar o anular los que registró. Los pagos los administra quien organiza.</p>
      {!member.account_linked && <p className="form-help">Este correo vinculará a la persona cuando entre con Google o lo verifique al crear su cuenta. No se envía una invitación automáticamente. Sin correo, puede seguir participando en las cuentas.</p>}
      {error && <p role="alert" className="alert error">{error}</p>}<button className="primary">{pending ? 'Guardando…' : 'Guardar permisos'}</button>
    </fieldset></form>}
  </div>
}
export default function MemberPermissions({ members, groupId, onChanged, onBusy }) {
  return <section className="card member-access"><h3>Acceso al viaje</h3>{members.map(member => <MemberPermission key={member.user_id} member={member} groupId={groupId} onChanged={onChanged} onBusy={onBusy} />)}</section>
}
