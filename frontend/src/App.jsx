import { TripAccess, useTripAccess } from './TripAccess'
import { authClient } from './authClient'
import MemberPermissions from './MemberPermissions'
import TripPicker from './TripPicker'
import { Users } from 'lucide-react'
import RegisterPaymentButton from './RegisterPaymentButton'
import PeopleDirectory from './PeopleDirectory'
import NewMemberForm from './NewMemberForm'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, errorMessage } from './api'
import './App.css'
import ExpenseForm from './ExpenseForm'
import ExpenseRow from './ExpenseRow'
import PaymentForm from './PaymentForm'
import PaymentHistory from './PaymentHistory'
import BalanceRow from './BalanceRow'

const currency = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' })

function App({ actor }) {
  const [users, setUsers] = useState([])
  const [groups, setGroups] = useState([])
  const [selectedGroup, setSelectedGroup] = useState('')
  const [members, setMembers] = useState([])
  const [expenses, setExpenses] = useState([])
  const [balances, setBalances] = useState([])
  const [settlements, setSettlements] = useState([])
  const [payments, setPayments] = useState([])
  const [paymentSuggestion, setPaymentSuggestion] = useState(null)
  const [activeTab, setActiveTab] = useState('summary')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [mutationPending, setMutationPending] = useState(false)

  const selectedGroupRef = useRef(selectedGroup)
  useEffect(() => { selectedGroupRef.current = selectedGroup }, [selectedGroup])
  const groupRequest = useRef(0)
  const [groupLoading, setGroupLoading] = useState(false)
  const [groupError, setGroupError] = useState('')
  const group = useMemo(() => groups.find((item) => String(item.id) === selectedGroup), [groups, selectedGroup])
  const currentMember = members.find(member => member.user_id === actor.id)
  const isOwner = Boolean(actor.local_development) || currentMember?.role === 'owner'
  const canRegister = isOwner || Boolean(currentMember?.can_register_expenses)
  const fail = (text) => { setError(text); setMessage('') }
  const loadUsers = useCallback(async () => setUsers(await api.get('/users/')), [])
  const loadGroups = useCallback(async () => {
    const data = await api.get('/groups/')
    setGroups(data)
    setSelectedGroup((current) => current || (data[0] ? String(data[0].id) : ''))
  }, [])
  const loadGroup = useCallback(async (id) => {
    const request = ++groupRequest.current
    setGroupLoading(true); setGroupError('')
    const groupId = Number(id)
    if (!Number.isInteger(groupId) || groupId <= 0) {
      setMembers([]); setExpenses([]); setBalances([]); setSettlements([]); setPayments([])
      setGroupLoading(false)
      return
    }
    try {
    const [groupMembers, allExpenses, groupBalances, groupSettlements, groupPayments] = await Promise.all([
      api.get(`/group-members/group/${groupId}`), api.get('/expenses/'), api.get(`/groups/${groupId}/balances`), api.get(`/groups/${groupId}/settlements`), api.get(`/payments/group/${groupId}`),
    ])
    if (request !== groupRequest.current) return
    setGroups((current) => current.map((item) => item.id === groupId ? { ...item, member_count: groupMembers.length } : item)); setMembers(groupMembers); setExpenses(allExpenses.filter((expense) => expense.group_id === groupId)); setBalances(groupBalances); setSettlements(groupSettlements); setPayments(groupPayments)
    } catch (failure) {
      if (request === groupRequest.current) setGroupError(errorMessage(failure))
    } finally {
      if (request === groupRequest.current) setGroupLoading(false)
    }
  }, [])
  const refresh = useCallback(async () => {
    try { setLoading(true); setError(''); await Promise.all([loadUsers(), loadGroups(), loadGroup(selectedGroupRef.current)]) }
    catch (failure) { fail(errorMessage(failure)) }
    finally { setLoading(false) }
  }, [loadGroups, loadUsers, loadGroup])
  useEffect(() => { void Promise.resolve().then(refresh) }, [refresh])
  useEffect(() => { void Promise.resolve().then(() => loadGroup(selectedGroup)) }, [selectedGroup, loadGroup])
  const reload = () => loadGroup(selectedGroup)

  const submitGroup = async (event) => {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form)
    let item
    try {
      item = await api.post('/groups/', {
        name: String(data.get('groupName')).trim(),
        ...(actor.id ? { owner_id: actor.id } : { organizer: { name: actor.name } }),
      })
    } catch (failure) {
      fail(errorMessage(failure))
      return
    }

    const groupId = Number(item.id)
    if (!Number.isInteger(groupId) || groupId <= 0) {
      fail('El servidor creó el viaje, pero no devolvió un identificador válido.')
      return
    }

    form.reset()
    setGroups((current) => current.some((group) => group.id === groupId) ? current : [...current, item])
    setSelectedGroup(String(groupId))
    setError('')
    setMessage('Viaje creado. Agrega a tus acompañantes.'); setActiveTab('members'); try { await loadUsers() } catch (failure) { fail(errorMessage(failure)) }
  }
  const submitMember = async (event) => {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form)
    try { await api.post('/group-members/', { user_id: Number(data.get('userId')), group_id: Number(selectedGroup), role: 'member' }); form.reset(); await reload(); setError(''); setMessage('Integrante agregado al viaje.') }
    catch (failure) { fail(errorMessage(failure)) }
  }
  const expenseSaved = async () => {
    setError(''); setMessage('Gasto guardado.'); setActiveTab('summary')
    await reload()
  }

  const startPayment = (suggestion = null) => { setPaymentSuggestion(suggestion); setActiveTab('payment') }
  const paymentSaved = async () => { setError(''); setMessage('Pago registrado.'); setActiveTab('summary'); await reload() }

  return <TripAccess.Provider value={{ actor, isOwner, canRegister }}><main className="app-shell"><a className="skip-link" href="#contenido">Ir al contenido</a>
    <header className="topbar"><div className="brand">viaje<span>claro</span></div><button className="quiet-button" disabled={loading || groupLoading || mutationPending} onClick={refresh}>Actualizar</button>{actor.local_development ? <small>Modo local · sin iniciar sesión</small> : <button className="quiet-button" disabled={mutationPending} onClick={async () => { const { error } = await authClient.auth.signOut(); if (error) fail("No se pudo cerrar la sesión. Inténtalo de nuevo.") }}>Cerrar sesión</button>}</header>
    <section className="hero"><h1>Menos tiempo calculando, <span>más tiempo compartiendo.</span></h1><p>Divide los gastos, <span>multiplica los momentos.</span></p></section>
    {error && <div className="alert error" role="alert">{error}</div>}{message && <div className="alert success" role="status">✓ {message}</div>}
    <section className="workspace"><aside className="sidebar" inert={mutationPending}><TripPicker groups={groups} value={selectedGroup} onChange={setSelectedGroup} disabled={loading || mutationPending} /><nav><button aria-current={activeTab === 'summary' ? 'page' : undefined} className={activeTab === 'summary' ? 'active' : ''} onClick={() => setActiveTab('summary')}>Resumen</button><button disabled={!canRegister} aria-current={activeTab === 'expense' ? 'page' : undefined} className={activeTab === 'expense' ? 'active' : ''} onClick={() => setActiveTab('expense')}>Registrar gasto</button></nav><div className="admin-nav"><p className="nav-label">Administrar</p><nav><button aria-current={activeTab === 'trips' ? 'page' : undefined} className={activeTab === 'trips' ? 'active' : ''} onClick={() => setActiveTab('trips')}>Viajes</button><button aria-current={activeTab === 'members' ? 'page' : undefined} className={activeTab === 'members' ? 'active' : ''} onClick={() => setActiveTab('members')}>Integrantes</button></nav></div><small>{group ? `${members.length} ${members.length === 1 ? 'persona' : 'personas'} en este viaje` : 'Crea tu primer viaje'}</small></aside>
      <section id="contenido" tabIndex={-1} className="content">{loading ? <Empty title="Cargando tu viaje…" /> : groupLoading && ['summary', 'expense', 'members', 'payment'].includes(activeTab) ? <Empty title="Cargando datos del viaje…" /> : groupError && ['summary', 'expense', 'members', 'payment'].includes(activeTab) ? <div role="alert"><p>{groupError}</p><button className="secondary" onClick={reload}>Reintentar</button></div> : activeTab === 'summary' ? <Summary members={members} payments={payments} onPay={startPayment} onPaymentsChanged={reload} onBusy={setMutationPending} busy={mutationPending} group={group} expenses={expenses} balances={balances} settlements={settlements} onAdd={() => setActiveTab('expense')} onSetup={() => setActiveTab('trips')} /> : activeTab === 'payment' && !isOwner ? <Empty title="Los pagos los administra quien organiza" /> : activeTab === 'expense' && !canRegister ? <Empty title="No tienes permiso para registrar gastos" /> : activeTab === 'payment' ? <PaymentForm balances={balances} key={selectedGroup} group={group} members={members} suggestion={paymentSuggestion} onSaved={paymentSaved} onCancel={() => setActiveTab('summary')} onBusy={setMutationPending} /> : activeTab === 'expense' ? <ExpenseForm key={selectedGroup} members={members} group={group} onSaved={expenseSaved} onBusy={setMutationPending} onNavigate={setActiveTab} /> : activeTab === 'people' && !isOwner ? <Empty title="Solo quien organiza puede administrar personas" /> : activeTab === 'people' ? <PeopleDirectory users={users} onBusy={setMutationPending} onBack={() => setActiveTab('members')} onSaved={(person) => { setUsers((current) => current.map((item) => item.id === person.id ? person : item)); setMembers((current) => current.map((item) => item.user_id === person.id ? { ...item, name: person.name, email: person.email } : item)) }} /> : activeTab === 'trips' ? <TripsPanel users={users} groups={groups} selectedGroup={selectedGroup} addGroup={submitGroup} selectGroup={setSelectedGroup} /> : <MembersPanel onChanged={reload} busy={mutationPending} onDirectory={() => setActiveTab('people')} key={selectedGroup} onBusy={setMutationPending} onAdded={async (person) => { setUsers((current) => [...current.filter((item) => item.id !== person.id), person]); setError(''); setMessage('Persona creada y agregada al viaje.'); await reload() }} users={users} members={members} group={group} addMember={submitMember} onGoTrips={() => setActiveTab('trips')} />}</section>
    </section>
  </main></TripAccess.Provider>
}

