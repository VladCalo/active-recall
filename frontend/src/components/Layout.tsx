/**
 * Layout Component
 * 
 * The main application layout with navigation header.
 * Used to wrap all pages with consistent navigation and styling.
 */

import { Link, useLocation } from 'react-router-dom'
import { Brain, LayoutDashboard, BookOpen } from 'lucide-react'
import { cn } from '@/lib/utils'

interface LayoutProps {
  children: React.ReactNode
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation()

  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/subjects', label: 'Subjects', icon: BookOpen },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <header className="sticky top-0 z-40 w-full border-b bg-white/80 backdrop-blur-sm">
        <div className="container flex h-16 items-center justify-between px-4 md:px-6">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 font-semibold">
            <Brain className="h-6 w-6 text-primary" />
            <span className="hidden sm:inline-block text-lg">Active Recall</span>
          </Link>

          {/* Navigation */}
          <nav className="flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.path
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={cn(
                    "flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                    isActive 
                      ? "bg-primary/10 text-primary" 
                      : "text-muted-foreground hover:bg-slate-100 hover:text-foreground"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span className="hidden sm:inline-block">{item.label}</span>
                </Link>
              )
            })}
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="container px-4 py-6 md:px-6 md:py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t bg-white/50 py-6 mt-auto">
        <div className="container px-4 md:px-6">
          <p className="text-center text-sm text-muted-foreground">
            Active Recall Monitor — Track your study subjects with spaced repetition
          </p>
        </div>
      </footer>
    </div>
  )
}
