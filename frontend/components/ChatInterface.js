'use client'
import { useState, useRef, useEffect } from 'react'
import { askQuestion } from '@/utils/api'
import ReactMarkdown from 'react-markdown'
import styles from './ChatInterface.module.css'

export default function ChatInterface({ selectedDocument }) {
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

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
      }
      setMessages(prev => [...prev, aiMessage])
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'ขออภัย เกิดข้อผิดพลาดในการประมวลผลคำถามของคุณ กรุณาลองใหม่อีกครั้ง',
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
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.headerTitle}>
          ถาม AI เกี่ยวกับสัญญา
        </h2>
        <p className={styles.headerSubtitle}>
          {selectedDocument 
            ? `กำลังค้นหาจาก: ${selectedDocument.title}`
            : 'กำลังค้นหาจากทุกเอกสารในระบบ'}
        </p>
      </div>

      <div className={styles.messagesContainer}>
        {messages.length === 0 ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>🤖</div>
            <h3 className={styles.emptyTitle}>เริ่มถาม AI เกี่ยวกับสัญญา</h3>
            <p className={styles.emptyText}>
              AI พร้อมตอบคำถามเกี่ยวกับรายละเอียดสัญญา เงื่อนไข ระยะเวลา มูลค่า และข้อมูลสำคัญอื่นๆ
            </p>
            <div className={styles.suggestions}>
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  className={styles.suggestionChip}
                  onClick={() => handleSuggestionClick(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div key={message.id} className={styles.messageGroup}>
                <div className={`${styles.avatar} ${message.role === 'user' ? styles.userAvatar : styles.aiAvatar}`}>
                  {message.role === 'user' ? '👤' : '🤖'}
                </div>
                <div className={styles.messageContent}>
                  <div className={styles.messageRole}>
                    {message.role === 'user' ? 'คุณ' : 'AI Assistant'}
                  </div>
                  <div className={styles.messageText}>
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>
                  {message.sources && message.sources.length > 0 && (
                    <div className={styles.sources}>
                      <div className={styles.sourceTitle}>แหล่งอ้างอิง:</div>
                      {message.sources.map((source, idx) => (
                        <div key={idx} className={styles.sourceItem}>
                          • {source.filename} (หน้า {source.page})
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className={styles.messageGroup}>
                <div className={`${styles.avatar} ${styles.aiAvatar}`}>🤖</div>
                <div className={styles.messageContent}>
                  <div className={styles.messageRole}>AI Assistant</div>
                  <div className={styles.loading}>
                    <div style={{ animationDelay: '0s' }} className={styles.loadingDot}></div>
                    <div style={{ animationDelay: '0.2s' }} className={styles.loadingDot}></div>
                    <div style={{ animationDelay: '0.4s' }} className={styles.loadingDot}></div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className={styles.inputContainer}>
        <div className={styles.inputWrapper}>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="พิมพ์คำถามเกี่ยวกับสัญญา..."
            className={styles.input}
            disabled={loading}
          />
          <button
            onClick={handleSend}
            className={styles.sendButton}
            disabled={loading || !inputValue.trim()}
          >
            <span>ส่ง</span>
            <span>➤</span>
          </button>
        </div>
      </div>
    </div>
  )
}