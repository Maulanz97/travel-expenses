import { useState } from 'react'
import { MAX_AMOUNT } from './validation'

export default function SplitFields({ members, initialIds, initialShares, inputName = 'participant' }) {
  const [kind, setKind] = useState(initialShares ? 'custom' : 'equal')
  const [selected, setSelected] = useState(initialIds || members.map((p) => p.user_id))
  return <fieldset><legend>¿Entre quiénes se divide?</legend>
    <input type="hidden" name="splitKind" value={kind} />
    <div className="split-choice" role="group" aria-label="Tipo de reparto">
      <button type="button" aria-pressed={kind === 'equal'} onClick={() => setKind('equal')}>Iguales</button>
      <button type="button" aria-pressed={kind === 'custom'} onClick={() => setKind('custom')}>Personalizado</button>
    </div>
    <p className="form-help">{kind === 'equal' ? 'Se divide entre las personas seleccionadas.' : 'Escribe la parte de cada persona. La suma debe coincidir con el total; puedes asignar cero.'}</p>
    {members.map((p) => <div key={p.user_id} className="split-person"><label><input type="checkbox" name={inputName} value={p.user_id} checked={selected.includes(p.user_id)} onChange={(event) => setSelected(event.target.checked ? [...selected, p.user_id] : selected.filter((id) => id !== p.user_id))} />{p.name}</label>{kind === 'custom' && selected.includes(p.user_id) && <label>Parte de {p.name} (MXN)<input required type="number" inputMode="decimal" name={`share-${p.user_id}`} min="0" max={MAX_AMOUNT} step="0.01" defaultValue={initialShares?.[p.user_id] ?? ''} /></label>}</div>)}
  </fieldset>
}
