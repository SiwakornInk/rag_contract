'use client'
import { useState, useEffect } from 'react'
import ChatInterface from '@/components/ChatInterface'
import { getDocuments } from '@/utils/api'

const styles = {
  container: {
    height: 'calc(100vh - 70px)',
    display: 'flex',
    backgroundColor: '#f8f9fa'
  },
  sidebar: {
    width: '300px',
    backgroundColor: 'white',
    borderRight: '1px solid #e5e7eb',
    padding: '20px',
    overflowY: 'auto'
  },
  sidebarTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#1e3a8a',
    marginBottom: '20px',
    fontFamily: 'Prompt, sans-serif'
  },
  documentList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px'
  },
  documentItem: {
    padding: '12px',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'all 0.2s',
    border: '1px solid transparent',
    fontSize: '14px'
  },
  documentItemActive: {
    backgroundColor: '#eff6ff',
    border: '1px solid #1e3a8a'
  },
  documentItemHover: {
    backgroundColor: '#f1f5f9'
  },
  allDocsOption: {
    padding: '12px',
    borderRadius: '8px',
    cursor: 'pointer',
    backgroundColor: '#1e3a8a',
    color: 'white',
    textAlign: 'center',
    fontWeight: '500',
    marginBottom: '15px',
    fontFamily: 'Prompt, sans-serif'
  },
  mainContent: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column'
  }
}

export default function ChatPage() {
  const [documents, setDocuments] = useState([])
  const [selectedDoc, setSelectedDoc] = useState(null)
  const [hoveredDoc, setHoveredDoc] = useState(null)

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

  return (
    <div style={styles.container}>
      <div style={styles.sidebar}>
        <h2 style={styles.sidebarTitle}>เลือกเอกสาร</h2>
        
        <div
          style={{
            ...styles.allDocsOption,
            ...(selectedDoc === null ? { backgroundColor: '#0f172a' } : {})
          }}
          onClick={() => setSelectedDoc(null)}
        >
          ค้นหาจากทุกเอกสาร
        </div>

        <div style={styles.documentList}>
          {documents.map((doc) => (
            <div
              key={doc.doc_id}
              style={{
                ...styles.documentItem,
                ...(selectedDoc?.doc_id === doc.doc_id ? styles.documentItemActive : {}),
                ...(hoveredDoc === doc.doc_id ? styles.documentItemHover : {})
              }}
              onMouseEnter={() => setHoveredDoc(doc.doc_id)}
              onMouseLeave={() => setHoveredDoc(null)}
              onClick={() => setSelectedDoc(doc)}
            >
              <div style={{ fontWeight: '500', marginBottom: '4px' }}>
                {doc.title}
              </div>
              <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '2px' }}>
                📄 {doc.filename}
              </div>
              <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                {doc.total_pages} หน้า
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={styles.mainContent}>
        <ChatInterface selectedDocument={selectedDoc} />
      </div>
    </div>
  )
}