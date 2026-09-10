export function validatePublicEnvironment(environment) {
  for (const name of Object.keys(environment)) {
    if (name.startsWith('VITE_') && /SECRET|SERVICE_ROLE|PRIVATE_KEY|LOCAL_DEV_TOKEN/i.test(name) && environment[name]) {
      throw new Error(`La variable ${name} no debe exponerse al navegador. Usa una variable exclusiva del servidor.`)
    }
  }
  const key = environment.VITE_SUPABASE_PUBLISHABLE_KEY
  if (!key) return
  if (key.startsWith('sb_publishable_')) return
  try {
    const pieces = key.split('.')
    if (pieces.length === 3 && JSON.parse(Buffer.from(pieces[1], 'base64url').toString('utf8')).role === 'anon') return
  } catch { /* Reject without echoing the supplied key. */ }
  throw new Error('Supabase: configura únicamente la clave pública Publishable o anon. No uses una clave secreta ni service_role en el frontend.')
}
