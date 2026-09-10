import { MAX_AMOUNT } from './validation'
import { useEffect, useRef, useState } from 'react'
import { api, errorMessage } from './api'
import { todayLocal, formatDate } from './dates'
import { paymentPreview } from './paymentPreview'
import PaymentImpact from './PaymentImpact'

const money = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN', currencyDisplay: 'code' })

export default function PaymentForm({ group, members, balances, suggestion, onSaved, onCancel, onBusy }) {
  const [impact, setImpact] = useState(null)
  const [review, setReview] = useState(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [uncertain, setUncertain] = useState(false)
  const lock = useRef(false)
  const title = useRef(null)
  const form = useRef(null)
  useEffect(() => { title.current?.focus() }, [review])
  const name = (id) => members.find((person) => person.user_id === id)?.name || 'Persona no disponible'

  function preview(event) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const from_user_id = Number(data.get('from'))
    const to_user_id = Number(data.get('to'))
    if (from_user_id === to_user_id) { setError('Elige dos personas diferentes.'); return }
    try { setImpact(paymentPreview(balances, from_user_id, to_user_id, data.get('amount'))) }
    catch (failure) { setError(failure.message); return }
    setError('')
    setReview({ group_id: group.id, from_user_id, to_user_id, amount: data.get('amount'), payment_date: data.get('date'), request_id: crypto.randomUUID() })
  }

  async function save() {
    if (lock.current) return
    lock.current = true; setPending(true); onBusy(true); setError('')
    let payment
    try { payment = await api.post('/payments/', review) }
    catch (failure) {
      setUncertain(Boolean(failure.uncertain))
      setError(failure.uncertain ? 'No recibimos confirmación. Puedes reintentar este mismo pago sin duplicarlo.' : errorMessage(failure))
      lock.current = false; setPending(false); onBusy(false)
      return
    }
    await onSaved(payment)
    onBusy(false); lock.current = false
  }

  if (members.length < 2) return <div className="empty"><h2>Agrega otro integrante</h2><p>Necesitas al menos dos personas en el viaje para registrar un pago.</p><button className="secondary" onClick={onCancel}>Volver al resumen</button></div>

  return <section className="payment-form" aria-busy={pending}>
    <h2 tabIndex={-1} ref={title}>{review ? 'Confirma el pago' : 'Registrar pago'}</h2>
    <p className="form-help">Registra dinero que ya se entregó entre integrantes. Puede ser un pago parcial; no aumenta los gastos del viaje.</p>
    {error && <p className="alert error" role="alert">{error}</p>}
    <form ref={form} className="form" hidden={Boolean(review)} onSubmit={preview}>
      <section className="form-section"><h3>Entre quiénes</h3><label>¿Quién pagó?<select required name="from" defaultValue={suggestion?.from_user_id || ''}><option value="" disabled>Selecciona una persona</option>{members.map((person) => <option key={person.user_id} value={person.user_id}>{person.name}</option>)}</select></label>
      <label>¿Quién recibió?<select required name="to" defaultValue={suggestion?.to_user_id || ''}><option value="" disabled>Selecciona una persona</option>{members.map((person) => <option key={person.user_id} value={person.user_id}>{person.name}</option>)}</select></label>
      </section><section className="form-section"><h3>Datos del pago</h3><label>Importe pagado (MXN)<input required name="amount" type="number" inputMode="decimal" min="0.01" max={MAX_AMOUNT} step="0.01" defaultValue={suggestion ? Number(suggestion.amount).toFixed(2) : ''} /></label>
      <label>Fecha del pago<input required type="date" name="date" defaultValue={todayLocal()} /></label>
      </section><div className="form-actions"><button type="button" className="secondary" onClick={onCancel}>Cancelar</button><button className="primary">Revisar pago</button></div>
    </form>
    {review && <div className="form review"><dl><dt>Pagó</dt><dd>{name(review.from_user_id)}</dd><dt>Recibió</dt><dd>{name(review.to_user_id)}</dd><dt>Importe</dt><dd>{money.format(review.amount)}</dd><dt>Fecha</dt><dd>{formatDate(review.payment_date)}</dd></dl><PaymentImpact impact={impact} name={name} /><div className="form-actions"><button type="button" className="secondary" disabled={pending || uncertain} onClick={() => { setReview(null); setError('') }}>Volver a editar</button><button type="button" className="primary" disabled={pending} onClick={save}>{pending ? 'Guardando…' : uncertain ? 'Reintentar el mismo pago' : 'Confirmar pago'}</button></div></div>}
  </section>
}
