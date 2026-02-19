import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import './DashboardLayout.css'

const menuItems = [
  { path: '/review', label: 'Review Queue', icon: '📋' },
  { path: '/alerts', label: 'Alerts', icon: '🚨' },
  { path: '/sensors', label: 'Sensors', icon: '📊' },
  { path: '/chat', label: 'Chat', icon: '💬' },
  { path: '/scenarios', label: 'Scenarios', icon: '⚙️' },
]

function DashboardLayout({ children }) {
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <div className="dashboard-layout">
      <header className="dashboard-header">
        <div className="header-left">
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            ☰
          </button>
          <h1>Agent D - Review Dashboard</h1>
        </div>
      </header>

      <div className="dashboard-content">
        <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
          <nav className="sidebar-nav">
            {menuItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
              >
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-label">{item.label}</span>
              </Link>
            ))}
          </nav>
        </aside>

        <main className="main-content">
          {children}
        </main>
      </div>
    </div>
  )
}

export default DashboardLayout
