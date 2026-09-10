import { expensePreview } from './expensePreview.js'
import { MAX_AMOUNT } from './validation.js'

export function readSplit(data, amount, payer, ids) {
  const equal = expensePreview(amount, payer, ids)
  if (data.get('splitKind') !== 'custom') return { shares: equal, custom_shares: null }
  const shares = ids.map((id) => {
    const value = String(data.get(`share-${id}`) ?? '')
    if (!/^\d+(\.\d{1,2})?$/.test(value) || Number(value) > Number(MAX_AMOUNT)) throw new Error('Reparto: completa cada importe con cero o una cantidad positiva de hasta dos decimales.')
    const [whole, fraction = ''] = value.split('.')
    return { id, cents: Number(whole) * 100 + Number(fraction.padEnd(2, '0')) }
  })
  const difference = equal.reduce((sum, p) => sum + p.cents, 0) - shares.reduce((sum, p) => sum + p.cents, 0)
  if (difference) throw new Error(`Reparto: ${difference > 0 ? 'faltan por asignar' : 'sobran'} $${(Math.abs(difference) / 100).toFixed(2)}. La suma debe coincidir con el total.`)
  return { shares, custom_shares: Object.fromEntries(shares.map((p) => [p.id, (p.cents / 100).toFixed(2)])) }
}
