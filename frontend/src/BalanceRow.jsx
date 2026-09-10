import { useId, useState } from 'react'
import DetailToggle from './DetailToggle'
import { formatDate } from './dates'

const money = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' })
const categories = [
  ['expenses_paid', 'Gastos que pagó', '+'],
  ['expense_share', 'Su parte de los gastos', '−'],
  ['payments_sent', 'Pagos enviados a integrantes', '+'],
  ['payments_received', 'Pagos recibidos de integrantes', '−'],
]

export default function BalanceRow({ item }) {
  const [open, setOpen] = useState(false)
  const panelId = useId()
  const amount = Number(item.balance)
  const label = amount > 0 ? 'Recibe' : amount < 0 ? 'Debe' : 'Al día'
  const parts = item.breakdown
  return <article className="balance-entry">
    <div className="balance">
      <span>{item.name}</span>
      <b className={amount >= 0 ? 'plus' : 'minus'}><small>{label}</small>{money.format(Math.abs(amount))}</b>
      <DetailToggle open={open} panelId={panelId} label="Desglose" subject={item.name} onClick={() => setOpen(!open)} />
    </div>
    <div id={panelId} hidden={!open} className="expense-detail balance-detail">
      {parts ? <>
        <p>Así se calcula el balance de <strong>{item.name}</strong>:</p>
        <dl>
          {categories.map(([key, title, sign]) => <div key={key}>
            <dt>{title}</dt><dd>{sign} {money.format(parts[key])}</dd>
            <dd className="balance-movements"><details>
              <summary aria-label={`Ver movimientos: ${title.toLowerCase()} de ${item.name}`}>Ver movimientos</summary>
              {item.movements?.[key] ? item.movements[key].length ? <ul aria-label={title}>{item.movements[key].map(movement => <li key={movement.id}>
                <span>{movement.description}<small>{formatDate(movement.date)}</small></span>
                <strong>{sign} {money.format(movement.amount)}</strong>
              </li>)}</ul> : <p>No hay movimientos en esta categoría.</p> : <p>Los movimientos no están disponibles. Actualiza los datos e inténtalo de nuevo.</p>}
            </details></dd>
          </div>)}
          <div className="balance-result"><dt>Balance actual · {label}</dt><dd>{money.format(Math.abs(amount))}</dd></div>
        </dl>
        <p className="detail-label">Un resultado positivo significa que recibe dinero; uno negativo, que debe. Los gastos y pagos anulados no se incluyen.</p>
      </> : <p role="status">El desglose no está disponible. Actualiza los datos e inténtalo de nuevo.</p>}
    </div>
  </article>
}
