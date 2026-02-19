import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import DashboardLayout from './components/layout/DashboardLayout'
import ReviewQueuePage from './pages/ReviewQueuePage'
import AlertsPage from './pages/AlertsPage'
import SensorsPage from './pages/SensorsPage'
import ChatPage from './pages/ChatPage'
import ScenariosPage from './pages/ScenariosPage'

function App() {
  return (
    <Router>
      <DashboardLayout>
        <Routes>
          <Route path="/" element={<Navigate to="/review" replace />} />
          <Route path="/review" element={<ReviewQueuePage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/sensors" element={<SensorsPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/scenarios" element={<ScenariosPage />} />
        </Routes>
      </DashboardLayout>
    </Router>
  )
}

export default App
