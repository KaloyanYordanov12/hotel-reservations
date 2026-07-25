import { createContext, useContext } from 'react'

// The context object and its hook live here, apart from the provider component,
// so each file exports one kind of thing (keeps fast refresh happy).
export const AuthContext = createContext(null)

export function useAuth() {
  return useContext(AuthContext)
}
