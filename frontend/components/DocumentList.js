'use client'
import { useState, useMemo } from 'react'
import styles from './DocumentList.module.css'

const ITEMS_PER_PAGE = 10

const levelColors = {
  'PUBLIC': { bg: '#e0f2fe', text: '#0c4a6e' },
  'INTERNAL': { bg: '#d1fae5', text: '#065f46' },
  'CONFIDENTIAL': { bg: '#ffedd5', text: '#9a3412' },
  'SECRET': { bg: '#fee2e2', text: '#991b1b' },
  'DEFAULT': { bg: '#e5e7eb', text: '#4b5563' }
}

export default function DocumentList({ documents, loading, onRefresh }) {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterLevel, setFilterLevel] = useState('ALL')
  const [currentPage, setCurrentPage] = useState(1)

  const filteredDocuments = useMemo(() => {
    return documents
      .filter(doc => {
        const searchLower = searchTerm.toLowerCase()
        const titleMatch = doc.title?.toLowerCase().includes(searchLower)
        const filenameMatch = doc.filename?.toLowerCase().includes(searchLower)
        return titleMatch || filenameMatch
      })
      .filter(doc => {
        if (filterLevel === 'ALL') return true
        return (doc.classification || 'PUBLIC') === filterLevel
      })
  }, [documents, searchTerm, filterLevel])

  const paginatedDocuments = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE
    return filteredDocuments.slice(startIndex, startIndex + ITEMS_PER_PAGE)
  }, [filteredDocuments, currentPage])

  const totalPages = Math.ceil(filteredDocuments.length / ITEMS_PER_PAGE)

  const handleView = (e, docId) => {
    e.stopPropagation()
    const token = localStorage.getItem('token')
    const url = `http://localhost:8000/document/${docId}/pdf?token=${encodeURIComponent(token)}`
    window.open(url, '_blank')
  }

  const handleDownload = (e, docId) => {
    e.stopPropagation()
    const token = localStorage.getItem('token')
    const url = `http://localhost:8000/document/${docId}/download?token=${encodeURIComponent(token)}`
    window.open(url, '_blank')
  }

  const classificationLevels = ['ALL', 'PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'SECRET']

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>
          <div className={styles.spinner}></div>
          กำลังโหลดข้อมูลเอกสาร...
        </div>
      </div>
    )
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>รายการสัญญาทั้งหมด</h2>
        <button className={styles.refreshButton} onClick={onRefresh}>
          รีเฟรช
        </button>
      </div>

      <div className={styles.controls}>
        <input
          type="text"
          placeholder="ค้นหาชื่อสัญญาหรือชื่อไฟล์..."
          className={styles.searchInput}
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value)
            setCurrentPage(1)
          }}
        />
        <div className={styles.filterContainer}>
          <label htmlFor="level-filter">ระดับชั้นความลับ:</label>
          <select
            id="level-filter"
            className={styles.filterSelect}
            value={filterLevel}
            onChange={(e) => {
              setFilterLevel(e.target.value)
              setCurrentPage(1)
            }}
          >
            {classificationLevels.map(level => (
              <option key={level} value={level}>{level}</option>
            ))}
          </select>
        </div>
      </div>

      {paginatedDocuments.length > 0 ? (
        <>
          <div className={styles.tableContainer}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>ชื่อสัญญา</th>
                  <th className={styles.th}>ชื่อไฟล์</th>
                  <th className={styles.th}>ระดับความลับ</th>
                  <th className={styles.th}>จำนวนหน้า</th>
                  <th className={styles.th}>วันที่อัพโหลด</th>
                  <th className={styles.th}>การดำเนินการ</th>
                </tr>
              </thead>
              <tbody>
                {paginatedDocuments.map((doc) => {
                  const level = doc.classification || 'PUBLIC'
                  const color = levelColors[level] || levelColors['DEFAULT']
                  return (
                    <tr key={doc.doc_id} className={styles.tr}>
                      <td className={`${styles.td} ${styles.titleCell}`}>{doc.title}</td>
                      <td className={styles.td}>{doc.filename}</td>
                      <td className={styles.td}>
                        <span className={styles.badge} style={{ backgroundColor: color.bg, color: color.text }}>
                          {level}
                        </span>
                      </td>
                      <td className={styles.td}>{doc.total_pages}</td>
                      <td className={styles.td}>{new Date(doc.upload_date).toLocaleDateString('th-TH')}</td>
                      <td className={styles.td}>
                        <button className={styles.actionButton} onClick={(e) => handleView(e, doc.doc_id)}>ดู</button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <div className={styles.pagination}>
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
            >
              ก่อนหน้า
            </button>
            <span>หน้า {currentPage} จาก {totalPages}</span>
            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
            >
              ถัดไป
            </button>
          </div>
        </>
      ) : (
        <div className={styles.empty}>
          <p>ไม่พบเอกสารที่ตรงกับเงื่อนไขการค้นหา</p>
        </div>
      )}
    </div>
  )
}