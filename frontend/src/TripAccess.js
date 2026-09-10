import { createContext, useContext } from 'react'
export const TripAccess = createContext({ actor: null, isOwner: false, canRegister: false })
export const useTripAccess = () => useContext(TripAccess)
