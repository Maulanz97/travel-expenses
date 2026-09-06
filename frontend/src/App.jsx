import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from './api'
import './App.css'

const currency = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' })

function App() {
  const [users, setUsers] = useState([])
  const [groups, setGroups] = useState([])
  const [selectedGroup, setSelectedGroup] = useState('')
  const [members, setMembers] = useState([])
  const [expenses, setExpenses] = useState([])
  const [balances, setBalances] = useState([])
  const [settlements, setSettlements] = useState([])
  const [activeTab, setActiveTab] = useState('summary')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const group = useMemo(() => groups.find((item) => String(item.id) === selectedGroup), [groups, selectedGroup])
  const fail = (text) => { setError(text); setMessage('') }
  const loadUsers = useCallback(async () => setUsers(await api.get('/users/')), [])
  const loadGroups = useCallback(async () => {
    const data = await api.get('/groups/')
    setGroups(data)
    setSelectedGroup((current) => current || (data[0] ? String(data[0].id) : ''))
  }, [])
  const loadGroup = useCallback(async (id) => {
    const groupId = Number(id)
    if (!Number.isInteger(groupId) || groupId <= 0) {
      setMembers([]); setExpenses([]); setBalances([]); setSettlements([])
      return
    }
    const [groupMembers, allExpenses, groupBalances, groupSettlements] = await Promise.all([
      api.get(`/group-members/group/${groupId}`), api.get('/expenses/'), api.get(`/groups/${groupId}/balances`), api.get(`/groups/${groupId}/settlements`),
    ])
    setMembers(groupMembers); setExpenses(allExpenses.filter((expense) => expense.group_id === groupId)); setBalances(groupBalances); setSettlements(groupSettlements)
  }, [])
  const refresh = useCallback(async () => {
    try { setLoading(true); setError(''); await Promise.all([loadUsers(), loadGroups()]) }
    catch { fail('No se pudo conectar con la API. Comprueba que el backend esté iniciado.') }
    finally { setLoading(false) }
  }, [loadGroups, loadUsers])
  useEffect(() => { refresh() }, [refresh])
  useEffect(() => { loadGroup(selectedGroup).catch(() => fail('No se pudieron cargar los datos del viaje.')) }, [selectedGroup, loadGroup])
  const reload = () => loadGroup(selectedGroup)

  const submitUser = async (event) => {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form)
    try { await api.post('/users/', { name: data.get('name'), email: data.get('email') }); form.reset(); await loadUsers(); setError(''); setMessage('Viajero agregado.') }
    catch { fail('No se pudo agregar el viajero. El correo debe ser único.') }
  }
  const submitGroup = async (event) => {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form)
    let item
    try {
      item = await api.post('/groups/', {
        name: data.get('groupName'),
        owner_id: Number(data.get('ownerId')),
      })
    } catch {
      fail('Primero agrega y selecciona a la persona que organiza el viaje.')
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
    setMessage('Viaje creado.')
  }
  const submitMember = async (event) => {
    event.preventDefault(); const data = new FormData(event.currentTarget)
    try { await api.post('/group-members/', { user_id: Number(data.get('userId')), group_id: Number(selectedGroup), role: 'member' }); await reload(); setError(''); setMessage('Integrante agregado al viaje.') }
    catch { fail('No se pudo agregar. Quizá esa persona ya pertenece al viaje.') }
  }
  const submitExpense = async (event) => {
    event.preventDefault(); const form = event.currentTarget; const data = new FormData(form)
    const participants = [...form.querySelectorAll('input[name="participant"]:checked')].map((item) => Number(item.value))
    try { await api.post('/expenses/', { description: data.get('description'), amount: Number(data.get('amount')), payer_id: Number(data.get('payerId')), group_id: Number(selectedGroup), participants }); form.reset(); await reload(); setError(''); setMessage('Gasto registrado y dividido.'); setActiveTab('summary') }
    catch { fail('No se pudo guardar. Selecciona pagador y al menos un participante.') }
  }

  return <main className="app-shell">
    <header className="topbar"><div className="brand"><b>✦</b> viaje<span>claro</span></div><button className="quiet-button" onClick={refresh}>↻ Actualizar</button></header>
    <section className="hero"><p className="eyebrow">GASTOS COMPARTIDOS</p><h1>Que los recuerdos pesen,<br /><em>no las cuentas.</em></h1><p>Organiza, divide y liquida los gastos de tu viaje en un solo lugar.</p></section>
    {error && <div className="alert error">{error}</div>}{message && <div className="alert success">✓ {message}</div>}
    <section className="workspace"><aside className="sidebar"><label className="eyebrow">VIAJE ACTIVO</label><select value={selectedGroup} onChange={(event) => setSelectedGroup(event.target.value)}><option value="">Selecciona un viaje</option>{groups.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><nav><button className={activeTab === 'summary' ? 'active' : ''} onClick={() => setActiveTab('summary')}>◫ Resumen</button><button className={activeTab === 'expense' ? 'active' : ''} onClick={() => setActiveTab('expense')}>＋ Registrar gasto</button><button className={activeTab === 'people' ? 'active' : ''} onClick={() => setActiveTab('people')}>◉ Personas</button></nav><small>{group ? `${members.length} personas en este viaje` : 'Crea tu primer viaje'}</small></aside>
      <section className="content">{loading ? <Empty title="Cargando tu viaje…" /> : activeTab === 'summary' ? <Summary group={group} expenses={expenses} balances={balances} settlements={settlements} onAdd={() => setActiveTab('expense')} /> : activeTab === 'expense' ? <ExpenseForm members={members} group={group} submit={submitExpense} /> : <People users={users} members={members} group={group} addUser={submitUser} addGroup={submitGroup} addMember={submitMember} />}</section>
    </section>
  </main>
}

