const namespace = `viajeclaro:pending-expense:e579a0:${import.meta.env?.VITE_API_URL || '/api'}:`
let owner = ''
export function setPendingExpenseOwner(value) { owner = value }
const key = (groupId) => namespace + (owner ? `${owner}:` : '') + groupId

export function loadPendingExpense(groupId, storage = localStorage) {
  const raw = storage.getItem(key(groupId))
  if (!raw) return null
  const value = JSON.parse(raw)
  if (!value?.request_id || value.group_id !== groupId || !Array.isArray(value.shares) || !Array.isArray(value.participants)) {
    throw new Error('No se pudo leer el gasto pendiente. Conserva los datos del navegador y vuelve a intentarlo.')
  }
  return value
}

export function savePendingExpense(review, storage = localStorage) {
  const existing = loadPendingExpense(review.group_id, storage)
  if (existing && existing.request_id !== review.request_id) {
    throw new Error('Hay otro gasto pendiente en este viaje. Recarga para recuperarlo antes de registrar uno nuevo.')
  }
  storage.setItem(key(review.group_id), JSON.stringify(review))
}

export function clearPendingExpense(review, storage = localStorage) {
  if (loadPendingExpense(review.group_id, storage)?.request_id === review.request_id) {
    storage.removeItem(key(review.group_id))
  }
}
