import { useTripAccess } from './TripAccess'
import { useEffect, useId, useState } from 'react'
import { errorMessage } from './api'
import { loadExpenseDetails } from './expenseDetails'
import { formatDate } from './dates'
import DetailToggle from './DetailToggle'
import ExpenseEditor, { ExpenseHistory } from './ExpenseEditor'

const money = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' })

export default function ExpenseRow({ expense, members = [], balances = [], onChanged, onBusy, busy, loadDetails = loadExpenseDetails }) {
  const { actor, isOwner, canRegister } = useTripAccess()
  const canEdit = isOwner || (canRegister && expense.created_by_id === actor?.id)
  const [mode, setMode] = useState(null)
  const [open, setOpen] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const panelId = useId()

  useEffect(() => {
    if (!open) return
    let active = true
    loadDetails(expense.id).then((data) => {
      if (active) setResult(data)
    }).catch((failure) => {
      if (active) setError(errorMessage(failure))
    })
    return () => { active = false }
  }, [open, expense.id, attempt, loadDetails])

  function toggle() {
    setResult(null)
    setError('')
    setOpen((current) => !current)
  }

  return <article className="expense-entry">
    <div className="expense">
      <b>{expense.description}{expense.voided && <small> · Anulado</small>}</b>
      <strong>{money.format(expense.amount)}</strong>
      <DetailToggle open={open} panelId={panelId} label="Reparto" subject={expense.description} disabled={busy} onClick={toggle} />
    </div>
    <div id={panelId} hidden={!open} className="expense-detail">
      {open && <p className="detail-label">Fecha del gasto: {formatDate(expense.expense_date)}</p>}
      {open && !result && !error && <p role="status">Cargando reparto…</p>}
      {error && <div role="alert"><p>{error}</p><button type="button" className="secondary" onClick={() => { setError(''); setAttempt((current) => current + 1) }}>Reintentar</button></div>}
      {result && <>
        <div className="expense-payer"><p>{result.payers?.length > 1 ? "Pagaron" : "Pagó"}</p>{result.payers ? <ul aria-label="Aportaciones de los pagadores">{result.payers.map(p => <li key={p.id}><span>{p.name}</span><strong>{money.format(p.amount)}</strong></li>)}</ul> : <strong>{result.payer}</strong>}</div>
        <p className="detail-label">{expense.custom_shares ? 'Reparto personalizado' : 'Partes iguales'} · MXN</p>
        <ul aria-label="Participantes y su parte del gasto">{result.participants.map((person) => <li key={person.id}><span>{person.name}</span><strong>{money.format(person.amount)}</strong></li>)}</ul>
        {expense.voided && <p>Este gasto no cuenta en el total ni en los balances.</p>}
        {!mode && canEdit && <div className="form-actions">{!expense.voided && <button type="button" className="secondary" disabled={busy} onClick={() => setMode('edit')}>Editar</button>}<button type="button" className="secondary" disabled={busy} onClick={() => setMode(expense.voided ? 'restore' : 'void')}>{expense.voided ? 'Restaurar gasto' : 'Anular gasto'}</button></div>}
        {mode && canEdit && <ExpenseEditor expense={expense} participants={result.participants} members={members} balances={balances} mode={mode} onCancel={() => setMode(null)} onBusy={onBusy} onDone={onChanged} />}
        <ExpenseHistory history={expense.history} />
      </>}
    </div>
  </article>
}
