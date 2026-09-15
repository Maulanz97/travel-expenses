import test from 'node:test'
import assert from 'node:assert/strict'
import { buildShareSummary } from './summaryText.js'

test('summary excludes voided expenses and uses balances after payments without exposing access details', () => {
  const text = buildShareSummary({group:{name:'Oaxaca'}, expenses:[{description:'Cena',amount:'10.10'},{description:'Taxi',amount:'0.20'},{description:'Anulado',amount:99,voided:true}], balances:[{name:'Ana',balance:'5.15',email:'private@example.com'},{name:'Luis',balance:'-5.15'},{name:'Sol',balance:0}], settlements:[{from_user:'Luis',to_user:'Ana',amount:'5.15'}]})
  assert.match(text, /Total gastado: \$10\.30/)
  assert.match(text, /Ana: recibe \$5\.15/)
  assert.match(text, /Luis: debe \$5\.15/)
  assert.match(text, /Sol: al día/)
  assert.match(text, /Luis paga \$5\.15 a Ana/)
  assert.doesNotMatch(text, /Anulado|private@example/)
})
test('empty trip has a usable summary', () => {
  const text = buildShareSummary({group:{name:'Viaje'},expenses:[],balances:[],settlements:[]})
  assert.match(text, /Total gastado: \$0\.00/)
  assert.match(text, /Sin gastos registrados/)
  assert.match(text, /No hay pagos pendientes/)
})
