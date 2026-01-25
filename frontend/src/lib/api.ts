/**
 * API Client for Active Recall Backend
 * 
 * This module provides typed functions for all API operations.
 * Uses axios for HTTP requests with consistent error handling.
 * 
 * Security:
 * - Access tokens stored in memory only (not localStorage)
 * - Refresh tokens in httpOnly cookies (handled by browser)
 * - Automatic token refresh on 401 responses
 * - Rate limit handling with retry-after support
 */

import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios'

// Base URL for API requests
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

export interface CalendarSubject {
  subject_id: string
  subject_name: string
  start_date: string
  schedule_type: ScheduleType
}

export interface RangeReviewsResponse {
  timezone: string
  start: string
  end: string
  items: Record<string, CalendarSubject[]>
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
  retry_after?: number
}

// Custom error class for rate limiting
export class RateLimitError extends Error {
  retryAfter: number
  
  constructor(message: string, retryAfter: number) {
    super(message)
    this.name = 'RateLimitError'
    this.retryAfter = retryAfter
  }
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

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Required for httpOnly cookies
  timeout: 30000, // 30 second timeout
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

// Response interceptor for token refresh and error handling
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
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    
    // Handle rate limiting (429)
    if (error.response?.status === 429) {
      const retryAfter = parseInt(error.response.headers['retry-after'] || '60', 10)
      const message = error.response.data?.detail || 'Too many requests. Please try again later.'
      return Promise.reject(new RateLimitError(message, retryAfter))
    }
    
    // Don't try to refresh if this IS the refresh request or other auth endpoints
    const isAuthEndpoint = originalRequest.url?.includes('/auth/')
    
    // If 401 and not already retrying and not an auth endpoint, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      if (isRefreshing) {
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

function getErrorMessage(error: unknown): string {
  if (error instanceof RateLimitError) {
    return error.message
  }
  if (error instanceof AxiosError) {
    if (error.response?.data?.detail) {
      return error.response.data.detail
    }
    if (error.response?.status === 429) {
      return 'Too many requests. Please try again later.'
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

export async function register(email: string, password: string): Promise<AuthResponse> {
  try {
    const response = await api.post<AuthResponse>('/auth/register', { email, password })
    setAccessToken(response.data.access_token)
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

export async function login(email: string, password: string, rememberMe: boolean = true): Promise<AuthResponse> {
  try {
    const response = await api.post<AuthResponse>('/auth/login', { email, password, remember_me: rememberMe })
    setAccessToken(response.data.access_token)
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

export async function logout(): Promise<void> {
  try {
    await api.post('/auth/logout')
  } finally {
    clearAccessToken()
  }
}

export async function getMe(): Promise<User> {
  const response = await api.get<User>('/auth/me')
  return response.data
}

export async function refreshToken(): Promise<AuthResponse> {
  const response = await api.post<AuthResponse>('/auth/refresh')
  setAccessToken(response.data.access_token)
  return response.data
}

// =============================================================================
// Health API Functions
// =============================================================================

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

export async function getSubjects(): Promise<Subject[]> {
  const response = await api.get<Subject[]>('/subjects')
  return response.data
}

export async function getSubject(id: string): Promise<Subject> {
  const response = await api.get<Subject>(`/subjects/${id}`)
  return response.data
}

export async function createSubject(data: SubjectCreate): Promise<Subject> {
  try {
    const response = await api.post<Subject>('/subjects', data)
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

export async function updateSubject(id: string, data: SubjectUpdate): Promise<Subject> {
  try {
    const response = await api.put<Subject>(`/subjects/${id}`, data)
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

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

export async function getTodayReviews(timezone = 'Europe/Bucharest'): Promise<TodayReviewsResponse> {
  const response = await api.get<TodayReviewsResponse>('/reviews/today', {
    params: { tz: timezone },
  })
  return response.data
}

export async function getUpcomingReviews(
  days = 7,
  timezone = 'Europe/Bucharest'
): Promise<UpcomingReviewsResponse> {
  const response = await api.get<UpcomingReviewsResponse>('/reviews/upcoming', {
    params: { days, tz: timezone },
  })
  return response.data
}

export async function getReviewsInRange(
  start: string,
  end: string,
  timezone = 'Europe/Bucharest'
): Promise<RangeReviewsResponse> {
  const response = await api.get<RangeReviewsResponse>('/reviews/range', {
    params: { start, end, tz: timezone },
  })
  return response.data
}
