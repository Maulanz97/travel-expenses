import { useId, useRef, useState } from 'react'
import { Share2 } from 'lucide-react'
import { buildShareSummary } from './summaryText'

export default function ShareSummary({ group, expenses, balances, settlements, busy }) {
  const [text, setText] = useState('')
  const [pending, setPending] = useState(false)
  const [message, setMessage] = useState('')
  const area = useRef(null)
  const lock = useRef(false)
  const id = useId()
  async function send(copy) {
    if (lock.current) return
    lock.current = true; setPending(true); setMessage('')
    try {
      if (copy) {
        await navigator.clipboard.writeText(text)
        setMessage('Resumen copiado. Ya puedes pegarlo donde quieras compartirlo.')
      } else {
        await navigator.share({ title: `Resumen · ${group.name}`, text })
        setMessage('Resumen entregado al menú de compartir.')
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        area.current?.focus(); area.current?.select()
        setMessage('No se pudo completar la acción. Puedes copiar manualmente el texto seleccionado.')
      }
    } finally { lock.current = false; setPending(false) }
  }
  return <section className="share-summary">
    <button type="button" className="secondary share-summary-trigger" disabled={busy || pending} aria-expanded={Boolean(text)} aria-controls={id} onClick={() => { setMessage(''); setText(text ? '' : buildShareSummary({ group, expenses, balances, settlements })) }}><Share2 size={17} aria-hidden="true" />{text ? 'Cerrar resumen para compartir' : 'Compartir resumen'}</button>
    {text && <div id={id} className="share-summary-preview"><label htmlFor={`${id}-text`}>Vista previa del resumen</label><p className="form-help">Incluye nombres e importes. Revisa el contenido antes de compartirlo. No concede acceso al viaje.</p><textarea id={`${id}-text`} ref={area} readOnly value={text} rows={14} /><div className="form-actions">{typeof navigator.share === 'function' && <button className="primary" disabled={busy || pending} onClick={() => send(false)}>Compartir…</button>}<button className="secondary" disabled={busy || pending} onClick={() => send(true)}>Copiar resumen</button><button className="secondary" disabled={busy || pending} onClick={() => { setText(buildShareSummary({ group, expenses, balances, settlements })); setMessage('Vista previa regenerada con los datos cargados.') }}>Regenerar texto</button></div>{message && <p role="status">{message}</p>}</div>}
  </section>
}