function Empty({ title, children }) { return <div className="empty"><h2>{title}</h2>{children}</div> }
function Summary({ group, expenses, balances, settlements, onAdd }) {
  if (!group) return <Empty title="Comienza un viaje"><p>Ve a Personas para crear viajeros y tu primer viaje.</p></Empty>
  const total = expenses.reduce((sum, item) => sum + Number(item.amount), 0)
  return <><div className="heading"><div><p className="eyebrow">TU VIAJE</p><h2>{group.name}</h2></div><button className="primary" onClick={onAdd}>＋ Registrar gasto</button></div><div className="stats"><Stat label="Total gastado" value={currency.format(total)} /><Stat label="Gastos registrados" value={expenses.length} /><Stat label="Por liquidar" value={settlements.length} /></div><div className="columns"><section className="card"><CardTitle title="Balances" detail="Saldo neto" />{balances.length ? balances.map((item) => <div className="balance" key={item.user_id}><Avatar name={item.name} /><span>{item.name}</span><b className={Number(item.balance) >= 0 ? 'plus' : 'minus'}>{Number(item.balance) >= 0 ? '+' : ''}{currency.format(item.balance)}</b></div>) : <p className="muted">Aún no hay gastos en este viaje.</p>}</section><section className="card"><CardTitle title="Para quedar a mano" detail={`${settlements.length} pagos`} />{settlements.length ? settlements.map((item, index) => <div className="settlement" key={index}><b>{item.from_user}</b> paga a <b>{item.to_user}</b><strong>{currency.format(item.amount)}</strong></div>) : <p className="muted">Todo está equilibrado por ahora.</p>}</section></div><section className="card expenses"><CardTitle title="Últimos gastos" detail={`${expenses.length} registros`} />{expenses.length ? expenses.slice().reverse().map((item) => <div className="expense" key={item.id}><span>▣</span><div><b>{item.description}</b><small>Gasto del viaje</small></div><strong>{currency.format(item.amount)}</strong></div>) : <p className="muted">Registra el primer gasto para comenzar.</p>}</section></>
}
const Stat = ({ label, value }) => <article><span>{label}</span><strong>{value}</strong></article>
const CardTitle = ({ title, detail }) => <div className="card-title"><h3>{title}</h3><span>{detail}</span></div>
const Avatar = ({ name }) => <span className="avatar">{name.slice(0, 1).toUpperCase()}</span>
function ExpenseForm({ members, group, submit }) {
  if (!group) return <Empty title="Selecciona un viaje"><p>Primero crea o elige un viaje en Personas.</p></Empty>
  if (!members.length) return <Empty title="Agrega viajeros"><p>Este viaje necesita al menos una persona.</p></Empty>
  return <form className="form" onSubmit={submit}><div className="heading"><div><p className="eyebrow">NUEVO REGISTRO</p><h2>Registrar gasto</h2></div></div><label>¿Qué pagaron?<input required name="description" placeholder="Ej. Cena en el centro" /></label><label>Monto total<input required name="amount" type="number" min="0.01" step="0.01" placeholder="0.00" /></label><label>¿Quién pagó?<select required name="payerId" defaultValue=""><option value="" disabled>Selecciona una persona</option>{members.map((item) => <option key={item.user_id} value={item.user_id}>{item.name}</option>)}</select></label><fieldset><legend>¿Entre quiénes se divide?</legend><div className="checks">{members.map((item) => <label key={item.user_id}><input type="checkbox" name="participant" value={item.user_id} defaultChecked />{item.name}</label>)}</div></fieldset><button className="primary">Guardar gasto</button></form>
}
function People({ users, members, group, addUser, addGroup, addMember }) { return <div className="people"><section className="card"><p className="eyebrow">1. VIAJEROS</p><h2>Personas</h2><form className="inline" onSubmit={addUser}><input required name="name" placeholder="Nombre" /><input required name="email" type="email" placeholder="correo@ejemplo.com" /><button className="primary">Agregar</button></form><div className="person-list">{users.map((item) => <div key={item.id}><Avatar name={item.name} /><span>{item.name}<small>{item.email}</small></span></div>)}</div></section><section className="card"><p className="eyebrow">2. NUEVO VIAJE</p><h2>Crear viaje</h2><form className="stack" onSubmit={addGroup}><input required name="groupName" placeholder="Ej. Oaxaca 2026" /><select required name="ownerId" defaultValue=""><option value="" disabled>¿Quién lo organiza?</option>{users.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><button className="primary">Crear viaje</button></form></section>{group && <section className="card"><p className="eyebrow">3. INTEGRANTES</p><h2>Invitar al viaje</h2><form className="stack" onSubmit={addMember}><select required name="userId" defaultValue=""><option value="" disabled>Selecciona una persona</option>{users.filter((user) => !members.some((member) => member.user_id === user.id)).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><button className="secondary">Agregar al viaje</button></form><div className="chips">{members.map((item) => <span key={item.user_id}>{item.name}{item.role === 'owner' && ' · organiza'}</span>)}</div></section>}</div> }
export default App
