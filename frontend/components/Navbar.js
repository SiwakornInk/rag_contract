'use client'
import { usePathname, useRouter } from 'next/navigation'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import styles from './Navbar.module.css' // Import CSS module

// Function to get initials from a name
const getInitials = (name) => {
  if (!name) return '?'
  return name.charAt(0).toUpperCase()
}

export default function Navbar() {
  const pathname = usePathname()
  const router = useRouter()
  const [authed, setAuthed] = useState(false)
  const [role, setRole] = useState('')
  const [maxLevel, setMaxLevel] = useState('')
  const [username, setUsername] = useState('')
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!mounted) return
    const token = localStorage.getItem('token')
    if (token) {
      setAuthed(true)
      setRole(localStorage.getItem('role') || '')
      setMaxLevel(localStorage.getItem('max_level') || '')
      setUsername(localStorage.getItem('username') || '')
    } else {
      setAuthed(false)
      setRole('')
      setMaxLevel('')
      setUsername('')
    }
  }, [mounted, pathname])

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('role')
    localStorage.removeItem('max_level')
    localStorage.removeItem('username')
    setAuthed(false)
    router.replace('/login')
  }

  const menuItems = [
    { href: '/', label: 'หน้าหลัก' },
    ...(authed ? [{ href: '/upload', label: 'อัพโหลด' }] : []),
    { href: '/chat', label: 'ถาม AI' },
    ...(authed ? [{ href: '/templates', label: 'เทมเพลต' }] : []),
    ...(authed && role === 'ADMIN' && maxLevel === 'SECRET' ? [{ href: '/admin/templates', label: 'จัดการเทมเพลต' }] : []),
    ...(authed && role === 'ADMIN' && maxLevel === 'SECRET' ? [{ href: '/admin/users', label: 'จัดการผู้ใช้' }] : [])
  ]

  return (
    <nav className={styles.nav}>
      <div className={styles.container}>
        <Link href="/" className={styles.logo}>
          <span className={styles.logoText}>Contract AI SYSTEM</span>
        </Link>
        
        <ul className={styles.menu}>
          {menuItems.map((item) => (
            <li key={item.href}>
              <Link href={item.href} className={`${styles.menuItem} ${pathname === item.href ? styles.menuItemActive : ''}`}>
                {item.label}
              </Link>
            </li>
          ))}
        </ul>

        <div className={styles.userMenu}>
          {!mounted ? null : !authed ? (
            <Link href="/login" className={styles.loginButton}>
              เข้าสู่ระบบ
            </Link>
          ) : (
            <>
              <div className={styles.userInfo}>
                <div className={styles.userAvatar}>{getInitials(username)}</div>
                <div className={styles.userDetails}>
                  <span className={styles.username}>{username}</span>
                  <span className={styles.userRole}>{role} · {maxLevel}</span>
                </div>
              </div>
              <button onClick={logout} className={styles.logoutButton}>
                ออกจากระบบ
              </button>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}