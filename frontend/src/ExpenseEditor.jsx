import { MAX_AMOUNT } from './validation'
import { useState, useRef } from 'react'
import { api, errorMessage } from './api'
import { readSplit } from './customSplit'
import PayerFields from './PayerFields'
import { readPayers, contributions } from './payers'
import SplitFields from './SplitFields'
import { formatDate } from './dates'

const money = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' })
const fields = { description: 'Descripción', amount: 'Importe', expense_date: 'Fecha', payer: 'Pagó', payer_contributions: 'Aportaciones', participants: 'Participantes', voided: 'Anulado', custom_shares: 'Reparto personalizado' }
const display = (key, value) => key === 'amount' ? money.format(value) : key === 'expense_date' ? formatDate(value) : Array.isArray(value) ? value.join(', ') : typeof value === 'boolean' ? value ? 'Sí' : 'No' : value

export function ExpenseHistory({ history = [] }) {
  return <details><summary>Historial de cambios ({history.length})</summary>{history.length ? history.slice().reverse().map((entry, index) => <div key={index}><p><strong>{entry.action}</strong> · {new Date(entry.at).toLocaleString('es-MX')}</p><ul>{Object.keys(fields).filter((key) => JSON.stringify(entry.before[key]) !== JSON.stringify(entry.after[key])).map((key) => <li key={key}>{fields[key]}: {display(key, entry.before[key])} → {display(key, entry.after[key])}</li>)}</ul></div>) : <p>Aún no hay cambios registrados.</p>}</details>
}

export default function ExpenseEditor({ expense, participants, members, balances, onDone, onBusy, onCancel, mode }) {
  const [amountInput, setAmountInput] = useState(String(expense.amount))
  const [review, setReview] = useState(null)
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const lock = useRef(false)
  const name = (id) => members.find((p) => p.user_id === Number(id))?.name || String(id)
  const old = { description: expense.description, amount: expense.amount, expense_date: expense.expense_date, payer: name(expense.payer_id), payer_contributions: contributions(expense).map(p => `${name(p.id)}: ${money.format(p.amount)}`), participants: participants.map((p) => name(p.id)), custom_shares: participants.map((p) => `${name(p.id)}: ${money.format(p.amount)}`) }
  function preview(event) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    try {
      const draft = { description: String(data.get('description')).trim(), amount: data.get('amount'), expense_date: data.get('date') || null, ...readPayers(data, data.get('amount')), participants: data.getAll('person').map(Number) }
      if (!draft.description) throw new Error('Escribe una descripción.')
      const { shares, custom_shares } = readSplit(data, draft.amount, draft.payer_id, draft.participants)
      setReview({ ...draft, shares, custom_shares }); setError('')
    } catch (failure) { setError(failure.message) }
  }
  async function save() {
    if (lock.current) return
    lock.current = true; setPending(true); onBusy(true); setError('')
    try {
      if (mode === 'edit') {
        const { shares: _shares, ...payload } = review
        await api.put(`/expenses/${expense.id}`, payload)
      } else await api.post(`/expenses/${expense.id}/${mode}`)
      await onDone()
    } catch (failure) { setError(errorMessage(failure)) }
    finally { lock.current = false; setPending(false); onBusy(false) }
  }
  const next = review && { ...review, payer: name(review.payer_id), payer_contributions: contributions(review).map(p => `${name(p.id)}: ${money.format(p.amount)}`), participants: review.participants.map(name), custom_shares: review.shares.map((p) => `${name(p.id)}: ${money.format(p.cents / 100)}`) }
  const showReview = mode !== 'edit' || review
  const projected = new Map(balances.map((p) => [p.user_id, Math.round(Number(p.balance) * 100)]))
  const change = (id, cents) => projected.set(id, (projected.get(id) || 0) + cents)
  if (!expense.voided) {
    contributions(expense).forEach(p => change(p.id, -Math.round(Number(p.amount) * 100)))
    participants.forEach((p) => change(p.id, Math.round(Number(p.amount) * 100)))
  }
  if (mode === 'restore') {
    contributions(expense).forEach(p => change(p.id, Math.round(Number(p.amount) * 100)))
    participants.forEach((p) => change(p.id, -Math.round(Number(p.amount) * 100)))
  } else if (review) {
    contributions(review).forEach(p => change(p.id, Math.round(Number(p.amount) * 100)))
    review.shares.forEach((p) => change(p.id, -p.cents))
  }
  return <section className="expense-editor" aria-busy={pending}>
    <h3>{mode === 'edit' ? 'Editar gasto' : mode === 'void' ? 'Anular gasto' : 'Restaurar gasto'}</h3>
    {error && <p role="alert" className="alert error">{error}</p>}
    {mode === 'edit' && <form className="form" onChange={event => setAmountInput(event.currentTarget.elements.amount.value)} hidden={Boolean(review)} onSubmit={preview}>
      <section className="form-section"><h4>Datos del gasto</h4><label>Descripción<input required maxLength={500} name="description" defaultValue={expense.description} /></label>
      <label>Fecha del gasto<input type="date" name="date" defaultValue={expense.expense_date || ''} /></label>
      <label>Importe (MXN)<input required type="number" inputMode="decimal" min="0.01" max={MAX_AMOUNT} step="0.01" name="amount" defaultValue={expense.amount} /></label>
      </section><section className="form-section"><h4>Quién pagó</h4><PayerFields members={members} amount={amountInput} initial={expense} />
      </section><section className="form-section"><SplitFields members={members} initialIds={participants.map((p) => p.id)} initialShares={expense.custom_shares} inputName="person" /></section>
      <div className="form-actions"><button type="button" className="secondary" onClick={onCancel}>Cancelar</button><button className="primary">Revisar cambios</button></div>
    </form>}
    {showReview && <>
      {next ? <><h4>Cambios propuestos</h4><ul>{Object.keys(old).filter((key) => JSON.stringify(old[key]) !== JSON.stringify(next[key])).map((key) => <li key={key}>{fields[key]}: {display(key, old[key])} → {display(key, next[key])}</li>)}</ul><h4>Nuevo reparto</h4><ul>{review.shares.map((p) => <li key={p.id}>{name(p.id)}: {money.format(p.cents / 100)}</li>)}</ul></> : <p>Se {mode === 'void' ? 'anulará' : 'restaurará'} «{expense.description}», por {money.format(expense.amount)}. Se recalcularán el total y los balances.</p>}
      <h4>Así quedarían los balances</h4><ul>{Array.from(projected, ([id, cents]) => <li key={id}>{name(id)}: {cents > 0 ? 'Recibe' : cents < 0 ? 'Debe' : 'Al día'} {money.format(Math.abs(cents) / 100)}</li>)}</ul>
      <p>Los pagos ya registrados se conservan. Esta previsión usa los datos del resumen actual.</p>
      <div className="form-actions"><button type="button" className="secondary" disabled={pending} onClick={onCancel}>Cancelar</button>{review && <button type="button" className="secondary" disabled={pending} onClick={() => setReview(null)}>Volver a editar</button>}<button type="button" className="primary" disabled={pending} onClick={save}>{pending ? 'Guardando…' : mode === 'edit' ? 'Guardar cambios' : mode === 'void' ? 'Confirmar anulación' : 'Confirmar restauración'}</button></div>
    </>}
  </section>
}
