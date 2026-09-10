import test from 'node:test'
import assert from 'node:assert/strict'
import { readPayers, contributions } from './payers.js'
const data = (ids, amounts) => ({ getAll: name => name === 'expensePayer' ? ids : amounts })
test('one payer needs no manual amount; multiple payers preserve cents', () => {
  assert.deepEqual(readPayers(data(['1'], []), '10'), { payer_id: 1, payer_contributions: null })
  assert.deepEqual(readPayers(data(['1','2'], ['0.01','9.99']), '10'), { payer_id: 1, payer_contributions: { 1: '0.01', 2: '9.99' } })
  assert.deepEqual(contributions({ payer_id: 1, amount: '10' }), [{ id: 1, amount: '10' }])
})
test('incomplete, duplicate, excess and nonpositive contributions cannot be confirmed', () => {
  for (const [ids, values] of [[['1','1'],['5','5']], [['1',''],['5','5']], [['1','2'],['0','10']], [['1','2'],['7','7']], [['1','2'],['2','3']], [['1','2'],['2.001','7.999']]]) {
    assert.throws(() => readPayers(data(ids, values), '10'))
  }
})
