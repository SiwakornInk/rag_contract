'use client'
import { useState, useRef, useEffect } from 'react'
import { askQuestion } from '@/utils/api'
import ReactMarkdown from 'react-markdown'

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    backgroundColor: 'white'
  },
  header: {
    padding: '20px 30px',
    borderBottom: '1px solid #e5e7eb',
    backgroundColor: '#fafbfc'
  },
  headerTitle: {
    fontSize: '20px',
    fontWeight: '600',
    color: '#1e3a8a',
    marginBottom: '8px',
    fontFamily: 'Prompt, sans-serif'
  },
  headerSubtitle: {
    fontSize: '14px',
    color: '#64748b',
    fontFamily: 'Prompt, sans-serif'
  },
  messagesContainer: {
    flex: 1,
    overflowY: 'auto',
    padding: '30px',
    display: 'flex',
    flexDirection: 'column',
    gap: '20px'
  },
  messageGroup: {
    display: 'flex',
    gap: '15px',
    animation: 'fadeIn 0.3s ease-in'
  },
  avatar: {
    width: '36px',
    height: '36px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '18px',
    flexShrink: 0
  },
  userAvatar: {
    backgroundColor: '#e0f2fe'
  },
  aiAvatar: {
    backgroundColor: '#fef3c7'
  },
  messageContent: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '8px'
  },
  messageRole: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#475569',
    fontFamily: 'Prompt, sans-serif'
  },
  messageText: {
    fontSize: '15px',
    lineHeight: '1.7',
    color: '#1f2937'
  },
  sources: {
    marginTop: '12px',
    padding: '12px',
    backgroundColor: '#f8fafc',
    borderRadius: '8px',
    borderLeft: '3px solid #1e3a8a'
  },
  sourceTitle: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#1e3a8a',
    marginBottom: '8px',
    fontFamily: 'Prompt, sans-serif'
  },
  sourceItem: {
    fontSize: '13px',
    color: '#64748b',
    marginBottom: '4px'
  },
  inputContainer: {
    padding: '20px 30px',
    borderTop: '1px solid #e5e7eb',
    backgroundColor: '#fafbfc'
  },
  inputWrapper: {
    display: 'flex',
    gap: '12px'
  },
  input: {
    flex: 1,
    padding: '12px 16px',
    fontSize: '15px',
    borderWidth: '1px',
    borderStyle: 'solid',
    borderColor: '#e5e7eb',
    borderRadius: '8px',
    outline: 'none',
    transition: 'border-color 0.2s, box-shadow 0.2s',
    fontFamily: 'Inter, Prompt, sans-serif'
  },
  inputFocused: {
    borderColor: '#1e3a8a',
    boxShadow: '0 0 0 3px rgba(30, 58, 138, 0.1)'
  },
  sendButton: {
    padding: '12px 24px',
    backgroundColor: '#1e3a8a',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '15px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
    fontFamily: 'Prompt, sans-serif',
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  },
  sendButtonDisabled: {
    backgroundColor: '#94a3b8',
    cursor: 'not-allowed'
  },
  loading: {
    display: 'flex',
    gap: '4px',
    padding: '8px'
  },
  loadingDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    backgroundColor: '#1e3a8a',
    animation: 'bounce 1.4s infinite ease-in-out'
  },
  suggestions: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '10px',
    marginTop: '15px'
  },
  suggestionChip: {
    padding: '8px 16px',
    backgroundColor: 'white',
    borderWidth: '1px',
    borderStyle: 'solid',
    borderColor: '#e5e7eb',
    borderRadius: '20px',
    fontSize: '13px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    fontFamily: 'Prompt, sans-serif'
  },
  suggestionChipHover: {
    backgroundColor: '#f1f5f9',
    borderColor: '#1e3a8a'
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#94a3b8'
  },
  emptyIcon: {
    fontSize: '64px',
    marginBottom: '20px'
  },
  emptyTitle: {
    fontSize: '20px',
    fontWeight: '500',
    marginBottom: '10px',
    color: '#64748b',
    fontFamily: 'Prompt, sans-serif'
  },
  emptyText: {
    fontSize: '14px',
    textAlign: 'center',
    maxWidth: '400px',
    lineHeight: '1.6',
    fontFamily: 'Prompt, sans-serif'
  }
}

const globalStyles = `
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  
  @keyframes bounce {
    0%, 80%, 100% { transform: scale(0); opacity: 0.5; }
    40% { transform: scale(1); opacity: 1; }
  }
`

