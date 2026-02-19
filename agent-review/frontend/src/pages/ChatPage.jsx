import { useState, useEffect } from 'react'
import { getChatSessions, getChatSession } from '../services/api'
import ChatLayout from '../components/chat/ChatLayout'
import LoadingSpinner from '../components/common/LoadingSpinner'
import './ChatPage.css'

function ChatPage() {
  const [sessions, setSessions] = useState([])
  const [currentSession, setCurrentSession] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadSessions()
  }, [])

  const loadSessions = async () => {
    try {
      setLoading(true)
      const data = await getChatSessions()
      setSessions(data)
    } catch (error) {
      console.error('Failed to load chat sessions:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSelectSession = async (sessionId) => {
    try {
      const session = await getChatSession(sessionId)
      setCurrentSession(session)
    } catch (error) {
      console.error('Failed to load session:', error)
    }
  }

  const handleNewSession = () => {
    setCurrentSession(null)
  }

  return (
    <div className="chat-page">
      {loading ? (
        <LoadingSpinner />
      ) : (
        <ChatLayout
          sessions={sessions}
          currentSession={currentSession}
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
          onSessionUpdate={loadSessions}
        />
      )}
    </div>
  )
}

export default ChatPage
