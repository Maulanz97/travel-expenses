const money = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' })
const status = (cents) => cents === 0 ? 'Al día' : `${cents > 0 ? 'A favor' : 'Debe'} ${money.format(Math.abs(cents) / 100)}`

export default function PaymentImpact({ impact, name }) {
  const sender = impact[0]
  return <section aria-label="Efecto del pago en los balances">
    <h3>Así quedarían los balances</h3>
    {impact.map((person) => <div key={person.id} className="payment-impact-person"><strong>{name(person.id)}</strong><dl><dt>Ahora</dt><dd>{status(person.before)}</dd><dt>Después del pago</dt><dd>{status(person.after)}</dd></dl></div>)}
    {sender.before < 0 && sender.after > 0 && <p>El pago supera lo que {name(sender.id)} debe en el viaje. Quedará con {money.format(sender.after / 100)} a favor.</p>}
    {sender.before >= 0 && <p>{name(sender.id)} no tiene deuda pendiente en el viaje. Este pago {sender.before > 0 ? 'aumentará su saldo a favor' : 'se registrará como anticipo'}.</p>}
    <p className="form-help">Son balances con el grupo completo, no deudas exclusivamente entre estas dos personas. Previsión con los datos del resumen actual; el total gastado no cambia.</p>
  </section>
}
