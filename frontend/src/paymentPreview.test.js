import test from 'node:test'
import assert from 'node:assert/strict'
import { paymentPreview } from './paymentPreview.js'

test('partial, exact and excess payments preserve the combined balance', () => {
  for (const [amount, expected] of [['200', -30000], ['500', 0], ['650', 15000]]) {
    const result = paymentPreview([{ user_id: 1, balance: '-500' }, { user_id: 2, balance: '500' }], 1, 2, amount)
    assert.equal(result[0].after, expected)
    assert.equal(result[0].after + result[1].after, 0)
  }
})
test('advances and payments between people with unequal group balances', () => {
  assert.equal(paymentPreview([], 1, 2, '0.01')[0].after, 1)
  const result = paymentPreview([{ user_id: 1, balance: '-100.01' }, { user_id: 2, balance: '30' }], 1, 2, '40.01')
  assert.equal(result[0].after, -6000)
  assert.equal(result[1].after, -1001)
})
test('invalid payment amounts and self payments are rejected', () => {
  for (const amount of ['0', '-1', '1.001', 'NaN']) assert.throws(() => paymentPreview([], 1, 2, amount))
  assert.throws(() => paymentPreview([], 1, 1, '10'))
})
