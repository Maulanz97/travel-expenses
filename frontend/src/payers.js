import { validateAmount } from './validation.js'
export function contributions(expense) {
  return Object.entries(expense.payer_contributions || { [expense.payer_id]: expense.amount }).map(([id, amount]) => ({ id: Number(id), amount }))
}
export function readPayers(data, amount) {
  const ids = data.getAll('expensePayer').map(Number)
  if (!ids.length || ids.some(id => !Number.isInteger(id) || id <= 0) || new Set(ids).size !== ids.length) throw new Error('Selecciona pagadores diferentes.')
  if (ids.length === 1) return { payer_id: ids[0], payer_contributions: null }
  const values = data.getAll('payerAmount').map(String)
  if (values.length !== ids.length) throw new Error('Completa las aportaciones de los pagadores.')
  values.forEach(validateAmount)
  validateAmount(amount)
  const difference = Math.round(Number(amount) * 100) - values.reduce((sum, value) => sum + Math.round(Number(value) * 100), 0)
  if (difference) throw new Error(`Pagadores: ${difference > 0 ? 'faltan' : 'sobran'} $${(Math.abs(difference) / 100).toFixed(2)}. Las aportaciones deben coincidir con el total.`)
  return { payer_id: ids[0], payer_contributions: Object.fromEntries(ids.map((id, i) => [id, values[i]])) }
}
