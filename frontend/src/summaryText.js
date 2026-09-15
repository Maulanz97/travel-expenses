const money = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' })
const line = value => String(value ?? '').replace(/[\r\n]+/g, ' ').trim()

export function buildShareSummary({ group, expenses, balances, settlements, generatedAt = new Date() }) {
  const active = expenses.filter(expense => !expense.voided)
  const cents = active.reduce((total, expense) => total + Math.round(Number(expense.amount) * 100), 0)
  return [
    `Resumen de gastos · ${line(group.name)}`,
    `Generado: ${new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium', timeStyle: 'short' }).format(generatedAt)}`,
    'Moneda: MXN',
    `Total gastado: ${money.format(cents / 100)}`,
    '', 'Gastos registrados:',
    ...(active.length ? active.map(expense => `• ${line(expense.description)}: ${money.format(expense.amount)}`) : ['Sin gastos registrados.']),
    '', 'Balances:',
    ...(balances.length ? balances.map(person => {
      const amount = Number(person.balance)
      return `• ${line(person.name)}: ${amount > 0 ? 'recibe ' + money.format(amount) : amount < 0 ? 'debe ' + money.format(-amount) : 'al día'}`
    }) : ['Sin movimientos.']),
    '', 'Para quedar a mano:',
    ...(settlements.length ? settlements.map(payment => `• ${line(payment.from_user)} paga ${money.format(payment.amount)} a ${line(payment.to_user)}.`) : ['No hay pagos pendientes.']),
    '', 'Los balances incluyen los pagos registrados. No se incluyen movimientos anulados.',
    'Este resumen es una copia de los datos consultados; no se actualiza automáticamente.',
  ].join('\n')
}
