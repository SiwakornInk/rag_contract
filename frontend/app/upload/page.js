'use client'
import { useState } from 'react'
import { uploadDocument } from '@/utils/api'
import { useRouter } from 'next/navigation'

const styles = {
  container: {
    maxWidth: '800px',
    margin: '0 auto',
    padding: '40px 20px'
  },
  card: {
    backgroundColor: 'white',
    borderRadius: '12px',
    padding: '40px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
  },
  title: {
    fontSize: '28px',
    fontWeight: '600',
    color: '#1e3a8a',
    marginBottom: '30px',
    fontFamily: 'Prompt, sans-serif'
  },
  uploadArea: {
    border: '2px dashed #cbd5e1',
    borderRadius: '12px',
    padding: '60px 20px',
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all 0.3s',
    backgroundColor: '#f8fafc'
  },
  uploadAreaActive: {
    borderColor: '#1e3a8a',
    backgroundColor: '#eff6ff'
  },
  uploadIcon: {
    fontSize: '48px',
    marginBottom: '20px'
  },
  uploadText: {
    fontSize: '18px',
    color: '#475569',
    marginBottom: '10px',
    fontFamily: 'Prompt, sans-serif'
  },
  uploadSubtext: {
    fontSize: '14px',
    color: '#94a3b8'
  },
  fileInput: {
    display: 'none'
  },
  selectedFile: {
    marginTop: '20px',
    padding: '15px',
    backgroundColor: '#f1f5f9',
    borderRadius: '8px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  fileName: {
    color: '#334155',
    fontWeight: '500',
    display: 'flex',
    alignItems: 'center',
    gap: '10px'
  },
  fileSize: {
    fontSize: '12px',
    color: '#64748b'
  },
  removeButton: {
    color: '#ef4444',
    cursor: 'pointer',
    fontSize: '20px'
  },
  ocrOption: {
    marginTop: '30px',
    padding: '20px',
    backgroundColor: '#f8fafc',
    borderRadius: '8px'
  },
  ocrTitle: {
    fontSize: '16px',
    fontWeight: '500',
    marginBottom: '15px',
    color: '#334155',
    fontFamily: 'Prompt, sans-serif'
  },
  radioGroup: {
    display: 'flex',
    gap: '30px'
  },
  radioLabel: {
    display: 'flex',
    alignItems: 'center',
    cursor: 'pointer',
    fontFamily: 'Prompt, sans-serif'
  },
  radioInput: {
    marginRight: '8px',
    cursor: 'pointer'
  },
  uploadButton: {
    width: '100%',
    marginTop: '30px',
    padding: '14px',
    backgroundColor: '#1e3a8a',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
    fontFamily: 'Prompt, sans-serif'
  },
  uploadButtonDisabled: {
    backgroundColor: '#94a3b8',
    cursor: 'not-allowed'
  },
  progress: {
    marginTop: '20px',
    padding: '20px',
    backgroundColor: '#eff6ff',
    borderRadius: '8px',
    textAlign: 'center'
  },
  progressText: {
    color: '#1e3a8a',
    marginBottom: '10px',
    fontFamily: 'Prompt, sans-serif'
  },
  progressBar: {
    width: '100%',
    height: '8px',
    backgroundColor: '#cbd5e1',
    borderRadius: '4px',
    overflow: 'hidden'
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#1e3a8a',
    transition: 'width 0.3s'
  },
  success: {
    marginTop: '20px',
    padding: '20px',
    backgroundColor: '#d1fae5',
    borderRadius: '8px',
    color: '#065f46',
    fontFamily: 'Prompt, sans-serif'
  },
  warning: {
    marginTop: '10px',
    padding: '15px',
    backgroundColor: '#fef3c7',
    borderRadius: '8px',
    color: '#92400e',
    fontSize: '14px',
    fontFamily: 'Prompt, sans-serif'
  },
  error: {
    marginTop: '20px',
    padding: '20px',
    backgroundColor: '#fee2e2',
    borderRadius: '8px',
    color: '#991b1b',
    fontFamily: 'Prompt, sans-serif'
  }
}

