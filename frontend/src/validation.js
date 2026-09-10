export const MAX_AMOUNT = '99999999.99'
export const EMAIL_PATTERN = '[^\\s@]+@[^\\s@]+\\.[^\\s@]+'
export function validateAmount(value) {
  if (!/^\d+(\.\d{1,2})?$/.test(String(value)) || Number(value) <= 0 || Number(value) > Number(MAX_AMOUNT)) {
    throw new Error(`Importe: escribe una cantidad mayor que cero, hasta ${MAX_AMOUNT}, con un máximo de dos decimales.`)
  }
}
const messages = {
  'Access email required': 'Indica un correo de acceso antes de conceder el permiso.',
  'Access email already linked': 'Este correo ya está vinculado a otra persona. No se fusionaron las cuentas.',
  'Linked account cannot be reassigned': 'Esta cuenta no se puede reasignar desde este viaje.',
  'Organizer access cannot be changed': 'Los permisos de quien organiza no se pueden cambiar aquí.',
  'Account already linked': 'La cuenta ya está vinculada. Contacta a quien organiza.',

  'Primary payer must have a contribution': 'Pagadores: indica cuánto aportó el primer pagador.',
  'Payer contributions must equal total': 'Pagadores: las aportaciones deben coincidir con el total.',
  'Expense request already used with different data': 'Este intento ya pertenece a otro gasto. Recarga para recuperar sus datos originales.',
  'Custom shares must match participants': 'Reparto: asigna un importe a cada participante seleccionado.',
  'Custom shares must equal total': 'Reparto: la suma de los importes debe coincidir con el total.',
  'Email already registered': 'Correo: ya está registrado. Selecciona la persona existente o usa otro correo.',
  'Invalid email': 'Correo: escribe una dirección válida o deja el campo vacío.',
  'Choose two different people': 'Personas: quien paga y quien recibe deben ser diferentes.',
  'Both people must belong to the group': 'Personas: ambas deben pertenecer al viaje. Actualiza los integrantes.',
  'Duplicate participants are not allowed': 'Participantes: selecciona cada persona una sola vez.',
  'Payer is not a member of this group': 'Quién pagó: selecciona un integrante del viaje.',
  'User is already a member of this group': 'Esta persona ya pertenece al viaje.',
  'Choose an existing organizer or create one': 'Organizador: selecciona una persona existente o escribe una nueva.',
  'Restore the expense before editing': 'Restaura el gasto antes de editarlo.',
}
export function validationMessage(detail) {
  if (typeof detail === 'string') return messages[detail] || null
  if (!Array.isArray(detail)) return null
  return [...new Set(detail.map((entry) => {
    const custom = messages[String(entry.msg).replace(/^Value error, /, '')]
    if (custom) return custom
    const field = entry.loc?.filter((part) => typeof part === 'string').at(-1)
    const labels = { name: 'Nombre', description: 'Descripción', amount: 'Importe', email: 'Correo', payer_id: 'Quién pagó', owner_id: 'Organizador', from_user_id: 'Quién pagó', to_user_id: 'Quién recibió', participants: 'Participantes', group_id: 'Viaje', payment_date: 'Fecha del pago', expense_date: 'Fecha del gasto' }
    if (entry.loc?.includes('payer_contributions')) return 'Pagadores: selecciona personas válidas e importes positivos con hasta dos decimales.'
    if (field === 'custom_shares') return 'Reparto: usa importes desde cero, con un máximo de dos decimales.'
    if (field === 'amount') return `Importe: debe ser mayor que cero, hasta ${MAX_AMOUNT}, con un máximo de dos decimales.`
    if (entry.type === 'string_too_long') return `${labels[field] || 'Campo'}: usa un máximo de ${entry.ctx?.max_length} caracteres.`
    if (field === 'participants') return 'Participantes: selecciona al menos una persona válida, sin repetirla.'
    if (field?.includes('date')) return `${labels[field]}: selecciona una fecha válida.`
    if (field === 'email') return messages['Invalid email']
    return `${labels[field] || 'Datos'}: ${entry.type === 'string_too_short' || entry.type === 'missing' ? 'completa este campo; no puede contener solo espacios.' : 'revisa el valor seleccionado.'}`
  }))].join(' ')
}
