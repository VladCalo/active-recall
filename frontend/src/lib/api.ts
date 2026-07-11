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
const API_BASE_URL = import.meta.env.VITE_API_URL || `${import.meta.env.BASE_URL.replace(/\/$/, '')}/api`

// =============================================================================
// Types
// =============================================================================

export type Category = 'HARD' | 'MEDIUM' | 'EASY'
export type Rating = 'MAJOR_GAPS' | 'MANY_CONFUSIONS' | 'GOOD_MINOR_HESITATION' | 'EXCELLENT'

export interface Subject {
  id: string
  name: string
  start_date: string
  category: Category
  stage: number
  next_due_date: string | null
  last_active_recall_date: string | null
  total_active_recall_count: number
  is_final_recall_reached: boolean
  final_active_recall_date: string | null
  final_category: Category | null
  reread_completed_at: string | null
  created_at: string
  updated_at: string
}

export interface SubjectCreate {
  name: string
  start_date: string
}

export interface SubjectUpdate {
  name?: string
  start_date?: string
}

export interface DueItem {
  subject_id: string
  subject_name: string
  category: Category
  stage: number
  due_date: string
  is_overdue: boolean
}

export interface TodayReviewsResponse {
  today: string
  timezone: string
  items: DueItem[]
  count: number
}

export interface CompleteReviewResponse {
  subject_id: string
  category: Category
  stage: number
  next_due_date: string | null
  is_final_recall: boolean
  banner_message: string | null
}

export interface CalendarItem {
  subject_id: string
  subject_name: string
  type: 'upcoming' | 'completed'
  category: Category
  rating: Rating | null
}

export interface RangeReviewsResponse {
  timezone: string
  start: string
  end: string
  items: Record<string, CalendarItem[]>
  total_count: number
}

export interface ReferenceModeChapter {
  subject_id: string
  subject_name: string
  last_active_recall_date: string | null
  final_category: Category
  total_active_recall_count: number
  recommended_intensity_label: string
  recommended_focus: string[]
  reread_completed: boolean
  reread_completed_at: string | null
}

export interface ReferenceModeListResponse {
  is_reference_mode: boolean
  cutoff_date: string
  chapters: ReferenceModeChapter[]
}

export interface ReferenceModeSummary {
  is_reference_mode: boolean
  chapters_completed: number
  chapters_remaining: number
  percentage_completed: number
  days_remaining_until_exam: number
  exam_date: string
}

export interface ExamSettings {
  exam_date: string
  final_recall_cutoff_date: string
  reference_mode_end_date: string
}

export interface User {
  id: string
  email: string
  is_admin: boolean
  created_at: string
  updated_at: string
  last_login_at: string | null
}

// Admin types
export interface AdminStats {
  total_users: number
  total_subjects: number
  admin_count: number
  disabled_users: number
  active_users_last_7_days: number
  subjects_created_last_7_days: number
  reviews_due_today_total: number
  reviews_due_next_7_days_total: number
}

export interface AdminUserListItem {
  id: string
  email: string
  is_admin: boolean
  is_disabled: boolean
  created_at: string | null
  last_login_at: string | null
  subject_count: number
}

export interface AdminUserListResponse {
  users: AdminUserListItem[]
  total: number
  skip: number
  limit: number
}

export interface AdminSubjectSummary {
  id: string
  name: string
  start_date: string
  category: string
}

export interface AdminUserDetail {
  id: string
  email: string
  is_admin: boolean
  is_disabled: boolean
  failed_login_attempts: number
  locked_until: string | null
  created_at: string | null
  updated_at: string | null
  last_login_at: string | null
  subject_count: number
  subjects: AdminSubjectSummary[]
}

export interface AdminTrafficStats {
  period_hours: number
  request_count_total: number
  requests_by_route: Record<string, number>
  status_code_counts: Record<string, number>
  avg_latency_ms: number
  p95_latency_ms: number
  requests_per_minute: number
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
      const detail = error.response.data.detail
      return typeof detail === 'string' ? detail : JSON.stringify(detail)
    }
    if (error.response?.status === 429) {
      return 'Too many requests. Please try again later.'
    }
    // Network error, CORS, or no response (e.g. backend unreachable)
    if (!error.response && error.message) {
      if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
        return 'Cannot reach the server. Check that the backend is running and CORS allows this origin.'
      }
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

export async function completeReview(
  subjectId: string,
  rating: Rating,
  completedAt?: string
): Promise<CompleteReviewResponse> {
  try {
    const response = await api.post<CompleteReviewResponse>('/reviews/complete', {
      subject_id: subjectId,
      rating,
      completed_at: completedAt,
    })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

// =============================================================================
// Reference Mode API Functions
// =============================================================================

export async function getReferenceMode(): Promise<ReferenceModeListResponse> {
  const response = await api.get<ReferenceModeListResponse>('/reference-mode')
  return response.data
}

export async function getReferenceModeSummary(): Promise<ReferenceModeSummary> {
  const response = await api.get<ReferenceModeSummary>('/reference-mode/summary')
  return response.data
}

export async function completeReread(subjectId: string): Promise<ReferenceModeChapter> {
  try {
    const response = await api.post<ReferenceModeChapter>(`/reference-mode/${subjectId}/complete-reread`)
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

// =============================================================================
// Settings API Functions
// =============================================================================

export async function getExamSettings(): Promise<ExamSettings> {
  const response = await api.get<ExamSettings>('/settings')
  return response.data
}

export async function updateExamSettings(examDate: string): Promise<ExamSettings> {
  try {
    const response = await api.put<ExamSettings>('/settings', { exam_date: examDate })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

// =============================================================================
// Admin API Functions
// =============================================================================

export async function getAdminStats(): Promise<AdminStats> {
  const response = await api.get<AdminStats>('/admin/stats')
  return response.data
}

export async function getAdminUsers(
  skip = 0,
  limit = 20,
  search?: string
): Promise<AdminUserListResponse> {
  const response = await api.get<AdminUserListResponse>('/admin/users', {
    params: { skip, limit, search: search || undefined },
  })
  return response.data
}

export async function getAdminUserDetail(userId: string): Promise<AdminUserDetail> {
  const response = await api.get<AdminUserDetail>(`/admin/users/${userId}`)
  return response.data
}

export async function updateAdminUser(
  userId: string,
  data: { is_admin?: boolean; is_disabled?: boolean }
): Promise<AdminUserDetail> {
  try {
    const response = await api.patch<AdminUserDetail>(`/admin/users/${userId}`, data)
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

export async function deleteAdminUser(userId: string): Promise<void> {
  try {
    await api.delete(`/admin/users/${userId}`, {
      headers: { 'X-Admin-Confirm': 'DELETE' },
    })
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

export async function getAdminTraffic(hours = 24): Promise<AdminTrafficStats> {
  const response = await api.get<AdminTrafficStats>('/admin/traffic', {
    params: { hours },
  })
  return response.data
}
