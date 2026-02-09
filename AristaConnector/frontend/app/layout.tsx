import type { Metadata } from 'next'
import './globals.css'
import Navigation from './components/Navigation'
import { ToastProvider } from './components/feedback/ToastProvider'

export const metadata: Metadata = {
  title: 'Arista Monitor Console',
  description: 'Modern light monitoring console for Arista vEOS fleet',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-TW">
      <body className="font-body text-slate-900">
        <ToastProvider>
          <Navigation />
          {children}
        </ToastProvider>
      </body>
    </html>
  )
}
