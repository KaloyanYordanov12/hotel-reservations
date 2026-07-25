import { Navigate, Route, Routes } from 'react-router-dom'

import { AuthProvider } from './auth/AuthProvider'
import { RequireAuth } from './auth/RequireAuth'
import BookScreen from './screens/BookScreen'
import LoginScreen from './screens/LoginScreen'
import SearchScreen from './screens/SearchScreen'

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginScreen />} />
        <Route element={<RequireAuth />}>
          <Route path="/" element={<SearchScreen />} />
          <Route path="/book" element={<BookScreen />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}

export default App
