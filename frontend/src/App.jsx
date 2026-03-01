import React, { useState, useEffect, useRef, useCallback } from 'react'
import './App.css'
import Settings from './Settings'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const WS_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/^http/, 'ws') + '/ws'

function App() {
  const [activeTab, setActiveTab] = useState('chat')
  const [prompt, setPrompt] = useState('')
  const [messages, setMessages] = useState([])
  const [emotion, setEmotion] = useState(null)
  const [knowledgeGraph, setKnowledgeGraph] = useState(null)
  const [autonomy, setAutonomy] = useState(null)
  const [loading, setLoading] = useState(false)
  
  // RAG и история
  const [ragContext, setRagContext] = useState(null)
  const [showSidebar, setShowSidebar] = useState(true)
  const [ragStats, setRagStats] = useState(null)
  
  // Аналитика
  const [analytics, setAnalytics] = useState(null)
  const [analyticsDays, setAnalyticsDays] = useState(7)
  
  // Mind State
  const [mindState, setMindState] = useState(null)
  
  // Новые модули
  const [truthStats, setTruthStats] = useState(null)
  const [safetyStats, setSafetyStats] = useState(null)
  const [eventsStats, setEventsStats] = useState(null)
  
  // Persona
  const [persona, setPersona] = useState(null)
  const [personaTraits, setPersonaTraits] = useState(null)
  
  // Pipeline
  const [pipelineStats, setPipelineStats] = useState(null)
  
  // Health Monitor
  const [healthData, setHealthData] = useState(null)
  
  // Roots Memory
  const [rootsData, setRootsData] = useState(null)
  
  // Meta Controller
  const [metaData, setMetaData] = useState(null)
  
  // Hygiene
  const [hygieneStats, setHygieneStats] = useState(null)
  const [hygieneReport, setHygieneReport] = useState(null)
  
  // v3.1: Новые компоненты
  const [episodicStats, setEpisodicStats] = useState(null)
  const [episodicTimeline, setEpisodicTimeline] = useState(null)
  const [semanticStats, setSemanticStats] = useState(null)
  const [dreamStats, setDreamStats] = useState(null)
  const [plansStats, setPlansStats] = useState(null)
  const [plansHierarchy, setPlansHierarchy] = useState(null)
  
  // Raw GigaChat response
  const [showRawResponse, setShowRawResponse] = useState(false)
  const [lastRawResponse, setLastRawResponse] = useState(null)
  const [lastMetadata, setLastMetadata] = useState(null)
  
  // WebSocket
  const [wsConnected, setWsConnected] = useState(false)
  const [wsMessages, setWsMessages] = useState([])
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const [showSettings, setShowSettings] = useState(false)

  // WebSocket подключение
  const connectWebSocket = useCallback(() => {
    // Не пытаемся подключиться если уже подключены или подключаемся
    if (wsRef.current?.readyState === WebSocket.OPEN || 
        wsRef.current?.readyState === WebSocket.CONNECTING) {
      return
    }
    
    try {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws
      
      ws.onopen = () => {
        console.log('📡 WebSocket подключен')
        setWsConnected(true)
        
        // Подписываемся на обновления
        ws.send(JSON.stringify({
          type: 'subscribe',
          channels: ['emotion', 'memory', 'autonomy', 'all']
        }))
      }
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          handleWsMessage(data)
        } catch (e) {
          console.error('Ошибка парсинга WS:', e)
        }
      }
      
      ws.onclose = () => {
        console.log('📡 WebSocket отключен')
        setWsConnected(false)
        
        // Переподключение через 5 секунд (увеличил для стабильности)
        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebSocket()
        }, 5000)
      }
      
      ws.onerror = () => {
        // Ошибка подключения - сервер недоступен
        // onclose будет вызван автоматически
      }
      
    } catch (e) {
      console.error('Ошибка создания WebSocket:', e)
      setWsConnected(false)
    }
  }, [])
  
  // Обработка WebSocket сообщений
  const handleWsMessage = (data) => {
    setWsMessages(prev => [...prev.slice(-50), data])
    
    switch (data.type) {
      case 'emotion_update':
        setEmotion(data.state)
        break
      case 'memory_update':
        if (data.memory_type === 'rag') {
          setRagStats(prev => ({ ...prev, ...data.data }))
        }
        break
      case 'autonomy_event':
        setAutonomy(prev => ({
          ...prev,
          planner: { ...prev?.planner, ...data.data }
        }))
        break
      case 'chat_response':
        // Ответ через WebSocket
        setMessages(prev => [...prev, {
          id: Date.now(),
          role: 'ai',
          text: data.response,
          provider: data.provider,
          confidence: data.confidence,
          timestamp: data.timestamp
        }])
        setLoading(false)
        break
      case 'mind_state':
        setMindState(data.state)
        break
      default:
        break
    }
  }
  
  // Отправка через WebSocket
  const sendWsMessage = (type, payload = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, ...payload }))
    }
  }
  
  // WebSocket ping для проверки соединения
  useEffect(() => {
    const interval = setInterval(() => {
      if (wsConnected) {
        sendWsMessage('ping')
      }
    }, 30000)
    return () => clearInterval(interval)
  }, [wsConnected])

  // Загрузка данных при старте
  useEffect(() => {
    fetchEmotion()
    fetchAutonomy()
    fetchKnowledgeGraph()
    fetchRagStats()
    fetchAnalytics()
    
    // Подключаем WebSocket
    connectWebSocket()
    
    // Загружаем историю из localStorage
    const saved = localStorage.getItem('neuromind_history')
    if (saved) {
      setMessages(JSON.parse(saved))
    }
    
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [connectWebSocket])

  // Перезагрузка аналитики при смене периода
  useEffect(() => {
    fetchAnalytics()
  }, [analyticsDays])

  // Сохраняем историю в localStorage
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem('neuromind_history', JSON.stringify(messages))
    }
  }, [messages])

  const fetchEmotion = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/emotion/state`)
      const data = await res.json()
      setEmotion(data)
    } catch (e) {
      console.error('Ошибка загрузки эмоций:', e)
    }
  }

  const fetchAutonomy = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/autonomy/status`)
      const data = await res.json()
      setAutonomy(data)
    } catch (e) {
      console.error('Ошибка загрузки автономии:', e)
    }
  }

  const fetchKnowledgeGraph = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/knowledge/graph`)
      const data = await res.json()
      setKnowledgeGraph(data)
    } catch (e) {
      console.error('Ошибка загрузки графа:', e)
    }
  }

  const fetchRagStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/rag/stats`)
      const data = await res.json()
      setRagStats(data)
    } catch (e) {
      console.error('Ошибка загрузки RAG статистики:', e)
    }
  }

  const fetchAnalytics = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/analytics/report?days=${analyticsDays}`)
      const data = await res.json()
      setAnalytics(data)
    } catch (e) {
      console.error('Ошибка загрузки аналитики:', e)
    }
  }

  const fetchMindState = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/mind-state`)
      const data = await res.json()
      setMindState(data)
    } catch (e) {
      console.error('Ошибка загрузки Mind State:', e)
    }
  }

  const fetchTruthStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/truth/stats`)
      const data = await res.json()
      setTruthStats(data)
    } catch (e) {
      console.error('Ошибка загрузки Truth:', e)
    }
  }

  const fetchSafetyStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/safety/stats`)
      const data = await res.json()
      setSafetyStats(data)
    } catch (e) {
      console.error('Ошибка загрузки Safety:', e)
    }
  }

  const fetchEventsStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/events/stats`)
      const data = await res.json()
      setEventsStats(data)
    } catch (e) {
      console.error('Ошибка загрузки Events:', e)
    }
  }

  // Persona
  const fetchPersona = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/persona/stats`)
      const data = await res.json()
      setPersona(data)
    } catch (e) {
      console.error('Ошибка загрузки Persona:', e)
    }
  }

  const fetchPersonaTraits = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/persona/traits`)
      const data = await res.json()
      setPersonaTraits(data)
    } catch (e) {
      console.error('Ошибка загрузки Traits:', e)
    }
  }

  // Pipeline
  const fetchPipelineStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/pipeline/stats`)
      const data = await res.json()
      setPipelineStats(data)
    } catch (e) {
      console.error('Ошибка загрузки Pipeline:', e)
    }
  }

  // Health Monitor
  const fetchHealthData = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/health`)
      const data = await res.json()
      setHealthData(data)
    } catch (e) {
      console.error('Ошибка загрузки Health:', e)
    }
  }

  // Roots Memory
  const fetchRootsData = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/roots`)
      const data = await res.json()
      setRootsData(data)
    } catch (e) {
      console.error('Ошибка загрузки Roots:', e)
    }
  }

  // Meta Controller
  const fetchMetaData = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/meta/stats`)
      const data = await res.json()
      setMetaData(data)
    } catch (e) {
      console.error('Ошибка загрузки Meta:', e)
    }
  }

  // Hygiene
  const fetchHygieneStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/hygiene/stats`)
      const data = await res.json()
      setHygieneStats(data)
    } catch (e) {
      console.error('Ошибка загрузки Hygiene:', e)
    }
  }

  const runHygieneAnalyze = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/hygiene/analyze?dry_run=true`, { method: 'POST' })
      const data = await res.json()
      setHygieneReport(data)
    } catch (e) {
      console.error('Ошибка анализа памяти:', e)
    }
  }

  const runHygieneCleanup = async () => {
    if (!confirm('Выполнить очистку памяти?')) return
    try {
      const res = await fetch(`${API_URL}/api/v1/hygiene/cleanup`, 
        { method: 'POST' })
      const data = await res.json()
      setHygieneReport(data.report)
      alert(`Очистка завершена!`)
    } catch (e) {
      console.error('Ошибка очистки памяти:', e)
    }
  }

  // v3.1: Episodic Memory
  const fetchEpisodicStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/episodic/stats`)
      const data = await res.json()
      setEpisodicStats(data)
    } catch (e) {
      console.error('Ошибка Episodic:', e)
    }
  }

  const fetchEpisodicTimeline = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/episodic/timeline?limit=10`)
      const data = await res.json()
      setEpisodicTimeline(data)
    } catch (e) {
      console.error('Ошибка Timeline:', e)
    }
  }

  // v3.1: Semantic Memory
  const fetchSemanticStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/semantic/stats`)
      const data = await res.json()
      setSemanticStats(data)
    } catch (e) {
      console.error('Ошибка Semantic:', e)
    }
  }

  // v3.1: Dreams
  const fetchDreamStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/dreams/stats`)
      const data = await res.json()
      setDreamStats(data)
    } catch (e) {
      console.error('Ошибка Dreams:', e)
    }
  }

  // v3.1: Plans
  const fetchPlansStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/plans/stats`)
      const data = await res.json()
      setPlansStats(data)
    } catch (e) {
      console.error('Ошибка Plans:', e)
    }
  }

  const fetchPlansHierarchy = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/plans/hierarchy`)
      const data = await res.json()
      setPlansHierarchy(data)
    } catch (e) {
      console.error('Ошибка Hierarchy:', e)
    }
  }

  const searchRag = async (query) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/rag/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, n_results: 3 })
      })
      const data = await res.json()
      return data.results
    } catch (e) {
      console.error('Ошибка поиска RAG:', e)
      return []
    }
  }

  const sendChat = async () => {
    if (!prompt.trim()) return
    
    setLoading(true)
    
    // Ищем релевантный контекст
    const ragResults = await searchRag(prompt)
    setRagContext(ragResults)
    
    const userMessage = { 
      id: Date.now(),
      role: 'user', 
      text: prompt,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMessage])
    
    try {
      const res = await fetch(`${API_URL}/api/v1/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      })
      const data = await res.json()
      
      const aiMessage = { 
        id: Date.now() + 1,
        role: 'ai', 
        text: data.response,
        provider: data.provider,
        confidence: data.confidence,
        cached: data.cached,
        ragUsed: data.rag_used,
        timestamp: new Date().toISOString(),
        rawLlmResponse: data.raw_llm_response,
        llmMetadata: data.llm_metadata
      }
      setMessages(prev => [...prev, aiMessage])
      setPrompt('')
      
      // Сохраняем сырой ответ для отображения
      if (data.raw_llm_response) {
        setLastRawResponse(data.raw_llm_response)
        setLastMetadata(data.llm_metadata)
      }
      
      // Обновляем статистику
      fetchRagStats()
      fetchEmotion()
      fetchAnalytics()
    } catch (e) {
      console.error('Ошибка чата:', e)
      setMessages(prev => [...prev, { 
        id: Date.now() + 1,
        role: 'ai', 
        text: 'Ошибка подключения к серверу',
        error: true,
        timestamp: new Date().toISOString()
      }])
    }
    
    setLoading(false)
  }

  const clearHistory = () => {
    if (confirm('Очистить историю чата?')) {
      setMessages([])
      localStorage.removeItem('neuromind_history')
    }
  }

  const exportToMarkdown = () => {
    let md = '# 🧠 PAD+ AI — История диалогов\n\n'
    md += `**Дата экспорта:** ${new Date().toLocaleString('ru')}\n\n`
    md += '---\n\n'
    
    messages.forEach((msg, i) => {
      const time = new Date(msg.timestamp).toLocaleString('ru')
      if (msg.role === 'user') {
        md += `### 👤 Пользователь (${time})\n\n${msg.text}\n\n`
      } else {
        md += `### 🤖 PAD+ AI (${time})\n\n${msg.text}\n\n`
        if (msg.provider) {
          md += `*Provider: ${msg.provider}, Confidence: ${msg.confidence}*\n\n`
        }
      }
    })
    
    downloadFile(md, 'padplus-history.md', 'text/markdown')
  }

  const exportToJSON = () => {
    const data = {
      exported: new Date().toISOString(),
      total_messages: messages.length,
      messages: messages
    }
    downloadFile(JSON.stringify(data, null, 2), 'padplus-history.json', 'application/json')
  }

  const downloadFile = (content, filename, type) => {
    const blob = new Blob([content], { type })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const startAutonomy = async () => {
    try {
      await fetch(`${API_URL}/api/v1/autonomy/start`, { method: 'POST' })
      fetchAutonomy()
    } catch (e) {
      console.error('Ошибка запуска автономии:', e)
    }
  }

  const stopAutonomy = async () => {
    try {
      await fetch(`${API_URL}/api/v1/autonomy/stop`, { method: 'POST' })
      fetchAutonomy()
    } catch (e) {
      console.error('Ошибка остановки автономии:', e)
    }
  }

  const runReflection = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/autonomy/reflect`, { method: 'POST' })
      const data = await res.json()
      alert(`Рефлексия завершена!\nНайдено: ${data.findings?.low_confidence?.length || 0} записей`)
    } catch (e) {
      console.error('Ошибка рефлексии:', e)
    }
  }

  // Компонент простого графика
  const SimpleChart = ({ data, labels, title, color = '#00d9ff' }) => {
    if (!data || !labels || data.length === 0) {
      return <p className="empty">Нет данных</p>
    }
    
    const max = Math.max(...data, 1)
    
    return (
      <div className="simple-chart">
        <h4>{title}</h4>
        <div className="chart-bars">
          {data.map((value, i) => (
            <div key={i} className="chart-bar-wrapper">
              <div 
                className="chart-bar" 
                style={{ 
                  height: `${(value / max) * 100}%`,
                  background: color
                }}
                title={`${labels[i]}: ${value}`}
              >
                {value > 0 && <span className="bar-value">{value}</span>}
              </div>
              <span className="bar-label">{labels[i]}</span>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      {/* Боковая панель истории */}
      {showSidebar && (
        <aside className="sidebar">
          <div className="sidebar-header">
            <h3>📜 История</h3>
            <button onClick={() => setShowSidebar(false)} className="close-btn">×</button>
          </div>
          
          <div className="sidebar-stats">
            {ragStats && (
              <span className="rag-badge" title="Диалогов в RAG">
                📚 {ragStats.total_dialogs}
              </span>
            )}
            <span className="msg-count">{messages.length} сообщений</span>
          </div>
          
          <div className="sidebar-actions">
            <button onClick={exportToMarkdown} className="export-btn" disabled={messages.length === 0}>
              📄 MD
            </button>
            <button onClick={exportToJSON} className="export-btn" disabled={messages.length === 0}>
              📋 JSON
            </button>
            <button onClick={clearHistory} className="clear-btn" disabled={messages.length === 0}>
              🗑️
            </button>
          </div>
          
          <div className="history-list">
            {messages.filter(m => m.role === 'user').map((msg, i) => (
              <div 
                key={msg.id || i} 
                className="history-item"
                title={msg.text}
              >
                <span className="history-time">
                  {new Date(msg.timestamp).toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' })}
                </span>
                <span className="history-text">
                  {msg.text.length > 30 ? msg.text.substring(0, 30) + '...' : msg.text}
                </span>
              </div>
            ))}
          </div>
        </aside>
      )}

      <div className="main-content">
        <header className="header">
          <h1>
            {!showSidebar && (
              <button onClick={() => setShowSidebar(true)} className="menu-btn">☰</button>
            )}
            🧠 PAD+ AI
          </h1>
          <div className="header-right">
            <button 
              onClick={() => setShowSettings(true)}
              className="settings-btn"
              title="Настройки провайдеров LLM"
            >
              ⚙️
            </button>
            <span className={`ws-status ${wsConnected ? 'connected' : 'disconnected'}`}>
              {wsConnected ? '📡' : '📵'}
            </span>
            <span className="version">v3.5 Cognitive</span>
          </div>
        </header>

        <nav className="tabs">
          <button 
            className={activeTab === 'chat' ? 'active' : ''} 
            onClick={() => setActiveTab('chat')}
          >
            💬 Чат
          </button>
          <button 
            className={activeTab === 'analytics' ? 'active' : ''} 
            onClick={() => setActiveTab('analytics')}
          >
            📊 Аналитика
          </button>
          <button 
            className={activeTab === 'emotions' ? 'active' : ''} 
            onClick={() => setActiveTab('emotions')}
          >
            😊 Эмоции
          </button>
          <button 
            className={activeTab === 'knowledge' ? 'active' : ''} 
            onClick={() => setActiveTab('knowledge')}
          >
            🕸️ Граф знаний
          </button>
          <button 
            className={activeTab === 'autonomy' ? 'active' : ''} 
            onClick={() => setActiveTab('autonomy')}
          >
            🔄 Автономия
          </button>
          <button 
            className={activeTab === 'mindstate' ? 'active' : ''} 
            onClick={() => { setActiveTab('mindstate'); fetchMindState(); }}
          >
            🧠 Mind State
          </button>
          <button 
            className={activeTab === 'persona' ? 'active' : ''} 
            onClick={() => { setActiveTab('persona'); fetchPersona(); fetchPersonaTraits(); }}
          >
            🎭 Persona
          </button>
          <button 
            className={activeTab === 'pipeline' ? 'active' : ''} 
            onClick={() => { setActiveTab('pipeline'); fetchPipelineStats(); }}
          >
            🔄 Pipeline
          </button>
          <button 
            className={activeTab === 'hygiene' ? 'active' : ''} 
            onClick={() => { setActiveTab('hygiene'); fetchHygieneStats(); }}
          >
            🧹 Гигиена
          </button>
          <button 
            className={activeTab === 'health' ? 'active' : ''} 
            onClick={() => { setActiveTab('health'); fetchHealthData(); }}
          >
            💚 Здоровье
          </button>
          <button 
            className={activeTab === 'roots' ? 'active' : ''} 
            onClick={() => { setActiveTab('roots'); fetchRootsData(); }}
          >
            🌳 Корни
          </button>
          <button 
            className={activeTab === 'meta' ? 'active' : ''} 
            onClick={() => { setActiveTab('meta'); fetchMetaData(); }}
          >
            🧬 Мета
          </button>
        </nav>

        <main className="content">
          {/* ЧАТ */}
          {activeTab === 'chat' && (
            <div className="chat-container">
              {/* RAG контекст */}
              {ragContext && ragContext.length > 0 && (
                <div className="rag-context">
                  <div className="rag-header">
                    <span>📚 Найдено в памяти</span>
                    <button onClick={() => setRagContext(null)} className="close-rag">×</button>
                  </div>
                  <div className="rag-items">
                    {ragContext.map((item, i) => (
                      <div key={i} className="rag-item">
                        <span className="rag-similarity">
                          {(item.similarity * 100).toFixed(0)}% схожесть
                        </span>
                        <div className="rag-text">
                          <strong>Вопрос:</strong> {item.metadata?.user_message?.substring(0, 100)}...
                        </div>
                        <div className="rag-text">
                          <strong>Ответ:</strong> {item.metadata?.ai_response?.substring(0, 100)}...
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              <div className="messages">
                {messages.length === 0 && (
                  <div className="welcome">
                    <h2>Привет! Я PAD+ AI</h2>
                    <p>Когнитивный слой, добавляющий эмоции и самосознание любому LLM.</p>
                    <p className="hint">Задайте мне вопрос, и я использую контекст из предыдущих диалогов.</p>
                  </div>
                )}
                {messages.map((msg, i) => (
                  <div key={msg.id || i} className={`message ${msg.role} ${msg.error ? 'error' : ''}`}>
                    <div className="text">{msg.text}</div>
                    {msg.provider && (
                      <div className="meta">
                        <span className="provider">{msg.provider}</span>
                        <span className="confidence">conf: {msg.confidence}</span>
                        {msg.ragUsed && <span className="rag-used">📚 RAG</span>}
                        {msg.cached && <span className="cached">📌 кэш</span>}
                        {msg.rawLlmResponse && (
                          <button 
                            className="raw-toggle-btn"
                            onClick={() => {
                              setShowRawResponse(showRawResponse === msg.id ? false : msg.id)
                            }}
                          >
                            🔧 RAW
                          </button>
                        )}
                      </div>
                    )}
                    {showRawResponse === msg.id && msg.rawLlmResponse && (
                      <div className="raw-response-panel">
                        <div className="raw-header">
                          <span>🤖 Сырой ответ GigaChat</span>
                          <button onClick={() => setShowRawResponse(false)}>×</button>
                        </div>
                        <div className="raw-metadata">
                          {msg.llmMetadata && (
                            <>
                              <span>Модель: {msg.llmMetadata.model || 'unknown'}</span>
                              <span>Токены: {msg.llmMetadata.usage?.total_tokens || 'N/A'}</span>
                              <span>Finish: {msg.llmMetadata.finish_reason || 'N/A'}</span>
                            </>
                          )}
                        </div>
                        <pre className="raw-content">
                          {typeof msg.rawLlmResponse === 'string' 
                            ? msg.rawLlmResponse 
                            : JSON.stringify(msg.rawLlmResponse, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
                {loading && <div className="message ai loading">Думаю...</div>}
              </div>
              
              <div className="input-area">
                <input
                  type="text"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && sendChat()}
                  placeholder="Введите сообщение..."
                  disabled={loading}
                />
                <button onClick={sendChat} disabled={loading || !prompt.trim()}>
                  Отправить
                </button>
              </div>
            </div>
          )}

          {/* АНАЛИТИКА */}
          {activeTab === 'analytics' && analytics && (
            <div className="analytics-container">
              <div className="analytics-header">
                <h2>📊 Аналитика использования</h2>
                <div className="period-selector">
                  <button 
                    className={analyticsDays === 7 ? 'active' : ''} 
                    onClick={() => setAnalyticsDays(7)}
                  >
                    7 дней
                  </button>
                  <button 
                    className={analyticsDays === 30 ? 'active' : ''} 
                    onClick={() => setAnalyticsDays(30)}
                  >
                    30 дней
                  </button>
                  <button 
                    className={analyticsDays === 90 ? 'active' : ''} 
                    onClick={() => setAnalyticsDays(90)}
                  >
                    90 дней
                  </button>
                </div>
              </div>
              
              {/* Dashboard метрики */}
              <div className="dashboard-metrics">
                <div className="metric-card">
                  <span className="metric-icon">💬</span>
                  <span className="metric-value">{analytics.dashboard?.total_messages || 0}</span>
                  <span className="metric-label">Сообщений</span>
                </div>
                <div className="metric-card">
                  <span className="metric-icon">👤</span>
                  <span className="metric-value">{analytics.dashboard?.messages_by_role?.user || 0}</span>
                  <span className="metric-label">От вас</span>
                </div>
                <div className="metric-card">
                  <span className="metric-icon">🤖</span>
                  <span className="metric-value">{analytics.dashboard?.messages_by_role?.ai || 0}</span>
                  <span className="metric-label">От ИИ</span>
                </div>
                <div className="metric-card">
                  <span className="metric-icon">📊</span>
                  <span className="metric-value">{analytics.dashboard?.avg_session_length || 0}</span>
                  <span className="metric-label">Ср. длина сессии</span>
                </div>
              </div>
              
              {/* Графики активностей */}
              <div className="activity-charts">
                <div className="chart-section">
                  <h3>🕐 Активность по часам</h3>
                  <SimpleChart 
                    data={analytics.activity?.hourly?.data} 
                    labels={analytics.activity?.hourly?.labels?.map(l => l.split(':')[0])}
                    title=""
                    color="#00d9ff"
                  />
                  {analytics.activity?.hourly?.peak_hour !== null && (
                    <p className="peak-info">
                      Пик активности: {analytics.activity?.hourly?.peak_hour}:00
                    </p>
                  )}
                </div>
                
                <div className="chart-section">
                  <h3>📅 Активность по дням недели</h3>
                  <SimpleChart 
                    data={analytics.activity?.weekday?.data} 
                    labels={analytics.activity?.weekday?.labels}
                    title=""
                    color="#00ff88"
                  />
                  {analytics.activity?.weekday?.peak_day && (
                    <p className="peak-info">
                      Самый активный: {analytics.activity?.weekday?.peak_day}
                    </p>
                  )}
                </div>
              </div>
              
              {/* Топ темы */}
              <div className="topics-section">
                <h3>📝 Популярные темы</h3>
                {analytics.topics?.top_topics?.length > 0 ? (
                  <div className="topics-list">
                    {analytics.topics.top_topics.map((t, i) => (
                      <div key={i} className="topic-item">
                        <span className="topic-rank">#{i + 1}</span>
                        <span className="topic-name">{t.topic}</span>
                        <span className="topic-count">{t.count} раз</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="empty">Пока нет данных о темах</p>
                )}
              </div>
              
              <button onClick={fetchAnalytics} className="refresh-btn">
                🔄 Обновить аналитику
              </button>
            </div>
          )}

          {/* ЭМОЦИИ */}
          {activeTab === 'emotions' && emotion && (
            <div className="emotions-container">
              <h2>😊 Эмоциональное состояние (PAD+)</h2>
              
              <div className="emotion-grid">
                <div className="emotion-item">
                  <label>Удовольствие</label>
                  <div className="bar">
                    <div 
                      className="fill" 
                      style={{ 
                        width: `${(emotion.удовольствие + 1) * 50}%`,
                        background: emotion.удовольствие > 0 ? '#4CAF50' : '#f44336'
                      }}
                    ></div>
                  </div>
                  <span>{emotion.удовольствие.toFixed(2)}</span>
                </div>
                
                <div className="emotion-item">
                  <label>Возбуждение</label>
                  <div className="bar">
                    <div 
                      className="fill" 
                      style={{ 
                        width: `${(emotion.возбуждение + 1) * 50}%`,
                        background: emotion.возбуждение > 0 ? '#FF9800' : '#2196F3'
                      }}
                    ></div>
                  </div>
                  <span>{emotion.возбуждение.toFixed(2)}</span>
                </div>
                
                <div className="emotion-item">
                  <label>Доминирование</label>
                  <div className="bar">
                    <div 
                      className="fill" 
                      style={{ 
                        width: `${(emotion.доминирование + 1) * 50}%`,
                        background: emotion.доминирование > 0 ? '#9C27B0' : '#607D8B'
                      }}
                    ></div>
                  </div>
                  <span>{emotion.доминирование.toFixed(2)}</span>
                </div>
                
                <div className="emotion-item">
                  <label>Любопытство</label>
                  <div className="bar">
                    <div 
                      className="fill curiosity" 
                      style={{ width: `${emotion.любопытство * 100}%` }}
                    ></div>
                  </div>
                  <span>{emotion.любопытство.toFixed(2)}</span>
                </div>
                
                <div className="emotion-item">
                  <label>Уверенность</label>
                  <div className="bar">
                    <div 
                      className="fill confidence" 
                      style={{ width: `${emotion.уверенность * 100}%` }}
                    ></div>
                  </div>
                  <span>{emotion.уверенность.toFixed(2)}</span>
                </div>
                
                <div className="emotion-item">
                  <label>Социальная связь</label>
                  <div className="bar">
                    <div 
                      className="fill" 
                      style={{ 
                        width: `${(emotion.социальная_связь + 1) * 50}%`,
                        background: emotion.социальная_связь > 0 ? '#E91E63' : '#795548'
                      }}
                    ></div>
                  </div>
                  <span>{emotion.социальная_связь.toFixed(2)}</span>
                </div>
              </div>

              <div className="style-info">
                <h3>Стиль общения</h3>
                <div className="style-tags">
                  <span className="tag">Тон: {emotion.style?.tone}</span>
                  <span className="tag">Подробность: {emotion.style?.verbosity}</span>
                  <span className="tag">Цвет: {emotion.style?.color}</span>
                </div>
              </div>

              <button onClick={fetchEmotion} className="refresh-btn">
                🔄 Обновить
              </button>
            </div>
          )}

          {/* ГРАФ ЗНАНИЙ */}
          {activeTab === 'knowledge' && knowledgeGraph && (
            <div className="knowledge-container">
              <h2>🕸️ Граф знаний</h2>
              
              <div className="stats">
                <div className="stat">
                  <span className="number">{knowledgeGraph.stats?.nodes || 0}</span>
                  <span className="label">Узлов</span>
                </div>
                <div className="stat">
                  <span className="number">{knowledgeGraph.stats?.edges || 0}</span>
                  <span className="label">Связей</span>
                </div>
                <div className="stat">
                  <span className="number">
                    {knowledgeGraph.stats?.density?.toFixed(3) || 0}
                  </span>
                  <span className="label">Плотность</span>
                </div>
              </div>

              <div className="nodes-list">
                <h3>Концепции</h3>
                {knowledgeGraph.nodes?.length > 0 ? (
                  <ul>
                    {knowledgeGraph.nodes.map((node, i) => (
                      <li key={i}>
                        <span className="node-name">{node.name}</span>
                        <span className="node-type">({node.type})</span>
                        <span className="node-conf">conf: {node.confidence?.toFixed(2)}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="empty">Пока нет концепций</p>
                )}
              </div>

              <div className="links-list">
                <h3>Связи</h3>
                {knowledgeGraph.links?.length > 0 ? (
                  <ul>
                    {knowledgeGraph.links.map((link, i) => (
                      <li key={i}>
                        {link.source} → {link.target}
                        <span className="link-type">({link.type})</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="empty">Пока нет связей</p>
                )}
              </div>

              <button onClick={fetchKnowledgeGraph} className="refresh-btn">
                🔄 Обновить
              </button>
            </div>
          )}

          {/* АВТОНОМИЯ */}
          {activeTab === 'autonomy' && autonomy && (
            <div className="autonomy-container">
              <h2>🔄 Автономные процессы</h2>
              
              {/* RAG статистика */}
              {ragStats && (
                <div className="rag-stats-section">
                  <h3>📚 RAG Память</h3>
                  <div className="status-row">
                    <span>Диалогов: {ragStats.total_dialogs}</span>
                    <span>Энкодер: {ragStats.encoder}</span>
                  </div>
                </div>
              )}
              
              <div className="autonomy-section">
                <h3>Планировщик вопросов</h3>
                <div className="status-row">
                  <span className={`status ${autonomy.planner?.running ? 'running' : 'stopped'}`}>
                    {autonomy.planner?.running ? '▶️ Работает' : '⏹️ Остановлен'}
                  </span>
                  <span>Ожидающих: {autonomy.planner?.pending_tasks || 0}</span>
                  <span>Выполнено: {autonomy.planner?.completed_tasks || 0}</span>
                </div>
                <div className="button-group">
                  <button onClick={startAutonomy} className="start-btn">▶️ Запустить</button>
                  <button onClick={stopAutonomy} className="stop-btn">⏹️ Остановить</button>
                </div>
              </div>

              <div className="autonomy-section">
                <h3>Саморефлексия</h3>
                <div className="status-row">
                  <span>Последняя: {autonomy.self_reflection?.last_reflection 
                    ? new Date(autonomy.self_reflection.last_reflection).toLocaleString('ru')
                    : 'не выполнялась'}</span>
                  <span>Находок: {autonomy.self_reflection?.total_findings || 0}</span>
                </div>
                <button onClick={runReflection} className="reflect-btn">
                  🔍 Запустить рефлексию
                </button>
              </div>

              <button onClick={() => { fetchAutonomy(); fetchRagStats(); }} className="refresh-btn">
                🔄 Обновить статус
              </button>
            </div>
          )}

          {/* MIND STATE */}
          {activeTab === 'mindstate' && (
            <div className="mindstate-container">
              <h2>🧠 Mind State — Полное состояние системы</h2>
              
              {mindState ? (
                <>
                  {/* Эмоциональное состояние */}
                  <div className="mindstate-section">
                    <h3>😊 Эмоции</h3>
                    <div className="mindstate-grid">
                      <div className="mini-metric">
                        <span className="label">Удовольствие</span>
                        <span className="value">{mindState.emotion?.удовольствие?.toFixed(2) || 0}</span>
                      </div>
                      <div className="mini-metric">
                        <span className="label">Возбуждение</span>
                        <span className="value">{mindState.emotion?.возбуждение?.toFixed(2) || 0}</span>
                      </div>
                      <div className="mini-metric">
                        <span className="label">Доминирование</span>
                        <span className="value">{mindState.emotion?.доминирование?.toFixed(2) || 0}</span>
                      </div>
                      <div className="mini-metric">
                        <span className="label">Любопытство</span>
                        <span className="value">{mindState.emotion?.любопытство?.toFixed(2) || 0}</span>
                      </div>
                      <div className="mini-metric">
                        <span className="label">Уверенность</span>
                        <span className="value">{mindState.emotion?.уверенность?.toFixed(2) || 0}</span>
                      </div>
                      <div className="mini-metric">
                        <span className="label">Стиль</span>
                        <span className="value">{mindState.emotion?.style?.tone || 'neutral'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Память */}
                  <div className="mindstate-section">
                    <h3>📚 Память</h3>
                    <div className="mindstate-grid">
                      <div className="mini-metric">
                        <span className="label">RAG Диалоги</span>
                        <span className="value">{mindState.memory?.rag?.total_dialogs || 0}</span>
                      </div>
                      <div className="mini-metric">
                        <span className="label">RAG Ключи</span>
                        <span className="value">{mindState.memory?.rag?.unique_keys || 0}</span>
                      </div>
                      <div className="mini-metric">
                        <span className="label">Факты</span>
                        <span className="value">{mindState.memory?.facts?.total_facts || 0}</span>
                      </div>
                      <div className="mini-metric">
                        <span className="label">Ср. уверенность</span>
                        <span className="value">{mindState.memory?.facts?.average_confidence?.toFixed(2) || 0}</span>
                      </div>
                    </div>
                  </div>

                  {/* Граф знаний */}
                  <div className="mindstate-section">
                    <h3>🕸️ Граф знаний</h3>
                    <div className="mindstate-grid">
                      <div className="mini-metric">
                        <span className="label">Узлов</span>
                        <span className="value">{mindState.knowledge?.nodes || 0}</span>
                      </div>
                      <div className="mini-metric">
                        <span className="label">Связей</span>
                        <span className="value">{mindState.knowledge?.edges || 0}</span>
                      </div>
                    </div>
                  </div>

                  {/* Автономность */}
                  <div className="mindstate-section">
                    <h3>🔄 Автономность</h3>
                    <div className="mindstate-grid">
                      <div className="mini-metric">
                        <span className="label">Статус</span>
                        <span className={`value ${mindState.autonomy?.running ? 'running' : 'stopped'}`}>
                          {mindState.autonomy?.running ? '▶️ Работает' : '⏹️ Остановлен'}
                        </span>
                      </div>
                      <div className="mini-metric">
                        <span className="label">Диалогов</span>
                        <span className="value">{mindState.autonomy?.dialog_count || 0}</span>
                      </div>
                    </div>
                  </div>

                  {/* Truth Loop */}
                  <div className="mindstate-section">
                    <h3>🔁 Truth Loop</h3>
                    <div className="mindstate-grid">
                      <div className="mini-metric">
                        <span className="label">Всего Claims</span>
                        <span className="value">{mindState.truth?.total_claims || 0}</span>
                      </div>
                      <div className="mini-metric">
                        <span className="label">Ср. уверенность</span>
                        <span className="value">{mindState.truth?.average_confidence?.toFixed(2) || 0}</span>
                      </div>
                    </div>
                  </div>

                  {/* Safety */}
                  <div className="mindstate-section">
                    <h3>🛡️ Безопасность</h3>
                    <div className="mindstate-grid">
                      <div className="mini-metric">
                        <span className="label">Запросов/мин</span>
                        <span className="value">{mindState.safety?.requests_last_minute || 0}</span>
                      </div>
                      <div className="mini-metric">
                        <span className="label">Автономных</span>
                        <span className="value">{mindState.safety?.autonomous_actions || 0}</span>
                      </div>
                      <div className="mini-metric">
                        <span className="label">Строгий режим</span>
                        <span className="value">{mindState.safety?.strict_mode ? '🔒 Вкл' : '🔓 Выкл'}</span>
                      </div>
                    </div>
                  </div>

                  {/* Events */}
                  <div className="mindstate-section">
                    <h3>📡 События</h3>
                    <div className="mindstate-grid">
                      <div className="mini-metric">
                        <span className="label">Всего событий</span>
                        <span className="value">{mindState.events?.total_events || 0}</span>
                      </div>
                      <div className="mini-metric">
                        <span className="label">Обработчиков</span>
                        <span className="value">{mindState.events?.handlers_count || 0}</span>
                      </div>
                    </div>
                  </div>

                  <button onClick={fetchMindState} className="refresh-btn">
                    🔄 Обновить Mind State
                  </button>
                </>
              ) : (
                <div className="loading-state">
                  <p>Загрузка состояния системы...</p>
                  <button onClick={fetchMindState} className="refresh-btn">
                    🔄 Загрузить
                  </button>
                </div>
              )}
            </div>
          )}

          {/* PERSONA */}
          {activeTab === 'persona' && (
            <div className="persona-container">
              <h2>🎭 Persona — Личность</h2>
              
              {/* Статистика */}
              {persona && (
                <div className="persona-stats">
                  <div className="stat">
                    <span className="number">{persona.traits_count}</span>
                    <span className="label">Черт характера</span>
                  </div>
                  <div className="stat">
                    <span className="number">{persona.users_known}</span>
                    <span className="label">Пользователей</span>
                  </div>
                  <div className="stat">
                    <span className="number">{persona.total_interactions}</span>
                    <span className="label">Взаимодействий</span>
                  </div>
                  <div className="stat">
                    <span className="number">{persona.reflections_count}</span>
                    <span className="label">Рефлексий</span>
                  </div>
                </div>
              )}
              
              {/* Черты характера */}
              <div className="traits-section">
                <h3>🧬 Черты характера</h3>
                {personaTraits?.traits ? (
                  <div className="traits-list">
                    {Object.entries(personaTraits.traits).map(([key, trait]) => (
                      <div key={key} className="trait-item">
                        <div className="trait-header">
                          <span className="trait-name">{trait.name}</span>
                          <span className="trait-value">{(trait.value * 100).toFixed(0)}%</span>
                        </div>
                        <div className="trait-bar">
                          <div 
                            className="trait-fill" 
                            style={{ 
                              width: `${trait.value * 100}%`,
                              background: trait.value > 0.7 ? '#4CAF50' : 
                                         trait.value > 0.4 ? '#FF9800' : '#f44336'
                            }}
                          ></div>
                        </div>
                        <span className="trait-desc">{trait.description}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="empty">Загрузка...</p>
                )}
              </div>
              
              {/* Доминирующие черты */}
              {persona?.dominant_traits && (
                <div className="dominant-section">
                  <h3>👑 Доминирующие черты</h3>
                  <div className="dominant-tags">
                    {persona.dominant_traits.map((trait, i) => (
                      <span key={i} className="dominant-tag">{trait}</span>
                    ))}
                  </div>
                </div>
              )}
              
              <button onClick={() => { fetchPersona(); fetchPersonaTraits(); }} className="refresh-btn">
                🔄 Обновить
              </button>
            </div>
          )}

          {/* PIPELINE */}
          {activeTab === 'pipeline' && (
            <div className="pipeline-container">
              <h2>🔄 Pipeline — Нервная система</h2>
              
              {/* Статистика */}
              {pipelineStats && (
                <div className="pipeline-stats">
                  <div className="stat">
                    <span className="number">{pipelineStats.total_calls || 0}</span>
                    <span className="label">Всего вызовов</span>
                  </div>
                  <div className="stat">
                    <span className="number">{pipelineStats.anti_loop_history_size || 0}</span>
                    <span className="label">Anti-loop история</span>
                  </div>
                </div>
              )}
              
              {/* Стадии пайплайна */}
              <div className="pipeline-stages">
                <h3>📋 Стадии обработки</h3>
                <div className="stages-list">
                  <div className="stage-item">
                    <span className="stage-num">1</span>
                    <span className="stage-name">🛡️ Safety Layer</span>
                    <span className="stage-desc">Проверка безопасности</span>
                  </div>
                  <div className="stage-item">
                    <span className="stage-num">2</span>
                    <span className="stage-name">🎯 Intent Router</span>
                    <span className="stage-desc">Классификация намерения</span>
                  </div>
                  <div className="stage-item">
                    <span className="stage-num">3</span>
                    <span className="stage-name">📚 Retrieve</span>
                    <span className="stage-desc">RAG + Facts + Knowledge</span>
                  </div>
                  <div className="stage-item">
                    <span className="stage-num">4</span>
                    <span className="stage-name">🎭 Persona</span>
                    <span className="stage-desc">Контекст личности</span>
                  </div>
                  <div className="stage-item">
                    <span className="stage-num">5</span>
                    <span className="stage-name">🤖 Generate</span>
                    <span className="stage-desc">Генерация ответа</span>
                  </div>
                  <div className="stage-item">
                    <span className="stage-num">6</span>
                    <span className="stage-name">✅ Truth Loop</span>
                    <span className="stage-desc">Верификация</span>
                  </div>
                  <div className="stage-item">
                    <span className="stage-num">7</span>
                    <span className="stage-name">💾 Remember</span>
                    <span className="stage-desc">Сохранение в память</span>
                  </div>
                  <div className="stage-item">
                    <span className="stage-num">8</span>
                    <span className="stage-name">🧬 Evolve</span>
                    <span className="stage-desc">Эволюция личности</span>
                  </div>
                  <div className="stage-item">
                    <span className="stage-num">9</span>
                    <span className="stage-name">📡 Emit</span>
                    <span className="stage-desc">События</span>
                  </div>
                </div>
              </div>
              
              {/* Anti-Loop Guard */}
              <div className="anti-loop-section">
                <h3>🔒 Anti-Loop Guard</h3>
                <p className="section-desc">
                  Защита от зацикливания. Отслеживает повторяющиеся запросы 
                  и блокирует циклические паттерны.
                </p>
                <div className="anti-loop-info">
                  <span>История: {pipelineStats?.anti_loop_history_size || 0} записей</span>
                  <span>Порог: 3 повторения</span>
                </div>
              </div>
              
              <button onClick={fetchPipelineStats} className="refresh-btn">
                🔄 Обновить
              </button>
            </div>
          )}

          {/* ЗДОРОВЬЕ */}
          {activeTab === 'health' && (
            <div className="health-container">
              <h2>💚 Здоровье — Когнитивный мониторинг</h2>
              
              {healthData ? (
                <>
                  {/* Общий score */}
                  <div className="health-score-section">
                    <div className="health-score-circle">
                      <span className="score-value">
                        {(healthData.overall_score * 100).toFixed(0)}%
                      </span>
                      <span className="score-label">Общее здоровье</span>
                    </div>
                  </div>
                  
                  {/* Метрики */}
                  <div className="health-metrics">
                    <div className="metric-card">
                      <span className="metric-icon">🎯</span>
                      <span className="metric-value">
                        {typeof healthData.metrics?.focus?.value === 'number' 
                          ? healthData.metrics.focus.value.toFixed(2) 
                          : (healthData.metrics?.focus?.toFixed(2) || '0.00')}
                      </span>
                      <span className="metric-label">Фокус</span>
                    </div>
                    <div className="metric-card">
                      <span className="metric-icon">⚡</span>
                      <span className="metric-value">
                        {typeof healthData.metrics?.energy?.value === 'number' 
                          ? healthData.metrics.energy.value.toFixed(2) 
                          : (healthData.metrics?.energy?.toFixed(2) || '0.00')}
                      </span>
                      <span className="metric-label">Энергия</span>
                    </div>
                    <div className="metric-card">
                      <span className="metric-icon">🔗</span>
                      <span className="metric-value">
                        {typeof healthData.metrics?.coherence?.value === 'number' 
                          ? healthData.metrics.coherence.value.toFixed(2) 
                          : (healthData.metrics?.coherence?.toFixed(2) || '0.00')}
                      </span>
                      <span className="metric-label">Когерентность</span>
                    </div>
                    <div className="metric-card">
                      <span className="metric-icon">🔄</span>
                      <span className="metric-value">
                        {typeof healthData.metrics?.adaptability?.value === 'number' 
                          ? healthData.metrics.adaptability.value.toFixed(2) 
                          : (healthData.metrics?.adaptability?.toFixed(2) || '0.00')}
                      </span>
                      <span className="metric-label">Адаптивность</span>
                    </div>
                  </div>
                  
                  {/* Рекомендации */}
                  {healthData.recommendations && healthData.recommendations.length > 0 && (
                    <div className="health-recommendations">
                      <h3>💡 Рекомендации</h3>
                      <ul>
                        {healthData.recommendations.map((rec, i) => (
                          <li key={i}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {/* История */}
                  {healthData.history && healthData.history.length > 0 && (
                    <div className="health-history">
                      <h3>📈 История</h3>
                      <div className="history-chart">
                        {healthData.history.slice(-10).map((h, i) => (
                          <div key={i} className="history-bar" 
                            style={{ height: `${h.score * 100}%` }}
                            title={`${h.event}: ${(h.score * 100).toFixed(0)}%`}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="loading-state">
                  <p>Загрузка состояния здоровья...</p>
                </div>
              )}
              
              <button onClick={fetchHealthData} className="refresh-btn">
                🔄 Обновить
              </button>
            </div>
          )}

          {/* КОРНИ */}
          {activeTab === 'roots' && (
            <div className="roots-container">
              <h2>🌳 Корни — Фундаментальные знания</h2>
              
              {rootsData ? (
                <>
                  {/* Статистика */}
                  <div className="roots-stats">
                    <div className="stat">
                      <span className="number">{rootsData.total || 0}</span>
                      <span className="label">Записей</span>
                    </div>
                    <div className="stat">
                      <span className="number">{rootsData.categories?.length || 0}</span>
                      <span className="label">Категорий</span>
                    </div>
                  </div>
                  
                  {/* Список корней */}
                  <div className="roots-list">
                    <h3>📚 Фундаментальные принципы</h3>
                    {rootsData.items && rootsData.items.length > 0 ? (
                      <div className="roots-items">
                        {rootsData.items.map((item, i) => (
                          <div key={i} className="root-item">
                            <span className="root-category">{item.category}</span>
                            <span className="root-content">{item.content}</span>
                            <span className="root-confidence">
                              conf: {(item.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="empty">Корни пока не добавлены</p>
                    )}
                  </div>
                  
                  {/* Категории */}
                  {rootsData.categories && rootsData.categories.length > 0 && (
                    <div className="roots-categories">
                      <h3>🏷️ Категории</h3>
                      <div className="category-tags">
                        {rootsData.categories.map((cat, i) => (
                          <span key={i} className="category-tag">{cat}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="loading-state">
                  <p>Загрузка корней...</p>
                </div>
              )}
              
              <button onClick={fetchRootsData} className="refresh-btn">
                🔄 Обновить
              </button>
            </div>
          )}

          {/* МЕТА */}
          {activeTab === 'meta' && (
            <div className="meta-container">
              <h2>🧬 Мета — Мета-когнитивный контроллер</h2>
              
              {metaData ? (
                <>
                  {/* Состояние */}
                  <div className="meta-state">
                    <div className="state-badge">
                      <span className="state-icon">
                        {metaData.state === 'idle' ? '😴' : 
                         metaData.state === 'processing' ? '⚡' : 
                         metaData.state === 'reflecting' ? '🤔' : '🔄'}
                      </span>
                      <span className="state-name">{metaData.state}</span>
                    </div>
                  </div>
                  
                  {/* Статистика */}
                  <div className="meta-stats">
                    <div className="stat">
                      <span className="number">{metaData.total_requests || 0}</span>
                      <span className="label">Запросов</span>
                    </div>
                    <div className="stat">
                      <span className="number">{metaData.successful_adaptations || 0}</span>
                      <span className="label">Адаптаций</span>
                    </div>
                    <div className="stat">
                      <span className="number">{metaData.subsystems || 0}</span>
                      <span className="label">Подсистем</span>
                    </div>
                  </div>
                  
                  {/* Когнитивная нагрузка */}
                  {metaData.cognitive_load && (
                    <div className="cognitive-load-section">
                      <h3>⚖️ Когнитивная нагрузка</h3>
                      <div className="load-bar">
                        <div className="load-fill" 
                          style={{ width: `${metaData.cognitive_load.current * 100}%` }}
                        />
                      </div>
                      <div className="load-details">
                        <span>Текущая: {(metaData.cognitive_load.current * 100).toFixed(0)}%</span>
                        <span>Ошибки: {metaData.cognitive_load.recent_errors || 0}</span>
                      </div>
                    </div>
                  )}
                  
                  {/* Распределение стратегий */}
                  {metaData.strategy_distribution && (
                    <div className="strategy-section">
                      <h3>📊 Стратегии</h3>
                      <div className="strategy-list">
                        {Object.entries(metaData.strategy_distribution).map(([name, count]) => (
                          <div key={name} className="strategy-item">
                            <span className="strategy-name">{name}</span>
                            <span className="strategy-count">{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Последние решения */}
                  {metaData.recent_decisions && metaData.recent_decisions > 0 && (
                    <div className="decisions-section">
                      <h3>🎯 Последние решения</h3>
                      <p className="decisions-count">
                        {metaData.recent_decisions} решений принято
                      </p>
                    </div>
                  )}
                </>
              ) : (
                <div className="loading-state">
                  <p>Загрузка мета-контроллера...</p>
                </div>
              )}
              
              <button onClick={fetchMetaData} className="refresh-btn">
                🔄 Обновить
              </button>
            </div>
          )}

          {/* HYGIENE */}
          {activeTab === 'hygiene' && (
            <div className="hygiene-container">
              <h2>🧹 Гигиена — Очистка памяти</h2>
              
              {/* Статистика */}
              {hygieneStats && (
                <div className="hygiene-stats">
                  <div className="stat">
                    <span className="number">{hygieneStats.total_cleanups || 0}</span>
                    <span className="label">Очисток</span>
                  </div>
                  <div className="stat">
                    <span className="number">{hygieneStats.config?.obsolete_days || 90}</span>
                    <span className="label">Дней до устаревания</span>
                  </div>
                </div>
              )}
              
              {/* Действия */}
              <div className="hygiene-actions">
                <h3>🔧 Действия</h3>
                <div className="action-buttons">
                  <button onClick={runHygieneAnalyze} className="analyze-btn">
                    🔍 Анализ (dry run)
                  </button>
                  <button onClick={runHygieneCleanup} className="cleanup-btn">
                    🧹 Очистка
                  </button>
                </div>
              </div>
              
              {/* Результат анализа */}
              {hygieneReport && (
                <div className="hygiene-report">
                  <h3>📊 Результат анализа</h3>
                  
                  <div className="report-metrics">
                    <div className="report-metric">
                      <span className="label">Просканировано</span>
                      <span className="value">{hygieneReport.items_scanned}</span>
                    </div>
                    <div className="report-metric">
                      <span className="label">Дубликатов</span>
                      <span className="value">{hygieneReport.duplicates?.found || 0}</span>
                    </div>
                    <div className="report-metric">
                      <span className="label">Устаревших</span>
                      <span className="value">{hygieneReport.obsolete?.found || 0}</span>
                    </div>
                    <div className="report-metric">
                      <span className="label">Низкое качество</span>
                      <span className="value">{hygieneReport.low_quality?.found || 0}</span>
                    </div>
                    <div className="report-metric">
                      <span className="label">Освобождено</span>
                      <span className="value">{hygieneReport.space_freed_kb || 0} KB</span>
                    </div>
                  </div>
                  
                  {/* Рекомендации */}
                  {hygieneReport.recommendations && hygieneReport.recommendations.length > 0 && (
                    <div className="recommendations">
                      <h4>💡 Рекомендации</h4>
                      <ul>
                        {hygieneReport.recommendations.map((rec, i) => (
                          <li key={i}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
              
              {/* Конфигурация */}
              <div className="hygiene-config">
                <h3>⚙️ Конфигурация</h3>
                <div className="config-list">
                  <div className="config-item">
                    <span>Порог схожести:</span>
                    <span>{hygieneStats?.config?.similarity_threshold || 0.85}</span>
                  </div>
                  <div className="config-item">
                    <span>Дней до устаревания:</span>
                    <span>{hygieneStats?.config?.obsolete_days || 90}</span>
                  </div>
                  <div className="config-item">
                    <span>Порог полезности:</span>
                    <span>{hygieneStats?.config?.usefulness_threshold || 0.2}</span>
                  </div>
                  <div className="config-item">
                    <span>Макс. элементов:</span>
                    <span>{hygieneStats?.config?.max_items || 10000}</span>
                  </div>
                </div>
              </div>
              
              <button onClick={fetchHygieneStats} className="refresh-btn">
                🔄 Обновить
              </button>
            </div>
          )}
        </main>

        <footer className="footer">
          <span>ANTI_DIRECTIVE: Не закрепляй знания, сомневайся, проверяй...</span>
        </footer>
      </div>

      {/* Модальное окно настроек */}
      {showSettings && (
        <Settings onClose={() => setShowSettings(false)} />
      )}
    </div>
  )
}

export default App
