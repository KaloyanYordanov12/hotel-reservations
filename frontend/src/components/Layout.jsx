import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '../auth/authContext'
import { strings as t } from '../strings'
import './Layout.css'

// Shell for the two main tabs. The focused booking form is deliberately outside
// this layout: it is a single task with its own back link, not a place with tabs.
export default function Layout() {
  const { logout } = useAuth()

  return (
    <div className="layout">
      <nav className="tabs">
        <NavLink to="/" end className="tab">
          {t.tabs.availability}
        </NavLink>
        <NavLink to="/reservations" className="tab">
          {t.tabs.reservations}
        </NavLink>
        <NavLink to="/grid" className="tab">
          {t.tabs.planner}
        </NavLink>
        <button type="button" className="ghost tabs__logout" onClick={logout}>
          {t.common.logout}
        </button>
      </nav>
      <Outlet />
    </div>
  )
}
