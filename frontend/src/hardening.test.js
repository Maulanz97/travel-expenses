import test from 'node:test'
import assert from 'node:assert/strict'
import { expensePreview } from './expensePreview.js'
import { api, errorMessage } from './api.js'

test('preview preserves all cents and assigns remainder exactly as server', () => {
  assert.deepEqual(expensePreview('10.00', 2, [1, 2, 3]), [{ id: 1, cents: 333 }, { id: 2, cents: 334 }, { id: 3, cents: 333 }])
  assert.deepEqual(expensePreview('0.01', 9, [1, 2, 3]), [{ id: 1, cents: 1 }, { id: 2, cents: 0 }, { id: 3, cents: 0 }])
  for (let count = 1; count <= 50; count++) {
    const shares = expensePreview('99999999.99', 1, Array.from({ length: count }, (_, i) => i + 1))
    assert.equal(shares.reduce((total, share) => total + share.cents, 0), 9999999999)
  }
})
test('invalid amounts and empty participants cannot produce a review', () => {
  for (const amount of ['', '0', '-1', '1.001', 'Infinity', '1e3']) assert.throws(() => expensePreview(amount, 1, [1]))
  assert.throws(() => expensePreview('10', 1, []), /Selecciona/)
})
test('API rejects legacy HTTP 200 validation errors and preserves uncertainty', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify({ message: 'Payer is not a member of this group' })))
  await assert.rejects(api.post('/expenses/', {}), (error) => error.status === 422)
  globalThis.fetch.mock.mockImplementation(async () => { throw new TypeError('offline') })
  await assert.rejects(api.post('/expenses/', {}), (error) => error.uncertain && errorMessage(error).includes('duplicados'))
  globalThis.fetch.mock.mockImplementation(async () => new Response(JSON.stringify({ id: 7 })))
  assert.equal((await api.post('/expenses/', {})).id, 7)
  for (const status of [401, 403, 404, 429, 500]) {
    globalThis.fetch.mock.mockImplementation(async () => new Response('{}', { status }))
    await assert.rejects(api.post('/expenses/', {}), (error) => error.status === status && errorMessage(error).length > 10)
  }
  globalThis.fetch.mock.mockImplementation(async () => new Response('{"id":null}'))
  await assert.rejects(api.post('/expenses/', {}), (error) => error.uncertain)
})
