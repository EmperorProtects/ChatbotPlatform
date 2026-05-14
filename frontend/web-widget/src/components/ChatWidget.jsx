import React, { useState, useRef, useEffect } from 'react'

export default function ChatWidget({ config }) {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState([
    { 
      id: 1, 
      text: 'Здравствуйте! Я ваш помощник. Чем могу помочь?', 
      sender: 'bot',
      timestamp: new Date()
    }
  ])
  const [inputText, setInputText] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [isConnected, setIsConnected] = useState(true)
  const [userId] = useState('web-user-' + Math.random().toString(36).substr(2, 9))
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const apiUrl = config?.apiUrl || 'http://localhost:8000'
  const briefId = config?.briefId || 1
  const theme = config?.theme || {}

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  // Load conversation history on open
  useEffect(() => {
    if (isOpen && messages.length <= 1) {
      loadConversationHistory()
    }
  }, [isOpen])

  const loadConversationHistory = async () => {
    try {
      const response = await fetch(`${apiUrl}/bot/conversation/${userId}?limit=20`)
      if (response.ok) {
        const data = await response.json()
        if (data.messages && data.messages.length > 0) {
          const historyMessages = data.messages.reverse().map((msg, index) => [
            {
              id: `history-user-${index}`,
              text: msg.message,
              sender: 'user',
              timestamp: new Date(msg.timestamp)
            },
            {
              id: `history-bot-${index}`,
              text: msg.response,
              sender: 'bot',
              timestamp: new Date(msg.timestamp)
            }
          ]).flat()
          
          setMessages([...historyMessages, ...messages])
        }
      }
    } catch (error) {
      console.error('Error loading conversation history:', error)
    }
  }

  const sendMessage = async () => {
    if (!inputText.trim() || isTyping) return

    const userMessage = {
      id: Date.now(),
      text: inputText.trim(),
      sender: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    const messageText = inputText
    setInputText('')
    setIsTyping(true)
    setIsConnected(true)

    try {
      const response = await fetch(`${apiUrl}/bot/incoming`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          brief_id: briefId,
          text: messageText,
          channel: 'web',
          language: 'ru'
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()
      
      // Simulate typing delay for better UX
      await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 1000))
      
      const botMessage = {
        id: Date.now() + 1,
        text: data.text || 'Извините, произошла ошибка. Попробуйте снова.',
        sender: 'bot',
        timestamp: new Date()
      }

      setMessages(prev => [...prev, botMessage])
      
    } catch (error) {
      console.error('Error sending message:', error)
      setIsConnected(false)
      
      const errorMessage = {
        id: Date.now() + 1,
        text: 'Ошибка соединения. Проверьте связь с интернетом.',
        sender: 'bot',
        timestamp: new Date(),
        isError: true
      }
      
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsTyping(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }
  
  const clearChat = () => {
    setMessages([
      {
        id: Date.now(),
        text: 'Чат очищен. Как я могу вам помочь?',
        sender: 'bot',
        timestamp: new Date()
      }
    ])
  }
  
  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('ru', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="chatbot-widget" style={{
      '--primary-color': theme.primaryColor || '#1976d2',
      '--secondary-color': theme.secondaryColor || '#f5f5f5',
      '--text-color': theme.textColor || '#333',
      '--border-radius': theme.borderRadius || '12px'
    }}>
      {/* Toggle Button */}
      <button
        className={`chatbot-toggle ${isOpen ? 'open' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        title={isOpen ? 'Закрыть чат' : 'Открыть чат'}
      >
        {isOpen ? (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
          </svg>
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h4l4 4 4-4h4c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z"/>
          </svg>
        )}
        {!isConnected && (
          <div className="connection-indicator error" title="Нет соединения"></div>
        )}
      </button>

      {/* Chat Window */}
      {isOpen && (
        <div className="chatbot-window">
          {/* Header */}
          <div className="chatbot-header">
            <div className="header-content">
              <h3>Помощник</h3>
              <div className="status">
                <div className={`status-indicator ${isConnected ? 'online' : 'offline'}`}></div>
                <span>{isConnected ? 'Онлайн' : 'Оффлайн'}</span>
              </div>
            </div>
            <div className="header-actions">
              <button onClick={clearChat} title="Очистить чат">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M19 7v-.5C19 5.12 17.88 4 16.5 4S14 5.12 14 6.5V7H6v2h1.2l.7 10.5c.1 1 .9 1.5 2 1.5h5c1.1 0 1.9-.5 2-1.5L17.8 9H19V7zm-7-.5c0-.28.22-.5.5-.5s.5.22.5.5V7h-1v-.5zm-1.9 2.5h7.8l-.6 9H10.7l-.6-9z"/>
                </svg>
              </button>
              <button onClick={() => setIsOpen(false)} title="Закрыть">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                </svg>
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="chatbot-messages">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`message ${msg.sender === 'user' ? 'user-message' : 'bot-message'} ${msg.isError ? 'error-message' : ''}`}
              >
                <div className="message-content">
                  <div className="message-text">{msg.text}</div>
                  <div className="message-time">{formatTime(msg.timestamp)}</div>
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="message bot-message typing-message">
                <div className="message-content">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="chatbot-input">
            <div className="input-container">
              <textarea
                ref={inputRef}
                placeholder="Напишите сообщение..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={isTyping}
                rows={1}
                style={{
                  resize: 'none',
                  overflow: 'hidden',
                  minHeight: '20px',
                  maxHeight: '120px'
                }}
                onInput={(e) => {
                  e.target.style.height = 'auto'
                  e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
                }}
              />
              <button 
                onClick={sendMessage} 
                disabled={!inputText.trim() || isTyping}
                className="send-button"
                title="Отправить"
              >
                {isTyping ? (
                  <div className="loading-spinner"></div>
                ) : (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                  </svg>
                )}
              </button>
            </div>
            <div className="input-footer">
              <small>Нажмите Enter для отправки</small>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
