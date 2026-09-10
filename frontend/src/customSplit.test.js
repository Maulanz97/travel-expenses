import test from 'node:test'
import assert from 'node:assert/strict'
import { readSplit } from './customSplit.js'
test('custom amounts preserve cents, zero and total', () => {
  const data = new FormData()
  data.set('splitKind', 'custom'); data.set('share-1','0'); data.set('share-2','10.01')
  assert.deepEqual(readSplit(data,'10.01',1,[1,2]).custom_shares,{1:'0.00',2:'10.01'})
  data.set('share-2','10')
  assert.throws(() => readSplit(data,'10.01',1,[1,2]), /faltan/)
  data.set('share-2','11')
  assert.throws(() => readSplit(data,'10.01',1,[1,2]), /sobran/)
  data.set('splitKind','equal')
  assert.equal(readSplit(data,'10.01',1,[1,2]).custom_shares,null)
})
