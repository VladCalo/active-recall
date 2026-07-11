/**
 * Authentication Context
 * 
 * Provides authentication state and methods throughout the application.
 * Handles login, logout, registration, and session persistence.
 * 
 * Security:
 * - Access tokens stored in memory only (not localStorage)
 * - Refresh tokens in httpOnly cookies (handled by browser)
 * - Automatic token refresh on app load
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import {
  User,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  refreshToken,
  clearAccessToken,
} from '@/lib/api'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>
  register: (email: string, password: string) => Promise<string>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Check for existing session on mount
  useEffect(() => {
    const initAuth = async () => {
      try {
        // Try to refresh the token (uses httpOnly cookie)
        const response = await refreshToken()
        setUser(response.user)
      } catch {
        // No valid session, user needs to log in
        clearAccessToken()
        setUser(null)
      } finally {
        setIsLoading(false)
      }
    }

    initAuth()
  }, [])

  const login = useCallback(async (email: string, password: string, rememberMe: boolean = true) => {
    const response = await apiLogin(email, password, rememberMe)
    setUser(response.user)
  }, [])

  const register = useCallback(async (email: string, password: string) => {
    // Registration no longer logs the user in - new accounts need admin
    // approval first. Return the server's message for the caller to show.
    const response = await apiRegister(email, password)
    return response.message
  }, [])

  const logout = useCallback(async () => {
    try {
      await apiLogout()
    } finally {
      setUser(null)
      clearAccessToken()
    }
  }, [])

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
