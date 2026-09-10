import { api } from './api.js'

export async function loadExpenseDetails(expenseId) {
  const [split, balances] = await Promise.all([
    api.get(`/expenses/${expenseId}/split`),
    api.get(`/expenses/${expenseId}/balances`),
  ])
  return {
    payers: balances.filter(person => Number(person.paid) > 0).map(person => ({ id: person.user_id, name: person.name, amount: person.paid })),
    payer: balances.find((person) => Number(person.paid) > 0)?.name || 'Persona no disponible',
    participants: split.shares.map((share) => ({
      id: share.user_id,
      name: balances.find((person) => person.user_id === share.user_id)?.name || 'Persona no disponible',
      amount: share.share,
    })),
  }
}
