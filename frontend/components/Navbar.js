'use client'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { useEffect, useState } from 'react'

const styles = {
  nav: {
    backgroundColor: '#1e3a8a',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    position: 'sticky',
    top: 0,
    zIndex: 100
  },
  container: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: '0 20px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    height: '70px'
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    textDecoration: 'none',
    color: 'white'
  },
  logoIcon: {
    fontSize: '28px'
  },
  logoText: {
    fontSize: '20px',
    fontWeight: '600',
    fontFamily: 'Prompt, sans-serif'
  },
  menu: {
    display: 'flex',
    gap: '10px',
    listStyle: 'none',
    margin: 0,
    padding: 0
  },
  menuItem: {
    color: 'white',
    textDecoration: 'none',
    padding: '10px 20px',
    borderRadius: '8px',
    transition: 'background-color 0.2s',
    fontFamily: 'Prompt, sans-serif',
    fontSize: '15px',
    fontWeight: '400',
    display: 'inline-block'
  },
  menuItemActive: {
    backgroundColor: 'rgba(255,255,255,0.2)'
  },
  menuItemHover: {
    backgroundColor: 'rgba(255,255,255,0.1)'
  }
}

export default function Navbar() {
  const pathname = usePathname()
  const [authed, setAuthed] = useState(false)
  const [role, setRole] = useState('')
  const [maxLevel, setMaxLevel] = useState('')

  useEffect(()=>{
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('token')
      if (token) {
        setAuthed(true)
        setRole(localStorage.getItem('role')||'')
        setMaxLevel(localStorage.getItem('max_level')||'')
      }
    }
  }, [pathname])

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('role')
    localStorage.removeItem('max_level')
    setAuthed(false)
    window.location.href = '/login'
  }

  const menuItems = [
    { href: '/', label: 'หน้าหลัก', icon: '🏠' },
    ...(authed ? [{ href: '/upload', label: 'อัพโหลด', icon: '📤' }] : []),
    { href: '/chat', label: 'ถาม AI', icon: '💬' },
    ...(authed ? [{ href: '/templates', label: 'เทมเพลต', icon: '📁' }] : []),
    ...(authed && role==='ADMIN' && maxLevel==='SECRET' ? [{ href: '/admin/templates', label: 'เทมเพลตผู้ดูแลระบบ', icon: '🛠️' }] : []),
    ...(authed && role==='ADMIN' && maxLevel==='SECRET' ? [{ href: '/admin/users', label: 'ผู้ใช้', icon: '👤' }] : [])
  ]

  return (
    <nav style={styles.nav}>
      <div style={styles.container}>
        <Link href="/" style={styles.logo}>
          <span style={styles.logoIcon}>📋</span>
          <span style={styles.logoText}>Contract AI System</span>
        </Link>
        
        <ul style={styles.menu}>
          {menuItems.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                style={{
                  ...styles.menuItem,
                  ...(pathname === item.href ? styles.menuItemActive : {})
                }}
                onMouseEnter={(e) => {
                  if (pathname !== item.href) {
                    e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)'
                  }
                }}
                onMouseLeave={(e) => {
                  if (pathname !== item.href) {
                    e.currentTarget.style.backgroundColor = 'transparent'
                  }
                }}
              >
                {item.icon} {item.label}
              </Link>
            </li>
          ))}
          {!authed && (
            <li>
              <Link href="/login" style={{...styles.menuItem, ...(pathname === '/login'? styles.menuItemActive : {})}}>🔐 เข้าสู่ระบบ</Link>
            </li>
          )}
          {authed && (
            <li>
              <span style={{...styles.menuItem, cursor:'pointer'}} onClick={logout}>🚪 ออกจากระบบ</span>
            </li>
          )}
          {authed && (
            <li>
              <span style={{...styles.menuItem, background:'rgba(255,255,255,0.2)'}}>{role} · {maxLevel}</span>
            </li>
          )}
        </ul>
      </div>
    </nav>
  )
}