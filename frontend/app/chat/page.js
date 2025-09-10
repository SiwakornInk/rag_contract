'use client'
import { useState, useEffect, useMemo } from 'react'
import ChatInterface from '@/components/ChatInterface'
import { getDocuments } from '@/utils/api'
import styles from './ChatPage.module.css'

const levelColors = {
  'PUBLIC': { bg: '#e0f2fe', text: '#0c4a6e' },
  'INTERNAL': { bg: '#d1fae5', text: '#065f46' },
  'CONFIDENTIAL': { bg: '#ffedd5', text: '#9a3412' },
  'SECRET': { bg: '#fee2e2', text: '#991b1b' },
  'DEFAULT': { bg: '#e5e7eb', text: '#4b5563' }
}

export default function ChatPage() {
  const [documents, setDocuments] = useState([])
  const [selectedDoc, setSelectedDoc] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterLevel, setFilterLevel] = useState('ALL')

  useEffect(() => {
    loadDocuments()
  }, [])

  const loadDocuments = async () => {
    try {
      const data = await getDocuments()
      setDocuments(data.documents || [])
    } catch (error) {
      console.error('Error loading documents:', error)
    }
  }

  const filteredDocuments = useMemo(() => {
    return documents
      .filter(doc => {
        const searchLower = searchTerm.toLowerCase()
        return doc.title?.toLowerCase().includes(searchLower) || doc.filename?.toLowerCase().includes(searchLower)
      })
      .filter(doc => {
        if (filterLevel === 'ALL') return true
        return (doc.classification || 'PUBLIC') === filterLevel
      })
  }, [documents, searchTerm, filterLevel])

  const classificationLevels = ['ALL', 'PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'SECRET']

  return (
    <div className={styles.container}>
      <div className={styles.sidebar}>
        <h2 className={styles.sidebarTitle}>เลือกเอกสารสำหรับถาม AI</h2>
        
        <div className={styles.controls}>
          <input
            type="text"
            placeholder="ค้นหาด้วยชื่อเรื่องหรือชื่อไฟล์..."
            className={styles.searchInput}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <select
            className={styles.filterSelect}
            value={filterLevel}
            onChange={(e) => setFilterLevel(e.target.value)}
          >
            {classificationLevels.map(level => (
              <option key={level} value={level}>{level}</option>
            ))}
          </select>
        </div>

        <div
          className={`${styles.allDocsOption} ${selectedDoc === null ? styles.active : ''}`}
          onClick={() => setSelectedDoc(null)}
        >
          ค้นหาจากทุกเอกสาร
        </div>

        <div className={styles.documentList}>
      {filteredDocuments.map((doc) => {
            const level = doc.classification || 'PUBLIC'
            const color = levelColors[level] || levelColors['DEFAULT']
            return (
              <div
                key={doc.doc_id}
                className={`${styles.documentItem} ${selectedDoc?.doc_id === doc.doc_id ? styles.active : ''}`}
                onClick={() => setSelectedDoc(doc)}
              >
        <div className={styles.docTitle}>{doc.title}</div>
        <div className={styles.docFilename}>{doc.filename}</div>
                <div className={styles.docDetails}>
                  <span className={styles.badge} style={{ backgroundColor: color.bg, color: color.text }}>
                    {level}
                  </span>
                  <span>{doc.total_pages} หน้า</span>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className={styles.mainContent}>
        <ChatInterface selectedDocument={selectedDoc} />
      </div>
    </div>
  )
}