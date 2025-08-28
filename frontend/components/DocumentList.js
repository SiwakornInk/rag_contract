'use client'
import { useState } from 'react'

const styles = {
  container: {
    backgroundColor: 'white',
    borderRadius: '12px',
    padding: '30px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '25px'
  },
  title: {
    fontSize: '24px',
    fontWeight: '600',
    color: '#1e3a8a',
    fontFamily: 'Prompt, sans-serif'
  },
  refreshButton: {
    padding: '8px 16px',
    backgroundColor: '#f1f5f9',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    transition: 'background-color 0.2s',
    fontFamily: 'Prompt, sans-serif'
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse'
  },
  th: {
    textAlign: 'left',
    padding: '12px',
    borderBottom: '2px solid #e5e7eb',
    color: '#475569',
    fontSize: '14px',
    fontWeight: '600',
    fontFamily: 'Prompt, sans-serif'
  },
  td: {
    padding: '12px',
    borderBottom: '1px solid #f1f5f9',
    fontSize: '14px'
  },
  tr: {
    transition: 'background-color 0.2s',
    cursor: 'pointer'
  },
  trHover: {
    backgroundColor: '#f8fafc'
  },
  titleCell: {
    fontWeight: '500',
    color: '#1e3a8a'
  },
  badge: {
    display: 'inline-block',
    padding: '4px 8px',
    borderRadius: '4px',
    fontSize: '12px',
    backgroundColor: '#dbeafe',
    color: '#1e3a8a',
    fontWeight: '500'
  },
  actionButton: {
    padding: '6px 12px',
    backgroundColor: '#1e3a8a',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '12px',
    marginRight: '8px',
    transition: 'background-color 0.2s'
  },
  loading: {
    textAlign: 'center',
    padding: '40px',
    color: '#64748b'
  },
  empty: {
    textAlign: 'center',
    padding: '40px',
    color: '#94a3b8'
  }
}

export default function DocumentList({ documents, loading, onRefresh }) {
  const [hoveredRow, setHoveredRow] = useState(null)

  const formatDate = (dateStr) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleDateString('th-TH', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    })
  }

  const handleView = (e, docId) => {
    e.stopPropagation()
    // เปิด PDF ในแท็บใหม่โดยตรง
    window.open(`http://localhost:8000/document/${docId}/pdf`, '_blank')
  }

  const handleDownload = async (e, docId) => {
    e.stopPropagation()
    window.open(`http://localhost:8000/document/${docId}/download`, '_blank')
  }

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>
          <div style={{ fontSize: '24px', marginBottom: '10px' }}>⏳</div>
          กำลังโหลดข้อมูล...
        </div>
      </div>
    )
  }

  if (documents.length === 0) {
    return (
      <div style={styles.container}>
        <div style={styles.empty}>
          <div style={{ fontSize: '48px', marginBottom: '20px' }}>📭</div>
          <div style={{ fontSize: '18px', marginBottom: '10px' }}>
            ยังไม่มีเอกสารในระบบ
          </div>
          <div style={{ color: '#cbd5e1' }}>
            เริ่มต้นโดยการอัพโหลดสัญญาตัวแรกของคุณ
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>📂 รายการสัญญาทั้งหมด</h2>
        <button 
          style={styles.refreshButton}
          onClick={onRefresh}
          onMouseEnter={(e) => e.target.style.backgroundColor = '#e2e8f0'}
          onMouseLeave={(e) => e.target.style.backgroundColor = '#f1f5f9'}
        >
          🔄 รีเฟรช
        </button>
      </div>

      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>ชื่อสัญญา</th>
            <th style={styles.th}>ชื่อไฟล์</th>
            <th style={styles.th}>จำนวนหน้า</th>
            <th style={styles.th}>วันที่อัพโหลด</th>
            <th style={styles.th}>การดำเนินการ</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((doc) => (
            <tr
              key={doc.doc_id}
              style={{
                ...styles.tr,
                ...(hoveredRow === doc.doc_id ? styles.trHover : {})
              }}
              onMouseEnter={() => setHoveredRow(doc.doc_id)}
              onMouseLeave={() => setHoveredRow(null)}
            >
              <td style={{ ...styles.td, ...styles.titleCell }}>
                {doc.title}
              </td>
              <td style={styles.td}>
                <span style={styles.badge}>📄 {doc.filename}</span>
              </td>
              <td style={styles.td}>{doc.total_pages} หน้า</td>
              <td style={styles.td}>{formatDate(doc.upload_date)}</td>
              <td style={styles.td}>
                <button 
                  style={styles.actionButton}
                  onClick={(e) => handleView(e, doc.doc_id)}
                  onMouseEnter={(e) => e.target.style.backgroundColor = '#1e40af'}
                  onMouseLeave={(e) => e.target.style.backgroundColor = '#1e3a8a'}
                >
                  👁️ ดู
                </button>
                <button 
                  style={styles.actionButton}
                  onClick={(e) => handleDownload(e, doc.doc_id)}
                  onMouseEnter={(e) => e.target.style.backgroundColor = '#1e40af'}
                  onMouseLeave={(e) => e.target.style.backgroundColor = '#1e3a8a'}
                >
                  ⬇️ ดาวน์โหลด
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}