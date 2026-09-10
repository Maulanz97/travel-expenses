import { HandCoins } from 'lucide-react'

export default function RegisterPaymentButton({ disabled, onClick, from, to }) {
  return <button type="button" className="register-payment-button" disabled={disabled} onClick={onClick} aria-label={from && to ? `Registrar pago de ${from} a ${to}` : undefined}>
    <HandCoins size={18} strokeWidth={2} aria-hidden="true" />
    <span>Registrar pago</span>
  </button>
}
