import { Navigate, Route, Routes } from 'react-router-dom'

import Layout from './components/Layout'
import { AuthProvider } from './auth/AuthProvider'
import { RequireAuth } from './auth/RequireAuth'
import BookScreen from './screens/BookScreen'
import GridScreen from './screens/GridScreen'
import LoginScreen from './screens/LoginScreen'
import ReservationsScreen from './screens/ReservationsScreen'
import SearchScreen from './screens/SearchScreen'

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginScreen />} />
        <Route element={<RequireAuth />}>
          <Route element={<Layout />}>
            <Route path="/" element={<SearchScreen />} />
            <Route path="/reservations" element={<ReservationsScreen />} />
            <Route path="/grid" element={<GridScreen />} />
          </Route>
          <Route path="/book" element={<BookScreen />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}

export default App
