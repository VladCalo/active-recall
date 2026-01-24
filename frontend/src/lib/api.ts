/**
 * API Client for Active Recall Backend
 * 
 * This module provides typed functions for all API operations.
 * Uses axios for HTTP requests with consistent error handling.
 */

import axios, { AxiosError } from 'axios'

// Base URL for API requests
// In development, Vite proxies /api to the backend
// In production, this should be the backend URL
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

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

export interface ApiError {
  detail: string
}

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
// API Functions
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
