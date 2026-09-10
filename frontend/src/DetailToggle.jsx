import { ReceiptText } from 'lucide-react'

export default function DetailToggle({ open, panelId, label, subject, disabled, onClick }) {
  return <button type="button" className="detail-toggle" disabled={disabled} aria-expanded={open} aria-controls={panelId} aria-label={`${open ? 'Ocultar' : 'Ver'} ${label.toLowerCase()} de ${subject}`} onClick={onClick}>
    <ReceiptText size={18} strokeWidth={2} aria-hidden="true" />
    <span>{label}</span>
  </button>
}
