import { validateAmount } from './validation.js'
// Matches the server's integer-cent split, including its remainder recipient.
export function expensePreview(amount, payerId, participants) {
  validateAmount(amount)
  if (!/^\d+(\.\d{1,2})?$/.test(String(amount))) throw new Error('Escribe un monto positivo con hasta dos decimales.')
  const [whole, fraction = ''] = String(amount).split('.')
  const cents = Number(whole) * 100 + Number(fraction.padEnd(2, '0'))
  if (!Number.isSafeInteger(cents) || cents <= 0) throw new Error('El monto debe ser positivo y estar dentro del límite permitido.')
  if (!participants.length) throw new Error('Selecciona al menos una persona para dividir el gasto.')
  const base = Math.floor(cents / participants.length)
  const remainder = cents % participants.length
  const recipient = participants.includes(payerId) ? payerId : participants[0]
  return participants.map((id) => ({ id, cents: base + (id === recipient ? remainder : 0) }))
}
