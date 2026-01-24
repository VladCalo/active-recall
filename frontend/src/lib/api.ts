/**
 * API Client for Active Recall Backend
 * 
 * This module provides typed functions for all API operations.
 * Uses axios for HTTP requests with consistent error handling.
 * 
 * Authentication:
 * - Access tokens are stored in memory (not localStorage for security)
 * - Refresh tokens are stored in httpOnly cookies (handled by browser)
 * - Automatic token refresh on 401 responses
 */

import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios'

// Base URL for API requests
// In development, Vite proxies /api to the backend
// In production, this should be the backend URL
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

// =============================================================================
// Types
// =============================================================================

export type ScheduleType = 'DEFAULT' | 'CUSTOM'

export interface Subject {
  id: string
  name: string
  start_date: string
  schedule_type: ScheduleType
  custom_intervals_days: number[] | null
  created_at: string
  updated_at: string
  next_due_date: string | null
  intervals: number[]
}

export interface SubjectCreate {
  name: string
  start_date: string
  schedule_type: ScheduleType
  custom_intervals_days?: number[]
}

export interface SubjectUpdate {
  name?: string
  start_date?: string
  schedule_type?: ScheduleType
  custom_intervals_days?: number[]
}

export interface TodayReviewsResponse {
  today: string
  timezone: string
  subjects: Subject[]
  count: number
}

export interface UpcomingReviewsResponse {
  start_date: string
  end_date: string
  timezone: string
  reviews: Record<string, Subject[]>
  total_count: number
}

export interface User {
  id: string
  email: string
  created_at: string
  updated_at: string
  last_login_at: string | null
}

export interface AuthResponse {
  user: User
  access_token: string
  token_type: string
  expires_in: number
}

export interface ApiError {
  detail: string
}

// =============================================================================
// Token Management
// =============================================================================

let accessToken: string | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

export function clearAccessToken(): void {
  accessToken = null
}

// =============================================================================
// Axios Instance Configuration
// =============================================================================

// Create axios instance with default config
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Required for httpOnly cookies
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for token refresh
let isRefreshing = false
let failedQueue: Array<{
  resolve: (value: unknown) => void
  reject: (reason?: unknown) => void
}> = []

const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    
    // Don't try to refresh if this IS the refresh request or auth endpoints
    const isAuthEndpoint = originalRequest.url?.includes('/auth/')
    
    // If 401 and not already retrying and not an auth endpoint, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      if (isRefreshing) {
        // If already refreshing, queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const response = await api.post<AuthResponse>('/auth/refresh')
        const newToken = response.data.access_token
        setAccessToken(newToken)
        processQueue(null, newToken)
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError as Error, null)
        clearAccessToken()
        // Don't redirect here - let the app handle it
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

// =============================================================================
// Error Handling
// =============================================================================

/**
 * Extract error message from API error response.
 */
function getErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    if (error.response?.data?.detail) {
      return error.response.data.detail
    }
    if (error.message) {
      return error.message
    }
  }
  return 'An unexpected error occurred'
}

// =============================================================================
// Auth API Functions
// =============================================================================

/**
 * Register a new user.
 */
export async function register(email: string, password: string): Promise<AuthResponse> {
  try {
    const response = await api.post<AuthResponse>('/auth/register', { email, password })
    setAccessToken(response.data.access_token)
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Log in a user.
 */
export async function login(email: string, password: string): Promise<AuthResponse> {
  try {
    const response = await api.post<AuthResponse>('/auth/login', { email, password })
    setAccessToken(response.data.access_token)
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Log out the current user.
 */
export async function logout(): Promise<void> {
  try {
    await api.post('/auth/logout')
  } finally {
    clearAccessToken()
  }
}

/**
 * Get the current user's profile.
 */
export async function getMe(): Promise<User> {
  const response = await api.get<User>('/auth/me')
  return response.data
}

/**
 * Refresh the access token.
 */
export async function refreshToken(): Promise<AuthResponse> {
  const response = await api.post<AuthResponse>('/auth/refresh')
  setAccessToken(response.data.access_token)
  return response.data
}

// =============================================================================
// Health API Functions
// =============================================================================

/**
 * Health check - verify backend is running.
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await api.get('/health')
    return response.data.ok === true
  } catch {
    return false
  }
}

// =============================================================================
// Subjects API Functions
// =============================================================================

/**
 * Get all subjects.
 */
export async function getSubjects(): Promise<Subject[]> {
  const response = await api.get<Subject[]>('/subjects')
  return response.data
}

/**
 * Get a single subject by ID.
 */
export async function getSubject(id: string): Promise<Subject> {
  const response = await api.get<Subject>(`/subjects/${id}`)
  return response.data
}

/**
 * Create a new subject.
 */
export async function createSubject(data: SubjectCreate): Promise<Subject> {
  try {
    const response = await api.post<Subject>('/subjects', data)
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Update an existing subject.
 */
export async function updateSubject(id: string, data: SubjectUpdate): Promise<Subject> {
  try {
    const response = await api.put<Subject>(`/subjects/${id}`, data)
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Delete a subject.
 */
export async function deleteSubject(id: string): Promise<void> {
  try {
    await api.delete(`/subjects/${id}`)
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

// =============================================================================
// Reviews API Functions
// =============================================================================

/**
 * Get subjects due for review today.
 * 
 * @param timezone - IANA timezone string (default: Europe/Bucharest)
 */
export async function getTodayReviews(timezone = 'Europe/Bucharest'): Promise<TodayReviewsResponse> {
  const response = await api.get<TodayReviewsResponse>('/reviews/today', {
    params: { tz: timezone },
  })
  return response.data
}

/**
 * Get upcoming reviews for the next N days.
 * 
 * @param days - Number of days to look ahead (default: 7)
 * @param timezone - IANA timezone string (default: Europe/Bucharest)
 */
export async function getUpcomingReviews(
  days = 7,
  timezone = 'Europe/Bucharest'
): Promise<UpcomingReviewsResponse> {
  const response = await api.get<UpcomingReviewsResponse>('/reviews/upcoming', {
    params: { days, tz: timezone },
  })
  return response.data
}
