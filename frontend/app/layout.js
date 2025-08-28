import { Inter } from 'next/font/google'
import Navbar from '@/components/Navbar'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'ระบบจัดการสัญญาอัจฉริยะ | Contract AI',
  description: 'ระบบวิเคราะห์และค้นหาข้อมูลสัญญาด้วย AI',
}

const styles = {
  html: {
    height: '100%'
  },
  body: {
    margin: 0,
    padding: 0,
    fontFamily: 'Inter, Prompt, sans-serif',
    backgroundColor: '#f8f9fa',
    minHeight: '100vh',
    color: '#1a202c'
  }
}

export default function RootLayout({ children }) {
  return (
    <html lang="th" style={styles.html}>
      <head>
        <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body className={inter.className} style={styles.body}>
        <Navbar />
        {children}
      </body>
    </html>
  )
}