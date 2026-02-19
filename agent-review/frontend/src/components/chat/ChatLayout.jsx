import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { chatAskStream } from '../../services/api'
import './ChatLayout.css'

function ChatLayout({ sessions, currentSession, onSelectSession, onNewSession, onSessionUpdate }) {
  const [input, setInput] = useState('')
  const [streamingMessage, setStreamingMessage] = useState(null)
  const [streamingSteps, setStreamingSteps] = useState([])
  const [pendingUserMessage, setPendingUserMessage] = useState(null)
  const [error, setError] = useState('')
  const messagesEndRef = useRef(null)

  const messages = currentSession?.conversation_history ?? currentSession?.session?.messages ?? []
  const sessionId = currentSession?.session?.id ?? null
  const isLoading = pendingUserMessage != null && streamingMessage === null

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingMessage, streamingSteps, pendingUserMessage])

  const handleSend = async () => {
    const question = input.trim()
    if (!question || pendingUserMessage != null) return
    setInput('')
    setError('')
    setStreamingSteps([])
    setStreamingMessage(null)
    setPendingUserMessage(question)

    const history = messages.map((m) => ({
      role: m.role,
      content: m.content || '',
    }))

    try {
      const newSessionId = await chatAskStream(
        question,
        sessionId,
        history,
        (event) => {
          if (event.type === 'step') {
            setStreamingSteps((prev) => [...prev, event.step || {}])
          }
          if (event.type === 'result' && event.answer != null) {
            setStreamingMessage(event.answer)
          }
          if (event.type === 'error') {
            setError(event.error || 'Unknown error')
          }
        }
      )
      setStreamingMessage(null)
      setStreamingSteps([])
      setPendingUserMessage(null)
      if (onSessionUpdate) onSessionUpdate()
      const idToSelect = newSessionId != null ? newSessionId : sessionId
      if (idToSelect != null && onSelectSession) onSelectSession(idToSelect)
    } catch (e) {
      setError(e?.message || 'Send failed')
      setStreamingMessage(null)
      setStreamingSteps([])
      setPendingUserMessage(null)
    }
  }

  return (
    <div className="chat-layout">
      <aside className="chat-sessions">
        <button type="button" className="btn-new-session" onClick={onNewSession}>
          + New chat
        </button>
        <ul className="session-list">
          {sessions.map((s) => (
            <li key={s.id}>
              <button
                type="button"
                className={`session-item ${currentSession?.session?.id === s.id ? 'active' : ''}`}
                onClick={() => onSelectSession(s.id)}
              >
                <span className="session-preview">{s.preview || `Session ${s.id}`}</span>
                <span className="session-date">
                  {s.updated_at ? new Date(s.updated_at).toLocaleDateString() : ''}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <div className="chat-main">
        <div className="chat-messages">
          {messages.length === 0 && !streamingMessage && !streamingSteps.length && !pendingUserMessage && (
            <div className="chat-empty">
              {currentSession ? 'No messages in this session yet.' : 'Select a session or start a new chat.'}
            </div>
          )}
          {messages.map((m) => (
            <div key={m.id} className={`message message-${m.role}`}>
              <div className="message-role">{m.role === 'user' ? 'You' : 'Assistant'}</div>
              <div className="message-content">
                {m.role === 'assistant' ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content || ''}</ReactMarkdown>
                ) : (
                  <span>{m.content}</span>
                )}
              </div>
              {m.steps && m.steps.length > 0 && (
                <div className="message-steps">
                  {m.steps.map((step, i) => (
                    <div key={i} className={`step step-${step.step_type || 'thought'}`}>
                      <span className="step-label">
                        {step.step_type === 'tool_call' && '🔧 Tool'}
                        {step.step_type === 'tool_result' && '📋 Result'}
                        {(step.step_type === 'thought' || !step.step_type) && '💭 Thought'}
                      </span>
                      {step.tool_name && <span className="step-tool">{step.tool_name}</span>}
                      {step.content && <pre className="step-content">{step.content}</pre>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
          {pendingUserMessage != null && (
            <div className="message message-user">
              <div className="message-role">You</div>
              <div className="message-content">
                <span>{pendingUserMessage}</span>
              </div>
            </div>
          )}
          {isLoading && streamingSteps.length === 0 && (
            <div className="message message-assistant message-loading">
              <div className="message-role">Assistant</div>
              <div className="message-content message-loading-content">
                <span className="typing-dots">
                  <span className="dot" />
                  <span className="dot" />
                  <span className="dot" />
                </span>
              </div>
            </div>
          )}
          {streamingSteps.length > 0 && (
            <div className="message message-assistant streaming-steps">
              <div className="message-role">Assistant</div>
              <div className="message-steps">
                {streamingSteps.map((step, i) => (
                  <div key={i} className={`step step-${step.step_type || 'thought'}`}>
                    <span className="step-label">
                      {step.step_type === 'tool_call' && '🔧 Tool'}
                      {step.step_type === 'tool_result' && '📋 Result'}
                      {(step.step_type === 'thought' || !step.step_type) && '💭 Thought'}
                    </span>
                    {step.tool_name && <span className="step-tool">{step.tool_name}</span>}
                    {step.content && <pre className="step-content">{step.content}</pre>}
                  </div>
                ))}
              </div>
            </div>
          )}
          {streamingMessage != null && (
            <div className="message message-assistant">
              <div className="message-role">Assistant</div>
              <div className="message-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingMessage}</ReactMarkdown>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {error && <div className="chat-error">{error}</div>}

        <div className="chat-input-wrap">
          <textarea
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
            placeholder="Ask about reviews, diagnoses, or sensors..."
            rows={2}
            disabled={!!pendingUserMessage}
          />
          <button
            type="button"
            className="btn-send"
            onClick={handleSend}
            disabled={!input.trim() || pendingUserMessage != null}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}

export default ChatLayout
