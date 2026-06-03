"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { BarChart3, AlertTriangle, FileText, User } from "lucide-react"
import { cn } from "@/lib/utils"
import { ThemeToggle } from "@/components/theme-toggle"

const navigation = [
  { name: "Показатели", href: "/", icon: BarChart3 },
  { name: "Предупреждения", href: "/alerts", icon: AlertTriangle },
  { name: "Отчёты", href: "/reports", icon: FileText },
]

interface SidebarProps {
  unreadAlertsCount?: number
}

export function Sidebar({ unreadAlertsCount = 0 }: SidebarProps) {
  const pathname = usePathname()

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-64 flex-col bg-sidebar border-r border-sidebar-border">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-sidebar-border px-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
          <span className="text-lg font-bold text-primary-foreground">И</span>
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold text-sidebar-foreground">ИГИС-БДД</span>
          <span className="text-xs text-muted-foreground">Модуль М10</span>
        </div>
        <ThemeToggle className="ml-auto h-8 w-8" />
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4">
        <ul className="flex flex-col gap-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href
            return (
              <li key={item.name}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
                  )}
                >
                  <item.icon className="h-5 w-5" />
                  <span>{item.name}</span>
                  {item.name === "Предупреждения" && unreadAlertsCount > 0 && (
                    <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-status-critical px-1.5 text-xs font-semibold text-white">
                      {unreadAlertsCount > 99 ? "99+" : unreadAlertsCount}
                    </span>
                  )}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* User info */}
      <div className="border-t border-sidebar-border p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-muted">
            <User className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium text-sidebar-foreground">Якимов Д.С.</span>
            <span className="text-xs text-muted-foreground">Аналитик</span>
          </div>
        </div>
      </div>
    </aside>
  )
}
