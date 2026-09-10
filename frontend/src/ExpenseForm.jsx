import { MAX_AMOUNT } from './validation'
import { useEffect, useRef, useState } from 'react'
import { api, errorMessage } from './api'
import { readSplit } from './customSplit'
import PayerFields from './PayerFields'
import { readPayers, contributions } from './payers'
import SplitFields from './SplitFields'
import { todayLocal } from './dates'
import { loadPendingExpense, savePendingExpense, clearPendingExpense } from './pendingExpense'

const money = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN', currencyDisplay: 'code' })

export default function ExpenseForm({ members, group, onSaved, onBusy, onNavigate }) {
  const [initial] = useState(() => {
    try { return { review: group ? loadPendingExpense(group.id) : null } }
    catch { return { error: 'No se pudo recuperar el intento pendiente. Habilita el almacenamiento del navegador y recarga antes de registrar gastos.' } }
  })
  const [review, setReview] = useState(initial.review || null)
  const [error, setError] = useState(initial.error || '')
  const [amountInput, setAmountInput] = useState('')
  const [formVersion, setFormVersion] = useState(0)
  const [saving, setSaving] = useState(false)
  const [uncertain, setUncertain] = useState(Boolean(initial.review))
  const lock = useRef(false)
  const form = useRef(null)
  const heading = useRef(null)
  const errorBox = useRef(null)
  useEffect(() => { if (review) heading.current?.focus() }, [review])
  useEffect(() => { if (error) errorBox.current?.focus() }, [error])

  if (!group) return <div className="empty"><h2>Selecciona un viaje</h2><p>Primero crea o elige el viaje al que pertenece este gasto.</p><button className="secondary" onClick={() => onNavigate('trips')}>Ir a Viajes</button></div>
  if (!members.length) return <div className="empty"><h2>Agrega integrantes</h2><p>Agrega a quienes compartirán los gastos del viaje.</p><button className="secondary" onClick={() => onNavigate('members')}>Ir a Integrantes</button></div>

  function preview(event) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    try {
      const description = String(data.get('description')).trim()
      if (!description) throw new Error('Escribe una descripción; no puede contener solo espacios.')
      const participants = data.getAll('participant').map(Number)
      const amount = String(data.get('amount'))
      const { payer_id, payer_contributions } = readPayers(data, amount)
      const { shares, custom_shares } = readSplit(data, amount, payer_id, participants)
      setError('')
      setReview({ request_id: crypto.randomUUID(), description, amount, payer_id, payer_contributions, participants, shares, custom_shares, group_id: group.id, expense_date: data.get('expenseDate') })
    } catch (failure) { setError(failure.message) }
  }

  async function confirm() {
    if (lock.current || initial.error) return
    try { savePendingExpense(review) }
    catch (failure) { setError(`No se envió el gasto. ${failure.message}`); return }
    lock.current = true
    setSaving(true)
    onBusy(true)
    setError('')
    let saved
    try {
      const { shares: _shares, ...payload } = review
      saved = await api.post('/expenses/', payload)
    } catch (failure) {
      const pending = uncertain || Boolean(failure.uncertain)
      setError(failure.uncertain ? 'No pudimos confirmar el resultado. Puedes reintentar este mismo gasto sin duplicarlo.' : errorMessage(failure))
      setUncertain(pending)
      if (!pending) {
        try { clearPendingExpense(review) }
        catch { setUncertain(true) }
      }
      lock.current = false
      setSaving(false)
      onBusy(false)
      return
    }
    try { clearPendingExpense(review) }
    catch {
      setError('El gasto está guardado, pero no pudimos limpiar el intento pendiente. Puedes confirmarlo otra vez sin duplicarlo.')
      setUncertain(true)
      setSaving(false)
      onBusy(false)
      lock.current = false
      return
    }
    setUncertain(false)
    form.current?.reset()
    setFormVersion(v => v + 1)
    setAmountInput('')
    setReview(null)
    setSaving(false)
    // A successful write must never be retried merely because refreshing failed.
    try { await onSaved(saved) }
    finally { onBusy(false); lock.current = false }
  }

  return <div className="expense-flow" aria-busy={saving}>
    {error && <p className="alert error" role="alert" tabIndex={-1} ref={errorBox}>{error}</p>}
    <form ref={form} className="form" onChange={event => setAmountInput(event.currentTarget.elements.amount.value)} onSubmit={preview} hidden={Boolean(review)}>
      <h2>Registrar gasto</h2>
      <section className="form-section"><h3>Datos del gasto</h3><label>¿Qué pagaron?<input required name="description" maxLength={500} placeholder="Ej. Cena en el centro" /></label>
      <label>Fecha del gasto<input required type="date" name="expenseDate" defaultValue={todayLocal()} /></label>
      <label>Monto total (MXN)<input required name="amount" type="number" min="0.01" max={MAX_AMOUNT} step="0.01" inputMode="decimal" placeholder="0.00" /></label>
      </section><section className="form-section"><h3>Quién pagó</h3><PayerFields key={formVersion} members={members} amount={amountInput} />
      </section><section className="form-section"><SplitFields members={members} /></section>
      <button className="primary" disabled={Boolean(initial.error)}>Revisar reparto</button>
    </form>
    {review && <section className="form review" aria-labelledby="review-title">
      <h2 id="review-title" tabIndex={-1} ref={heading}>Confirma el reparto</h2>
      <p>{uncertain ? 'Hay un intento pendiente de confirmar. Recuperaremos el gasto si ya se guardó.' : 'Todavía no se ha enviado el gasto.'}</p>
      <dl><dt>Viaje</dt><dd>{group.name}</dd><dt>Descripción</dt><dd>{review.description}</dd><dt>Total</dt><dd>{money.format(review.amount)}</dd><dt>{review.payer_contributions ? "Pagaron" : "Pagó"}</dt><dd>{contributions(review).map(p => <div key={p.id}>{members.find(item => item.user_id === p.id)?.name || `Persona ${p.id}`}: {money.format(p.amount)}</div>)}</dd></dl>
      <h3>A cada persona le corresponde</h3>
      <ul className="share-list">{review.shares.map(({ id, cents }) => <li key={id}><span>{members.find((item) => item.user_id === id)?.name}</span><strong>{money.format(cents / 100)}</strong></li>)}</ul>
      {!review.custom_shares && <p className="form-help">El total se reparte en centavos. Si sobra algún centavo, se asigna al primer pagador si participa; de lo contrario, a la primera persona seleccionada. Estos importes son participaciones en este gasto, no los pagos finales del viaje.</p>}
      <div className="form-actions"><button type="button" className="secondary" disabled={saving || uncertain} onClick={() => { setReview(null); setError(''); requestAnimationFrame(() => form.current?.elements.description.focus()) }}>Volver a editar</button><button type="button" className="primary" disabled={saving} onClick={confirm}>{saving ? 'Confirmando…' : uncertain ? 'Reintentar confirmación' : 'Confirmar gasto'}</button></div>
      {uncertain && <p>Se conserva el mismo intento al recargar o regresar a este viaje en este navegador. Confírmalo antes de registrar otro gasto.</p>}
    </section>}
  </div>
}
