'use client'
import { useState, useEffect } from 'react'
import DocumentList from '@/components/DocumentList'
import { getDocuments } from '@/utils/api'

const styles = {
  container: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: '40px 20px'
  },
  header: {
    marginBottom: '40px'
  },
  title: {
    fontSize: '36px',
    fontWeight: '700',
    color: '#1e3a8a',
    marginBottom: '10px',
    fontFamily: 'Prompt, sans-serif'
  },
  subtitle: {
    fontSize: '18px',
    color: '#64748b',
    fontFamily: 'Prompt, sans-serif'
  },
  statsContainer: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
    gap: '20px',
    marginBottom: '40px'
  },
  statCard: {
    backgroundColor: 'white',
    padding: '25px',
    borderRadius: '12px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    transition: 'transform 0.2s, box-shadow 0.2s',
    cursor: 'pointer'
  },
  statCardHover: {
    transform: 'translateY(-2px)',
    boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
  },
  statNumber: {
    fontSize: '32px',
    fontWeight: '700',
    color: '#1e3a8a',
    marginBottom: '8px'
  },
  statLabel: {
    fontSize: '14px',
    color: '#64748b',
    fontFamily: 'Prompt, sans-serif'
  },
  statDetail: {
    fontSize: '12px',
    color: '#94a3b8',
    marginTop: '8px',
    fontFamily: 'Prompt, sans-serif'
  },
  actionButtons: {
    display: 'flex',
    gap: '15px',
    marginBottom: '30px'
  },
  primaryButton: {
    backgroundColor: '#1e3a8a',
    color: 'white',
    padding: '12px 30px',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: '500',
    border: 'none',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
    fontFamily: 'Prompt, sans-serif',
    textDecoration: 'none',
    display: 'inline-block'
  },
  secondaryButton: {
    backgroundColor: 'white',
    color: '#1e3a8a',
    padding: '12px 30px',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: '500',
    border: '2px solid #1e3a8a',
    cursor: 'pointer',
    transition: 'all 0.2s',
    fontFamily: 'Prompt, sans-serif',
    textDecoration: 'none',
    display: 'inline-block'
  }
}

export default function Home() {
  const [documents, setDocuments] = useState([])
  const [hoveredCard, setHoveredCard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({
    totalDocs: 0,
    totalPages: 0,
    avgPages: 0,
    lastUploadDate: null,
    documentTypes: []
  })
  const [maxLevel, setMaxLevel] = useState('')

  useEffect(() => {
    if (typeof window !== 'undefined') {
      if (!localStorage.getItem('token')) {
        window.location.href = '/login'
        return
      }
    }
  setMaxLevel(localStorage.getItem('max_level')||'')
  loadDocuments()
  }, [])

  const loadDocuments = async () => {
    try {
      const data = await getDocuments()
      const docs = data.documents || []
      setDocuments(docs)
      
      // คำนวณสถิติจริงจากข้อมูล
      const totalPages = docs.reduce((sum, doc) => sum + (doc.total_pages || 0), 0)
      const avgPages = docs.length > 0 ? Math.round(totalPages / docs.length) : 0
      
      // หาวันที่อัพโหลดล่าสุด
      const sortedByDate = [...docs].sort((a, b) => 
        new Date(b.upload_date) - new Date(a.upload_date)
      )
      const lastUpload = sortedByDate[0]?.upload_date || null
      
      // รวบรวมประเภทเอกสาร (จาก metadata ถ้ามี)
      const types = new Set()
      docs.forEach(doc => {
        // ดึงประเภทจากชื่อไฟล์หรือ title
        if (doc.title) {
          if (doc.title.includes('สัญญาจ้าง')) types.add('สัญญาจ้าง')
          if (doc.title.includes('สัญญาซื้อขาย')) types.add('สัญญาซื้อขาย')
          if (doc.title.includes('สัญญาเช่า')) types.add('สัญญาเช่า')
          if (doc.title.includes('สัญญาบริการ')) types.add('สัญญาบริการ')
        }
      })
      
      setStats({
        totalDocs: docs.length,
        totalPages: totalPages,
        avgPages: avgPages,
        lastUploadDate: lastUpload,
        documentTypes: Array.from(types)
      })
    } catch (error) {
      console.error('Error loading documents:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return 'ยังไม่มีข้อมูล'
    const date = new Date(dateStr)
    return date.toLocaleDateString('th-TH', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    })
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>ระบบจัดการสัญญาอัจฉริยะ</h1>
        <p style={styles.subtitle}>วิเคราะห์และค้นหาข้อมูลสัญญาด้วยเทคโนโลยี AI</p>
        {maxLevel === 'PUBLIC' && (
          <div style={{marginTop:'10px', padding:'10px 14px', background:'#fff7ed', color:'#9a3412', borderRadius:'8px', fontSize:'13px'}}>
            คุณกำลังใช้งานในระดับ Public – เห็นได้เฉพาะเอกสาร Public เท่านั้น
          </div>
        )}
      </div>

      <div style={styles.statsContainer}>
        <div 
          style={{
            ...styles.statCard,
            ...(hoveredCard === 'docs' ? styles.statCardHover : {})
          }}
          onMouseEnter={() => setHoveredCard('docs')}
          onMouseLeave={() => setHoveredCard(null)}
        >
          <div style={styles.statNumber}>{stats.totalDocs}</div>
          <div style={styles.statLabel}>สัญญาทั้งหมด</div>
        </div>
        
        <div 
          style={{
            ...styles.statCard,
            ...(hoveredCard === 'pages' ? styles.statCardHover : {})
          }}
          onMouseEnter={() => setHoveredCard('pages')}
          onMouseLeave={() => setHoveredCard(null)}
        >
          <div style={styles.statNumber}>{stats.totalPages.toLocaleString()}</div>
          <div style={styles.statLabel}>หน้าเอกสารทั้งหมด</div>
          {stats.avgPages > 0 && (
            <div style={styles.statDetail}>เฉลี่ย {stats.avgPages} หน้า/เอกสาร</div>
          )}
        </div>
        
        <div 
          style={{
            ...styles.statCard,
            ...(hoveredCard === 'upload' ? styles.statCardHover : {})
          }}
          onMouseEnter={() => setHoveredCard('upload')}
          onMouseLeave={() => setHoveredCard(null)}
        >
          <div style={{ ...styles.statNumber, fontSize: '16px', lineHeight: '1.5' }}>
            {formatDate(stats.lastUploadDate)}
          </div>
          <div style={styles.statLabel}>อัพโหลดล่าสุด</div>
        </div>
      </div>

      <div style={styles.actionButtons}>
        <a href="/upload" style={styles.primaryButton}>
          📤 อัพโหลดสัญญาใหม่
        </a>
        <a href="/chat" style={styles.secondaryButton}>
          💬 ถาม AI เกี่ยวกับสัญญา
        </a>
      </div>

      <DocumentList documents={documents} loading={loading} onRefresh={loadDocuments} />
    </div>
  )
}