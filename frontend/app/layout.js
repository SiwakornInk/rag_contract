import { Inter } from 'next/font/google'
import Navbar from '@/components/Navbar'
import './globals.css' // Import the global stylesheet

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'ระบบจัดการสัญญาอัจฉริยะ | Contract AI',
  description: 'ระบบวิเคราะห์และค้นหาข้อมูลสัญญาด้วย AI',
}

export default function RootLayout({ children }) {
  return (
    <html lang="th">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="true" />
        <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body className={inter.className}>
        <Navbar />
        <main>{children}</main>
      </body>
    </html>
  )
}