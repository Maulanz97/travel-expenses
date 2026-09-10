import test from 'node:test'
import assert from 'node:assert/strict'
import { api } from './api.js'
import { loadExpenseDetails } from './expenseDetails.js'
import { formatDate } from './dates.js'

test('details include zero-cent participants without treating an external payer as participant', async (t) => {
  t.mock.method(api, 'get', async (path) => path.endsWith('/split') ? {
    shares: [{ user_id: 1, share: '0.01' }, { user_id: 2, share: '0.00' }],
  } : [{ user_id: 1, name: 'Ana', paid: 0 }, { user_id: 2, name: 'Luis', paid: 0 }, { user_id: 3, name: 'Sofía', paid: '0.01' }])
  const details = await loadExpenseDetails(5)
  assert.equal(details.payer, 'Sofía')
  assert.deepEqual(details.participants.map((p) => p.id), [1, 2])
  assert.equal(details.participants[1].amount, '0.00')
})
test('date-only values preserve the calendar day and do not invent legacy dates', () => {
  assert.equal(formatDate(null), 'Sin fecha registrada')
  assert.match(formatDate('2026-09-01'), /^1 de septiembre de 2026$/)
})