export default function UploadPage() {
  const [file, setFile] = useState(null)
  const [useCloudOCR, setUseCloudOCR] = useState(true)
  const [classification, setClassification] = useState('PUBLIC')
  const [role, setRole] = useState('')
  const [maxLevel, setMaxLevel] = useState('')
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const router = useRouter()

  const handleDragEnter = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile && droppedFile.type === 'application/pdf') {
      setFile(droppedFile)
      setError(null)
    } else {
      setError('กรุณาเลือกไฟล์ PDF เท่านั้น')
    }
  }

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      // ตรวจสอบขนาดไฟล์ (50 MB)
      if (selectedFile.size > 50 * 1024 * 1024) {
        setError('ไฟล์มีขนาดใหญ่เกิน 50 MB')
        return
      }
      setFile(selectedFile)
      setError(null)
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const handleUpload = async () => {
    if (!file) return

    setUploading(true)
    setProgress(0)
    setError(null)
    setResult(null)

    const interval = setInterval(() => {
      setProgress(prev => Math.min(prev + 10, 90))
    }, 500)

    try {
  const response = await uploadDocument(file, useCloudOCR, classification)
      clearInterval(interval)
      setProgress(100)
      setResult(response)
      
      setTimeout(() => {
        router.push('/')
      }, 3000)
    } catch (err) {
      clearInterval(interval)
      setError(err.response?.data?.detail || 'เกิดข้อผิดพลาดในการอัพโหลด')
      setProgress(0)
    } finally {
      setUploading(false)
    }
  }

  // Check auth
  if (typeof window !== 'undefined' && !localStorage.getItem('token')) {
    if (typeof window !== 'undefined') window.location.href = '/login'
    return null
  }
  if (typeof window !== 'undefined' && !role) {
    setRole(localStorage.getItem('role')||'')
    setMaxLevel(localStorage.getItem('max_level')||'')
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>📤 อัพโหลดสัญญา</h1>
        
        <div
          style={{
            ...styles.uploadArea,
            ...(isDragging ? styles.uploadAreaActive : {})
          }}
          onDragEnter={handleDragEnter}
          onDragOver={(e) => e.preventDefault()}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => document.getElementById('fileInput').click()}
        >
          <div style={styles.uploadIcon}>📄</div>
          <div style={styles.uploadText}>
            ลากไฟล์มาวางที่นี่ หรือคลิกเพื่อเลือกไฟล์
          </div>
          <div style={styles.uploadSubtext}>
            รองรับไฟล์ PDF ขนาดไม่เกิน 50 MB
          </div>
          <input
            id="fileInput"
            type="file"
            accept=".pdf"
            onChange={handleFileSelect}
            style={styles.fileInput}
          />
        </div>

        {file && (
          <div style={styles.selectedFile}>
            <div style={styles.fileName}>
              <span>📎 {file.name}</span>
              <span style={styles.fileSize}>({formatFileSize(file.size)})</span>
            </div>
            <span
              style={styles.removeButton}
              onClick={() => setFile(null)}
            >
              ✕
            </span>
          </div>
        )}

  <div style={styles.ocrOption}>
          <div style={styles.ocrTitle}>เลือกวิธีการสกัดข้อความ (OCR)</div>
          <div style={styles.radioGroup}>
            <label style={styles.radioLabel}>
              <input
                type="radio"
                name="ocr"
                checked={useCloudOCR}
                onChange={() => setUseCloudOCR(true)}
                style={styles.radioInput}
              />
              Cloud OCR (Google Vision) - แม่นยำสูง
            </label>
            <label style={styles.radioLabel}>
              <input
                type="radio"
                name="ocr"
                checked={!useCloudOCR}
                onChange={() => setUseCloudOCR(false)}
                style={styles.radioInput}
              />
              Local OCR (EasyOCR) - เร็วกว่า
            </label>
          </div>
        </div>

        {maxLevel === 'SECRET' && (
          <div style={styles.ocrOption}>
            <div style={styles.ocrTitle}>ระดับการจัดประเภท (Classification)</div>
            <select
              value={classification}
              onChange={e=>setClassification(e.target.value)}
              style={{ padding:'10px', border:'1px solid #cbd5e1', borderRadius:'6px', fontFamily:'Prompt, sans-serif'}}>
              <option value="PUBLIC">Public</option>
              <option value="INTERNAL">Internal</option>
              <option value="CONFIDENTIAL">Confidential</option>
              <option value="SECRET">Secret</option>
            </select>
          </div>
        )}

        {maxLevel !== 'SECRET' && (
          <div style={{...styles.warning, background:'#e2e8f0', color:'#475569'}}>
            คุณมีสิทธิ์อัพโหลดเฉพาะผู้ใช้ระดับสูงสุด (SECRET) เท่านั้น – เข้าสู่ระบบด้วยบัญชีที่มีสิทธิ์เพื่ออัพโหลด
          </div>
        )}

        <button
          style={{
            ...styles.uploadButton,
            ...((!file || uploading || maxLevel !== 'SECRET') ? styles.uploadButtonDisabled : {})
          }}
          onClick={handleUpload}
          disabled={!file || uploading || maxLevel !== 'SECRET'}
        >
          {uploading ? 'กำลังอัพโหลด...' : 'อัพโหลดเอกสาร'}
        </button>

        {uploading && (
          <div style={styles.progress}>
            <div style={styles.progressText}>กำลังประมวลผล... {progress}%</div>
            <div style={styles.progressBar}>
              <div style={{...styles.progressFill, width: `${progress}%`}}></div>
            </div>
          </div>
        )}

        {result && (
          <>
            <div style={styles.success}>
              ✅ อัพโหลดสำเร็จ! เอกสาร "{result.title}" ได้ถูกบันทึกแล้ว
              <br />จำนวน {result.total_chunks} ส่วน | {result.extraction_stats?.total_pages || 0} หน้า
              {result.ocr_mode && (
                <>
                  <br />ใช้ {result.ocr_mode === 'cloud' ? 'Cloud OCR' : 'Local OCR'}
                </>
              )}
              <br />กำลังกลับไปหน้าหลัก...
            </div>
            {result.warnings && result.warnings.length > 0 && (
              <div style={styles.warning}>
                ⚠️ คำเตือน:
                {result.warnings.map((warning, idx) => (
                  <div key={idx}>• {warning}</div>
                ))}
              </div>
            )}
          </>
        )}

        {error && (
          <div style={styles.error}>
            ❌ {error}
          </div>
        )}
      </div>
    </div>
  )
}