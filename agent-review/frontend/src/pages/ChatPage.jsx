import { useState, useEffect } from 'react'
import { getChatSessions, getChatSession, deleteChatSession } from '../services/api'
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

  const handleDeleteSession = async (sessionId, e) => {
    e?.stopPropagation?.()
    if (!confirm('Delete this conversation?')) return
    try {
      await deleteChatSession(sessionId)
      if (currentSession?.session?.id === sessionId) {
        setCurrentSession(null)
      }
      loadSessions()
    } catch (error) {
      console.error('Failed to delete session:', error)
    }
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
          onDeleteSession={handleDeleteSession}
        />
      )}
    </div>
  )
}

export default ChatPage