function Empty({ title, children }) { return <div className="empty"><h2>{title}</h2>{children}</div> }
export function Summary({ members = [], group, expenses, balances, settlements, onAdd, onSetup, payments = [], onPay, onPaymentsChanged, onBusy, busy }) {
  const { canRegister, isOwner } = useTripAccess()
  if (!group) return <Empty title="Comienza un viaje"><p>Crea un viaje y después agrega a tus acompañantes.</p><button className="primary" onClick={onSetup}>Preparar mi viaje</button></Empty>
  const total = expenses.filter((item) => !item.voided).reduce((sum, item) => sum + Number(item.amount), 0)
  return <>
    <div className="heading trip-summary-heading"><div><h2>{group.name}</h2><p className="trip-summary-members"><Users size={16} aria-hidden="true" />{members.length} {members.length === 1 ? 'integrante' : 'integrantes'}</p></div><p className="summary-total">Total gastado · MXN<strong>{currency.format(total)}</strong></p><div className="summary-actions"><button className="primary" disabled={busy || !canRegister} onClick={onAdd}>Registrar gasto</button><RegisterPaymentButton disabled={busy || !isOwner} onClick={() => onPay()} /></div></div>
    <div className="columns">
      <section className="card payments"><CardTitle title="Para quedar a mano" detail={`${settlements.length} ${settlements.length === 1 ? 'pago sugerido' : 'pagos sugeridos'}`} />
        {settlements.length ? settlements.map((item, index) => <div className="settlement" key={index}><span><b>{item.from_user}</b> paga a <b>{item.to_user}</b></span><strong>{currency.format(item.amount)}</strong><RegisterPaymentButton disabled={busy} onClick={() => onPay(item)} from={item.from_user} to={item.to_user} /></div>) : <p className="muted">{expenses.length || payments.length ? 'No hay pagos pendientes entre integrantes.' : 'Los pagos sugeridos aparecerán al registrar gastos.'}</p>}
      </section>
      <section className="card"><CardTitle title="Balances" />
        {balances.length ? balances.map((item) => <BalanceRow key={item.user_id} item={item} />) : <p className="muted">Aún no hay gastos en este viaje.</p>}
      </section>
    </div>
    <section className="card expenses"><CardTitle title="Gastos registrados" detail={`${expenses.length} ${expenses.length === 1 ? 'gasto' : 'gastos'}`} />
      {expenses.length ? expenses.slice().reverse().map((item) => <ExpenseRow key={item.id} expense={item} members={members} balances={balances} onChanged={onPaymentsChanged} onBusy={onBusy} busy={busy} />) : <p className="muted">Registra el primer gasto para comenzar.</p>}
    </section>
    <PaymentHistory payments={payments} onChanged={onPaymentsChanged} onBusy={onBusy} />
  </>
}
const CardTitle = ({ title, detail }) => <div className="card-title"><h3>{title}</h3>{detail && <span>{detail}</span>}</div>
const Avatar = ({ name = '' }) => <span className="avatar">{(Array.from(name)[0] || '').toUpperCase()}</span>
function TripsPanel({ groups, selectedGroup, addGroup, selectGroup }) { const { actor } = useTripAccess(); return <div className="management"><div className="heading"><div><h2>Crear y seleccionar viaje</h2></div></div><section className="card"><CardTitle title="Nuevo viaje" detail="Elige quién lo organiza" /><PendingForm className="stack" onSubmit={addGroup}><label>Nombre del viaje<input required name="groupName" pattern=".*\S.*" maxLength={150} placeholder="Ej. Oaxaca 2026" /></label><p>Organiza: {actor.name}</p><button className="primary">Crear viaje</button></PendingForm></section><section className="card"><CardTitle title="Viajes disponibles" detail={`${groups.length} ${groups.length === 1 ? 'viaje' : 'viajes'}`} /><div className="directory">{groups.length ? groups.map((item) => <button type="button" className={`trip-row ${String(item.id) === selectedGroup ? 'selected' : ''}`} key={item.id} onClick={() => selectGroup(String(item.id))}><span><b>{item.name}</b><small>{String(item.id) === selectedGroup ? 'Viaje activo' : 'Seleccionar este viaje'}</small></span>{String(item.id) === selectedGroup && <em>Activo</em>}</button>) : <p className="muted">Aún no has creado viajes.</p>}</div></section></div> }
function MemberManagement({ busy, onDirectory, onAdded, onBusy, users, members, group, addMember, onGoTrips }) { const [adding, setAdding] = useState(false); const [kind, setKind] = useState('new'); if (!group) return <Empty title="Selecciona un viaje"><p>Elige o crea un viaje antes de administrar sus integrantes.</p><button className="secondary" onClick={onGoTrips}>Ir a Viajes</button></Empty>; const availableUsers = users.filter((user) => !members.some((member) => member.user_id === user.id)); return <div className="management"><div className="heading"><div><h2>{group.name}</h2></div></div><button className="primary" disabled={busy} aria-expanded={adding} onClick={() => setAdding(!adding)}>{adding ? 'Cerrar formulario' : 'Agregar persona'}</button>{adding && <><label>Agregar<select disabled={busy} value={kind} onChange={(event) => setKind(event.target.value)}><option value="new">Persona nueva</option><option value="existing">Persona guardada</option></select></label>{kind === 'new' ? <NewMemberForm group={group} onAdded={onAdded} onBusy={onBusy} /> : <section className="card"><CardTitle title="Agregar persona existente" detail="Selecciona a alguien que ya registraste" />{availableUsers.length ? <PendingForm className="stack" onSubmit={addMember}><select aria-label="Persona que se agregará al viaje" required name="userId" defaultValue=""><option value="" disabled>Selecciona una persona</option>{availableUsers.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><button className="primary">Agregar al viaje</button></PendingForm> : <p className="muted">Todas las personas registradas ya pertenecen a este viaje.</p>}</section>}</>}<button className="expense-toggle" disabled={busy} onClick={onDirectory}>Administrar personas guardadas</button><section className="card"><CardTitle title="Integrantes del viaje" detail={`${members.length} ${members.length === 1 ? 'persona' : 'personas'}`} /><div className="person-list">{members.map((item) => <div key={item.user_id}><Avatar name={item.name} /><span>{item.name}{item.email && <small>{item.email}</small>}</span><em className="role">{item.role === 'owner' ? 'Organiza' : 'Integrante'}</em></div>)}</div></section></div> }
export default App

function PendingForm({ onSubmit, children, className }) {
  const lock = useRef(false)
  const [pending, setPending] = useState(false)
  return <form className={className} aria-busy={pending} onSubmit={async (event) => {
    event.preventDefault()
    if (lock.current) return
    lock.current = true; setPending(true)
    try { await onSubmit(event) } finally { lock.current = false; setPending(false) }
  }}><fieldset className="pending-fields" disabled={pending}>{children}</fieldset>{pending && <p role="status">Guardando…</p>}</form>
}

function MembersPanel(props) {
  const { isOwner, actor } = useTripAccess()
  if (!props.group) return <Empty title="Selecciona un viaje" />
  if (!isOwner) return <section className="card"><h2>Integrantes</h2>{props.members.map(p => <p key={p.user_id}>{p.name} · {p.role === 'owner' ? 'Organiza' : 'Integrante'}</p>)}<p>Los permisos los administra quien organiza.</p></section>
  return <><MemberManagement {...props} />{!actor.local_development && <MemberPermissions members={props.members} groupId={props.group.id} onChanged={props.onChanged} onBusy={props.onBusy} />}</>
}
