import test from 'node:test'
import assert from 'node:assert/strict'
import { validatePublicEnvironment } from './publicEnvironment.js'
const legacy = role => `header.${Buffer.from(JSON.stringify({ role })).toString('base64url')}.signature`
test('only public Supabase keys may enter a frontend build', () => {
  for (const key of ['', 'sb_publishable_example', legacy('anon')]) {
    assert.doesNotThrow(() => validatePublicEnvironment({ VITE_SUPABASE_PUBLISHABLE_KEY: key }))
  }
  for (const key of ['sb_secret_example', legacy('service_role'), 'invalid']) {
    assert.throws(() => validatePublicEnvironment({ VITE_SUPABASE_PUBLISHABLE_KEY: key }), error => !error.message.includes(key))
  }
  assert.throws(() => validatePublicEnvironment({ VITE_LOCAL_DEV_TOKEN: 'private-token' }))
  assert.doesNotThrow(() => validatePublicEnvironment({ LOCAL_DEV_TOKEN: 'server-only' }))
})
