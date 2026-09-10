import { useEffect, useState } from 'react'
import { authClient } from './authClient'
import { api, errorMessage, setTokenProvider } from './api'
import { setPendingExpenseOwner } from './pendingExpense'
import './App.css'
import { localDevelopment } from './localDevelopment'

if (authClient && !localDevelopment) setTokenProvider(async () => {
  const { data, error } = await authClient.auth.getSession()
  if (error || !data.session) throw Object.assign(new Error('Sign in required'), { status: 401 })
  return data.session.access_token
})

export default function AuthGate({ children }) {
  return localDevelopment ? <LocalGate>{children}</LocalGate> : <SupabaseGate>{children}</SupabaseGate>
}

function LocalGate({ children }) {
  const [profile, setProfile] = useState(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    setPendingExpenseOwner('')
    api.get('/auth/me').then(user => {
      if (!user.local_development) throw new Error('Local mode not enabled')
      if (active) setProfile(user)
    }).catch(() => { if (active) setError('No se pudo conectar el modo local. Inicia la app con el lanzador de desarrollo.') })
    return () => { active = false }
  }, [attempt])
  if (profile) return children(profile)
  return <main className="auth-shell"><h1>viajeclaro</h1><p role={error ? 'alert' : 'status'}>{error || 'Abriendo la app local…'}</p>{error && <button className="secondary" onClick={() => setAttempt(n => n + 1)}>Reintentar</button>}</main>
}

function SupabaseGate({ children }) {
  const [session, setSession] = useState(null)
  const [ready, setReady] = useState(false)
  const [actor, setActor] = useState(null)
  const [mode, setMode] = useState(new URLSearchParams(location.search).has('recovery') ? 'password' : 'login')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const sessionId = session?.user.id
  useEffect(() => {
    if (!authClient) return
    const { data } = authClient.auth.onAuthStateChange((event, next) => {
      setPendingExpenseOwner(next?.user.id || '')
      setSession(next)
      setReady(true)
      if (event === 'PASSWORD_RECOVERY') setMode('password')
      if (!next) setActor(null)
    })
    authClient.auth.getSession().then(({ data, error }) => {
      if (error) setError('No se pudo recuperar la sesión. Vuelve a entrar.')
      setPendingExpenseOwner(data.session?.user.id || '')
      setSession(data.session); setReady(true)
    })
    return () => data.subscription.unsubscribe()
  }, [])
  useEffect(() => {
    let active = true
    if (sessionId && mode !== 'password') {
      api.get('/auth/me').then(user => { if (active) { setActor({ profile: user, subject: sessionId }); setError('') } }).catch(failure => { if (active) { setActor(null); setError(errorMessage(failure)) } })
    }
    return () => { active = false }
  }, [sessionId, mode, attempt])

  if (!authClient) return <main className="auth-shell"><h1>viajeclaro</h1><p>El acceso está pendiente de configuración. Conecta el proyecto de Supabase para habilitar Google y correo.</p></main>
  if (!ready) return <main className="auth-shell"><p role="status">Comprobando sesión…</p></main>
  if (session && actor?.subject === sessionId && mode !== 'password') return children(actor.profile)

  const redirect = location.origin + location.pathname
  async function submit(event) {
    event.preventDefault()
    if (busy) return
    const data = new FormData(event.currentTarget)
    setBusy(true); setError(''); setMessage('')
    try {
      let result
      const email = String(data.get('email') || '').trim()
      const password = String(data.get('password') || '')
      if (mode === 'signup') result = await authClient.auth.signUp({ email, password, options: { emailRedirectTo: redirect } })
      else if (mode === 'reset') result = await authClient.auth.resetPasswordForEmail(email, { redirectTo: redirect + '?recovery=1' })
      else if (mode === 'password') result = await authClient.auth.updateUser({ password })
      else result = await authClient.auth.signInWithPassword({ email, password })
      if (result.error) throw result.error
      if (mode === 'signup') setMessage('Revisa tu correo para confirmar la cuenta. Si ya tienes una, inicia sesión o recupera tu contraseña.')
      if (mode === 'reset') setMessage('Si el correo corresponde a una cuenta, recibirás un enlace para recuperar el acceso.')
      if (mode === 'password') { history.replaceState(null, '', location.pathname); setMode('login'); setMessage('Contraseña actualizada.') }
    } catch { setError(mode === 'login' ? 'No se pudo iniciar sesión. Revisa tu correo, contraseña y la confirmación de tu cuenta.' : 'No se pudo completar la solicitud. Comprueba la conexión y vuelve a intentarlo.') }
    finally { setBusy(false) }
  }
  async function google() {
    setBusy(true); setError('')
    try {
      const { error } = await authClient.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: redirect } })
      if (error) throw error
    } catch { setError('No se pudo abrir Google. Vuelve a intentarlo.') }
    finally { setBusy(false) }
  }
  return <main className="auth-shell"><div className="brand">viaje<span>claro</span></div>
    <h1>{mode === 'signup' ? 'Crea tu cuenta' : mode === 'reset' ? 'Recupera tu acceso' : mode === 'password' ? 'Elige una nueva contraseña' : 'Entra a tus viajes'}</h1>
    {error && <p className="alert error" role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    {session && mode !== 'password' ? <><p>{error ? 'No se pudieron cargar tus viajes.' : 'Cargando tu cuenta…'}</p><button className="secondary" onClick={() => setAttempt(n => n + 1)}>Reintentar</button><button className="secondary" onClick={() => authClient.auth.signOut()}>Cerrar sesión</button></> : <>
      {['login', 'signup'].includes(mode) && <button type="button" className="secondary" disabled={busy} onClick={google}>Continuar con Google</button>}
      <form className="form" onSubmit={submit}><fieldset className="pending-fields" disabled={busy}>
        {mode !== 'password' && <label>Correo<input required type="email" name="email" autoComplete="email" /></label>}
        {mode !== 'reset' && <label>Contraseña<input required type="password" name="password" minLength={mode === 'login' ? 1 : 8} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} /></label>}
        <button className="primary">{busy ? 'Espera…' : mode === 'signup' ? 'Crear cuenta' : mode === 'reset' ? 'Enviar enlace' : mode === 'password' ? 'Guardar contraseña' : 'Entrar con correo'}</button>
      </fieldset></form>
      {mode !== 'password' && <div className="form-actions"><button className="quiet-button" disabled={busy} onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(''); setMessage('') }}>{mode === 'login' ? 'Crear una cuenta' : 'Volver a iniciar sesión'}</button>{mode === 'login' && <button className="quiet-button" disabled={busy} onClick={() => setMode('reset')}>Olvidé mi contraseña</button>}</div>}
    </>}
  </main>
}
