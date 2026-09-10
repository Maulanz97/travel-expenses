import test from 'node:test'
import assert from 'node:assert/strict'
import { loadPendingExpense, savePendingExpense, clearPendingExpense, setPendingExpenseOwner } from './pendingExpense.js'

function storage() {
  const data = new Map()
  return { getItem: k => data.get(k) ?? null, setItem: (k, v) => data.set(k, v), removeItem: k => data.delete(k) }
}
const review = { request_id: 'original', group_id: 1, amount: '12.00', participants: [1], shares: [{ id: 1, cents: 1200 }] }
test('reload recovers exact request and other trips remain independent', () => {
  const disk = storage()
  savePendingExpense(review, disk)
  assert.deepEqual(loadPendingExpense(1, disk), review)
  assert.equal(loadPendingExpense(2, disk), null)
  assert.throws(() => savePendingExpense({ ...review, request_id: 'new' }, disk))
  clearPendingExpense({ ...review, request_id: 'new' }, disk)
  assert.deepEqual(loadPendingExpense(1, disk), review)
  clearPendingExpense(review, disk)
  assert.equal(loadPendingExpense(1, disk), null)
})
test('storage failure is propagated before sending a request', () => {
  assert.throws(() => savePendingExpense(review, { getItem: () => null, setItem: () => { throw new Error('Quota exceeded') } }))
  assert.throws(() => loadPendingExpense(1, { getItem: () => '{invalid' }))
})
test('pending requests stay isolated when another account signs in', () => {
  const disk = storage()
  try {
    setPendingExpenseOwner('account-a')
    savePendingExpense(review, disk)
    setPendingExpenseOwner('account-b')
    assert.equal(loadPendingExpense(1, disk), null)
    setPendingExpenseOwner('account-a')
    assert.deepEqual(loadPendingExpense(1, disk), review)
  } finally { setPendingExpenseOwner('') }
})
