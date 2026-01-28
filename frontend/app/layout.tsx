import './globals.css'
import type { Metadata } from 'next'
import Analytics from './Analytics'

export const metadata: Metadata = {
  title: 'Jet Lag Planner',
  description: 'Compute and visualize jet lag timetables',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap" rel="stylesheet" />
      </head>
      <body>
        <Analytics />
        {children}
      </body>
    </html>
  )
}
