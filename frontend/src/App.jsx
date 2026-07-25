import { Navigate, Route, Routes } from 'react-router-dom'

import { AuthProvider } from './auth/AuthProvider'
import { RequireAuth } from './auth/RequireAuth'
import Home from './screens/Home'
import LoginScreen from './screens/LoginScreen'

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginScreen />} />
        <Route element={<RequireAuth />}>
          <Route path="/" element={<Home />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}

export default App
