import React from 'react'
import ReactDOM from 'react-dom/client'
import ChatWidget from './components/ChatWidget'
import './styles/widget.css'

// Initialize widget
window.ChatbotWidget = {
  init: (config) => {
    const container = document.getElementById(config.containerId || 'chatbot-widget')
    if (container) {
      const root = ReactDOM.createRoot(container)
      root.render(<ChatWidget config={config} />)
    }
  }
}

// Auto-init if container exists
if (document.getElementById('chatbot-widget')) {
  window.ChatbotWidget.init({
    apiUrl: 'http://localhost:8007',
  })
}
