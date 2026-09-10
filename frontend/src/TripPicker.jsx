import { useEffect, useId, useRef, useState } from 'react'
import { Check, ChevronDown, Luggage } from 'lucide-react'

export default function TripPicker({ groups, value, onChange, disabled }) {
  const [open, setOpen] = useState(false)
  const root = useRef(null)
  const trigger = useRef(null)
  const panelId = useId()
  const selected = groups.find((group) => String(group.id) === value)
  useEffect(() => {
    if (!open) return
    const buttons = root.current.querySelectorAll('.trip-picker-option')
    const index = groups.findIndex((group) => String(group.id) === value)
    buttons[Math.max(index, 0)]?.focus()
    const outside = (event) => { if (!root.current?.contains(event.target)) setOpen(false) }
    document.addEventListener('pointerdown', outside)
    return () => document.removeEventListener('pointerdown', outside)
  }, [open, groups, value])
  function keyDown(event) {
    if (event.key === 'Escape') { setOpen(false); trigger.current.focus(); event.preventDefault() }
    if (open && ['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
      const buttons = [...root.current.querySelectorAll('.trip-picker-option')]
      if (!buttons.length) return
      const index = buttons.indexOf(document.activeElement)
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (index + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length
      buttons[next].focus(); event.preventDefault()
    } else if (!open && ['ArrowDown', 'ArrowUp'].includes(event.key)) { setOpen(true); event.preventDefault() }
  }
  return <div className="trip-picker" ref={root} onKeyDown={keyDown} onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false) }}>
    <span className="nav-label" id={`${panelId}-label`}>Viaje activo</span>
    <button type="button" className="trip-picker-trigger" ref={trigger} disabled={disabled || !groups.length} aria-labelledby={`${panelId}-label ${panelId}-name`} aria-expanded={open} aria-controls={panelId} onClick={() => setOpen(!open)}>
      <Luggage size={18} aria-hidden="true" /><span id={`${panelId}-name`}>{selected?.name || (groups.length ? 'Selecciona un viaje' : 'Sin viajes todavía')}</span><ChevronDown size={16} aria-hidden="true" />
    </button>
    {open && <div id={panelId} className="trip-picker-list" role="group" aria-label="Viajes disponibles">{groups.map((group) => <button type="button" className="trip-picker-option" key={group.id} aria-pressed={String(group.id) === value} onClick={() => { onChange(String(group.id)); setOpen(false); trigger.current.focus() }}><span>{group.name}{Number.isInteger(group.member_count) && <small>{group.member_count} {group.member_count === 1 ? 'integrante' : 'integrantes'}</small>}</span>{String(group.id) === value && <Check size={18} aria-hidden="true" />}</button>)}</div>}
  </div>
}
