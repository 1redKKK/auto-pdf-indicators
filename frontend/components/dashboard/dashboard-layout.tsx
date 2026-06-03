"use client"

import { Sidebar } from "./sidebar"

interface DashboardLayoutProps {
  children: React.ReactNode
  unreadAlertsCount?: number
}

export function DashboardLayout({ children, unreadAlertsCount = 0 }: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      <Sidebar unreadAlertsCount={unreadAlertsCount} />
      <main className="ml-64 min-h-screen">
        {children}
      </main>
    </div>
  )
}