export default function ChatInterface({ selectedDocument }) {
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [inputFocused, setInputFocused] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    const styleElement = document.createElement('style')
    styleElement.textContent = globalStyles
    document.head.appendChild(styleElement)
    
    return () => {
      document.head.removeChild(styleElement)
    }
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleSend = async () => {
    if (!inputValue.trim() || loading) return

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: inputValue,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setLoading(true)

    try {
      const response = await askQuestion(
        inputValue, 
        selectedDocument?.filename || null
      )

      const aiMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, aiMessage])
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'ขออภัย เกิดข้อผิดพลาดในการประมวลผลคำถามของคุณ กรุณาลองใหม่อีกครั้ง',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const suggestions = [
    "สรุปสาระสำคัญของสัญญานี้",
    "มูลค่าสัญญาเท่าไหร่",
    "ระยะเวลาสัญญากี่วัน",
    "มีเงื่อนไขการชำระเงินอย่างไร",
    "ใครคือคู่สัญญา"
  ]

  const handleSuggestionClick = (suggestion) => {
    setInputValue(suggestion)
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.headerTitle}>
          💬 ถาม AI เกี่ยวกับสัญญา
        </div>
        <div style={styles.headerSubtitle}>
          {selectedDocument 
            ? `กำลังค้นหาจาก: ${selectedDocument.title}`
            : 'กำลังค้นหาจากทุกเอกสารในระบบ'}
        </div>
      </div>

      <div style={styles.messagesContainer}>
        {messages.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={styles.emptyIcon}>🤖</div>
            <div style={styles.emptyTitle}>เริ่มถาม AI เกี่ยวกับสัญญา</div>
            <div style={styles.emptyText}>
              AI พร้อมตอบคำถามเกี่ยวกับรายละเอียดสัญญา เงื่อนไข ระยะเวลา มูลค่า และข้อมูลสำคัญอื่นๆ
            </div>
            <div style={styles.suggestions}>
              {suggestions.map((suggestion, index) => (
                <div
                  key={index}
                  style={styles.suggestionChip}
                  onClick={() => handleSuggestionClick(suggestion)}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#f1f5f9'
                    e.currentTarget.style.borderColor = '#1e3a8a'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'white'
                    e.currentTarget.style.borderColor = '#e5e7eb'
                  }}
                >
                  {suggestion}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div key={message.id} style={styles.messageGroup}>
                <div style={{
                  ...styles.avatar,
                  ...(message.role === 'user' ? styles.userAvatar : styles.aiAvatar)
                }}>
                  {message.role === 'user' ? '👤' : '🤖'}
                </div>
                <div style={styles.messageContent}>
                  <div style={styles.messageRole}>
                    {message.role === 'user' ? 'คุณ' : 'AI Assistant'}
                  </div>
                  <div style={styles.messageText}>
                    {message.role === 'assistant' ? (
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    ) : (
                      message.content
                    )}
                  </div>
                  {message.sources && message.sources.length > 0 && (
                    <div style={styles.sources}>
                      <div style={styles.sourceTitle}>📚 แหล่งอ้างอิง:</div>
                      {message.sources.map((source, idx) => (
                        <div key={idx} style={styles.sourceItem}>
                          • {source.filename} (หน้า {source.page})
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div style={styles.messageGroup}>
                <div style={{ ...styles.avatar, ...styles.aiAvatar }}>🤖</div>
                <div style={styles.messageContent}>
                  <div style={styles.messageRole}>AI Assistant</div>
                  <div style={styles.loading}>
                    <div style={{ ...styles.loadingDot, animationDelay: '0s' }}></div>
                    <div style={{ ...styles.loadingDot, animationDelay: '0.2s' }}></div>
                    <div style={{ ...styles.loadingDot, animationDelay: '0.4s' }}></div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div style={styles.inputContainer}>
        <div style={styles.inputWrapper}>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            onFocus={() => setInputFocused(true)}
            onBlur={() => setInputFocused(false)}
            placeholder="พิมพ์คำถามเกี่ยวกับสัญญา..."
            style={{
              ...styles.input,
              ...(inputFocused ? styles.inputFocused : {})
            }}
            disabled={loading}
          />
          <button
            onClick={handleSend}
            style={{
              ...styles.sendButton,
              ...(loading || !inputValue.trim() ? styles.sendButtonDisabled : {})
            }}
            disabled={loading || !inputValue.trim()}
            onMouseEnter={(e) => {
              if (!loading && inputValue.trim()) {
                e.currentTarget.style.backgroundColor = '#1e40af'
              }
            }}
            onMouseLeave={(e) => {
              if (!loading && inputValue.trim()) {
                e.currentTarget.style.backgroundColor = '#1e3a8a'
              }
            }}
          >
            <span>ส่ง</span>
            <span>➤</span>
          </button>
        </div>
      </div>
    </div>
  )
}