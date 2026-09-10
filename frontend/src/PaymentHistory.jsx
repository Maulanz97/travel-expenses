import { useTripAccess } from './TripAccess'
import { useRef, useState } from 'react'
import { api, errorMessage } from './api'
import { formatDate } from './dates'

const money = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' })

export default function PaymentHistory({ payments, onChanged, onBusy }) {
  const { isOwner } = useTripAccess()
  const [confirm, setConfirm] = useState(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const lock = useRef(false)
  async function cancelPayment(id) {
    if (lock.current) return
    lock.current = true; setPending(true); onBusy(true); setError('')
    try { await api.post(`/payments/${id}/void`, {}); await onChanged() }
    catch (failure) { setError(errorMessage(failure)) }
    finally { lock.current = false; setPending(false); onBusy(false); setConfirm(null) }
  }
  return <details className="payment-history"><summary>Pagos registrados ({payments.length})</summary>
    {error && <p role="alert">{error}</p>}
    {payments.length ? <ul>{payments.map((payment) => <li key={payment.id}>
      <div><span>{payment.from_user} pagó a {payment.to_user}</span><small>{formatDate(payment.payment_date)}{payment.voided ? ' · Anulado' : ''}</small></div><strong>{money.format(payment.amount)}</strong>
      {isOwner && !payment.voided && <button type="button" className="expense-toggle" disabled={pending} onClick={() => setConfirm(payment.id)}>Anular</button>}
      {isOwner && confirm === payment.id && <div className="payment-cancel"><p>¿Anular este registro? El pago dejará de contar en los balances. No se devuelve dinero.</p><button className="secondary" disabled={pending} onClick={() => setConfirm(null)}>Conservar</button><button className="secondary" disabled={pending} onClick={() => cancelPayment(payment.id)}>{pending ? 'Anulando…' : 'Confirmar anulación'}</button></div>}
    </li>)}</ul> : <p className="muted">Aún no se han registrado pagos.</p>}
  </details>
}
