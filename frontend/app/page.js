'use client'
import { useState, useEffect } from 'react'
import DocumentList from '@/components/DocumentList'
import { getDocuments } from '@/utils/api'
import styles from './page.module.css'

export default function Home() {
  const [allDocuments, setAllDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({
    totalDocs: 0,
    totalPages: 0,
    avgPages: 0,
    lastUploadDate: null,
  })
  const [maxLevel, setMaxLevel] = useState('')

  useEffect(() => {
    if (typeof window !== 'undefined') {
      if (!localStorage.getItem('token')) {
        window.location.href = '/login'
        return
      }
      setMaxLevel(localStorage.getItem('max_level') || '')
    }
    loadDocuments()
  }, [])

  const loadDocuments = async () => {
    setLoading(true)
    try {
      const data = await getDocuments()
      const docs = data.documents || []
      setAllDocuments(docs)
      
      const totalPages = docs.reduce((sum, doc) => sum + (doc.total_pages || 0), 0)
      const avgPages = docs.length > 0 ? Math.round(totalPages / docs.length) : 0
      
      const sortedByDate = [...docs].sort((a, b) => new Date(b.upload_date) - new Date(a.upload_date))
      const lastUpload = sortedByDate[0]?.upload_date || null
      
      setStats({
        totalDocs: docs.length,
        totalPages: totalPages,
        avgPages: avgPages,
        lastUploadDate: lastUpload,
      })
    } catch (error) {
      console.error('Error loading documents:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A'
    const date = new Date(dateStr)
    return date.toLocaleDateString('th-TH', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    })
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>ระบบจัดการสัญญาอัจฉริยะ</h1>
        <p className={styles.subtitle}>วิเคราะห์ ค้นหา และจัดการเอกสารสัญญาของคุณด้วย AI</p>
        {maxLevel === 'PUBLIC' && (
          <div className={styles.publicWarning}>
            คุณกำลังใช้งานในระดับ Public – สามารถเข้าถึงได้เฉพาะเอกสาร Public เท่านั้น
          </div>
        )}
      </header>

      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statNumber}>{stats.totalDocs}</div>
          <div className={styles.statLabel}>สัญญาทั้งหมด</div>
        </div>
        
        <div className={styles.statCard}>
          <div className={styles.statNumber}>{stats.totalPages.toLocaleString()}</div>
          <div className={styles.statLabel}>หน้าเอกสารทั้งหมด</div>
          {stats.avgPages > 0 && (
            <div className={styles.statDetail}>เฉลี่ย {stats.avgPages} หน้า/ฉบับ</div>
          )}
        </div>
        
        <div className={styles.statCard}>
          <div className={styles.statNumber} style={{ fontSize: '1.25rem' }}>
            {formatDate(stats.lastUploadDate)}
          </div>
          <div className={styles.statLabel}>อัพโหลดล่าสุด</div>
        </div>
      </div>

  {/* CTA buttons removed per request */}

      <DocumentList 
        documents={allDocuments} 
        loading={loading} 
        onRefresh={loadDocuments} 
      />
    </div>
  )
}