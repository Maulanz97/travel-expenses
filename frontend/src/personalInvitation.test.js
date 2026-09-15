import test from 'node:test'
import assert from 'node:assert/strict'
import { captureInvitation, storageKey } from './invitationStorage.js'

test('invitation survives OAuth return without keeping token in the address', () => {
  const values = new Map()
  const token = 'x'.repeat(43)
  globalThis.location = { hash: `#invite=${token}`, pathname: '/', search: '' }
  globalThis.sessionStorage = { setItem: (key, value) => values.set(key, value), getItem: key => values.get(key) }
  let replaced
  globalThis.history = { replaceState: (_state, _title, url) => { replaced = url } }
  assert.equal(captureInvitation(), token)
  assert.equal(replaced, '/')
  assert.equal(values.get(storageKey), token)
  location.hash = ''; location.search = '?code=oauth-code'
  assert.equal(captureInvitation(), token)
  assert.equal(location.search, '?code=oauth-code')
  delete globalThis.location; delete globalThis.sessionStorage; delete globalThis.history
})
