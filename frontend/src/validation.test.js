import test from 'node:test'
import assert from 'node:assert/strict'
import { validateAmount, validationMessage } from './validation.js'
test('shared amount boundaries', () => {
  for (const value of ['0.01', '99999999.99']) validateAmount(value)
  for (const value of ['0', '-1', '0.001', '100000000', 'NaN', 'Infinity']) assert.throws(() => validateAmount(value))
})
test('validation errors identify fields without exposing server details', () => {
  assert.match(validationMessage([{ loc: ['body', 'amount'], type: 'decimal_max_places' }]), /Importe:/)
  assert.match(validationMessage([{ loc: ['body', 'name'], type: 'string_too_long', ctx: { max_length: 100 } }]), /100 caracteres/)
  assert.match(validationMessage('Email already registered'), /Correo:/)
  assert.equal(validationMessage('SQL internal error'), null)
})
