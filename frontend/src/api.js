import { validationMessage } from './validation.js'
const API_URL = import.meta.env?.VITE_API_URL || '/api'
let tokenProvider = async () => null
export function setTokenProvider(provider) { tokenProvider = provider }

export function errorMessage(error) {
  if ([400, 409, 422].includes(error.status) && error.validation) return error.validation
  if (error.status === 401) return 'Tu sesión no está disponible. Vuelve a entrar y revisa tus datos.'
  if (error.status === 403) return 'No tienes permiso para realizar esta operación.'
  if (error.status === 404) return 'El registro ya no está disponible. Actualiza los datos.'
  if (error.status === 429) return 'Hay demasiadas solicitudes. Espera un momento antes de continuar.'
  if (error.status === 400 || error.status === 409 || error.status === 422) return 'No se aceptaron los datos. Revisa los campos y actualiza la lista de personas o viajes.'
  if (error.uncertain) return 'No pudimos confirmar el resultado. Revisa el resumen antes de volver a enviar para evitar duplicados.'
  return 'No se pudieron cargar los datos. Comprueba tu conexión y vuelve a intentar.'
}

async function request(path, options = {}) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 20000)
  try {
    const token = await tokenProvider()
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options.headers, ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      signal: options.signal || controller.signal,
    })
    const data = await response.json()
    if (!response.ok || (data && !Array.isArray(data) && data.message)) {
      throw Object.assign(new Error('Solicitud rechazada'), {
        status: response.ok ? 422 : response.status,
        validation: validationMessage(data?.detail || data?.message),
        uncertain: !response.ok && response.status >= 500 && ['POST', 'PUT'].includes(options.method),
      })
    }
    if (['POST', 'PUT'].includes(options.method) && (!Number.isInteger(Number(data?.id)) || Number(data?.id) <= 0)) {
      throw Object.assign(new Error('Respuesta incompleta'), { uncertain: true })
    }
    return data
  } catch (error) {
    if (!error.status && ['POST', 'PUT'].includes(options.method)) error.uncertain = true
    throw error
  } finally {
    clearTimeout(timeout)
  }
}

export const api = {
  put: (path, body) => request(path, { method: 'PUT', body: JSON.stringify(body) }),
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
}
