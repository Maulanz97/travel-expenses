import { useState } from 'react'
import { Plus, X } from 'lucide-react'
import { MAX_AMOUNT } from './validation'
import { contributions } from './payers'

export default function PayerFields({ members, amount, initial }) {
  const [rows, setRows] = useState(() => initial ? contributions(initial).map(p => ({ id: String(p.id), amount: String(p.amount) })) : [{ id: '', amount: '' }])
  const multiple = rows.length > 1
  const update = (index, field, value) => setRows(rows.map((row, i) => i === index ? { ...row, [field]: value } : row))
  const difference = Math.round(Number(amount || 0) * 100) - rows.reduce((sum, row) => sum + Math.round(Number(row.amount || 0) * 100), 0)
  return <div className="payer-fields">
    {rows.map((row, index) => <div className="payer-input-row" key={index}>
      <label><span className={multiple ? '' : 'sr-only'}>{multiple ? `Pagador ${index + 1}` : 'Quién pagó'}</span><select required name="expensePayer" value={row.id} onChange={e => update(index, 'id', e.target.value)}><option value="" disabled>Selecciona una persona</option>{members.map(p => <option key={p.user_id} value={p.user_id} disabled={rows.some((other, i) => i !== index && other.id === String(p.user_id))}>{p.name}</option>)}</select></label>
      {multiple && <><label>Aportó (MXN)<input required name="payerAmount" type="number" min="0.01" max={MAX_AMOUNT} step="0.01" inputMode="decimal" value={row.amount} onChange={e => update(index, 'amount', e.target.value)} /></label><button type="button" className="secondary payer-remove" aria-label={`Quitar pagador ${index + 1}`} onClick={() => setRows(rows.filter((_, i) => i !== index))}><X size={18} aria-hidden="true" /></button></>}
    </div>)}
    {rows[0].id && rows.length < members.length && <button type="button" className="secondary payer-add" disabled={rows.some(row => !row.id)} onClick={() => setRows([...rows.map(row => !multiple ? { ...row, amount: '' } : row), { id: '', amount: '' }])}><Plus size={16} aria-hidden="true" />Agregar otro pagador</button>}
    {multiple && <p className="form-help" role="status">{rows.some(row => !row.id || !row.amount || Number(row.amount) <= 0) ? 'Completa cada pagador y su aportación.' : difference === 0 ? 'Las aportaciones coinciden con el total.' : `${difference > 0 ? 'Faltan por asignar' : 'Sobran'} $${(Math.abs(difference) / 100).toFixed(2)}.`}</p>}
  </div>
}
