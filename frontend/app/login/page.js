"use client"
import { useState, useEffect } from 'react'
import { login, getMe } from '@/utils/api'
import { useRouter } from 'next/navigation'

const styles = {
  container: { maxWidth: '400px', margin: '60px auto', background: 'white', padding: '40px', borderRadius: '12px', boxShadow: '0 4px 14px rgba(0,0,0,0.08)', fontFamily: 'Prompt, sans-serif' },
  title: { fontSize: '26px', fontWeight: '600', color: '#1e3a8a', marginBottom: '25px', textAlign: 'center' },
  field: { marginBottom: '18px' },
  label: { display: 'block', fontSize: '14px', color: '#475569', marginBottom: '6px' },
  input: { width: '100%', padding: '12px 14px', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '14px' },
  button: { width: '100%', padding: '14px', background: '#1e3a8a', color: 'white', border: 'none', borderRadius: '8px', fontSize: '15px', fontWeight: '500', cursor: 'pointer', marginTop: '5px' },
  error: { background: '#fee2e2', color: '#991b1b', padding: '12px', borderRadius: '8px', fontSize: '13px', marginBottom: '10px' },
  info: { background: '#eff6ff', color: '#1e3a8a', padding: '12px', borderRadius: '8px', fontSize: '13px', marginBottom: '10px' }
}

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const router = useRouter()

  useEffect(() => {
    const check = async () => {
      try { await getMe(); router.push('/'); } catch(_){}
    }
    check()
  }, [router])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(''); setInfo(''); setLoading(true)
    try {
      const res = await login(username, password)
      localStorage.setItem('token', res.access_token)
      localStorage.setItem('role', res.role)
      localStorage.setItem('max_level', res.max_level)
      setInfo('เข้าสู่ระบบสำเร็จ กำลังเปลี่ยนหน้า...')
      setTimeout(()=> router.push('/'), 800)
    } catch (err) {
      setError(err.response?.data?.detail || 'เข้าสู่ระบบไม่สำเร็จ')
    } finally { setLoading(false) }
  }

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>🔐 Login</h1>
      {error && <div style={styles.error}>❌ {error}</div>}
      {info && <div style={styles.info}>✅ {info}</div>}
      <form onSubmit={handleSubmit}>
        <div style={styles.field}>
          <label style={styles.label}>Username</label>
          <input style={styles.input} value={username} onChange={e=>setUsername(e.target.value)} autoComplete="username"/>
        </div>
        <div style={styles.field}>
          <label style={styles.label}>Password</label>
          <input type="password" style={styles.input} value={password} onChange={e=>setPassword(e.target.value)} autoComplete="current-password"/>
        </div>
        <button style={styles.button} disabled={loading}>{loading? 'กำลังตรวจสอบ...' : 'เข้าสู่ระบบ'}</button>
      </form>
      <div style={{marginTop:'18px', fontSize:'12px', color:'#64748b', textAlign:'center'}}>Default admin: admin / Admin123!</div>
    </div>
  )
}