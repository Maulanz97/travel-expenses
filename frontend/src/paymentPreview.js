import { validateAmount } from './validation.js'
function cents(value) {
  const match = /^(-?)(\d+)(?:\.(\d{1,2}))?$/.exec(String(value))
  if (!match) throw new Error('Escribe un importe con hasta dos decimales.')
  const amount = Number(match[2]) * 100 + Number((match[3] || '').padEnd(2, '0'))
  if (!Number.isSafeInteger(amount)) throw new Error('El importe supera el límite permitido.')
  return match[1] ? -amount : amount
}

export function paymentPreview(balances, from, to, amount) {
  validateAmount(amount)
  const paid = cents(amount)
  if (paid <= 0 || from === to) throw new Error('Elige dos personas diferentes y un importe positivo.')
  const before = (id) => cents(balances.find((person) => person.user_id === id)?.balance ?? 0)
  return [
    { id: from, before: before(from), after: before(from) + paid },
    { id: to, before: before(to), after: before(to) - paid },
  ]
}
