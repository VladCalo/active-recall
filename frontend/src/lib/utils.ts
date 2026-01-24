/**
 * Utility functions for the application.
 * 
 * This module provides helper functions used throughout the app,
 * including the cn() function for merging Tailwind classes.
 */

import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * Merge class names with Tailwind CSS conflict resolution.
 * 
 * Uses clsx for conditional classes and tailwind-merge to handle
 * conflicting Tailwind utility classes.
 * 
 * @example
 * cn("px-2 py-1", condition && "bg-red-500", "px-4")
 * // Returns "py-1 px-4 bg-red-500" if condition is true
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format a date as a human-readable string.
 * 
 * @param date - Date string or Date object
 * @returns Formatted date string (e.g., "Jan 25, 2026")
 */
export function formatDate(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

/**
 * Format intervals as a readable string.
 * 
 * @param intervals - Array of interval days
 * @returns Formatted string (e.g., "1, 3, 7, 14...")
 */
export function formatIntervals(intervals: number[]): string {
  if (intervals.length <= 4) {
    return intervals.join(', ')
  }
  return `${intervals.slice(0, 3).join(', ')}... +${intervals.length - 3} more`
}

/**
 * Parse a comma-separated string into an array of numbers.
 * 
 * @param input - Comma-separated string (e.g., "1, 3, 7")
 * @returns Array of positive integers, or null if invalid
 */
export function parseIntervals(input: string): number[] | null {
  if (!input.trim()) return null
  
  const parts = input.split(',').map(s => s.trim()).filter(s => s)
  const numbers: number[] = []
  
  for (const part of parts) {
    const num = parseInt(part, 10)
    if (isNaN(num) || num <= 0 || !Number.isInteger(num)) {
      return null
    }
    numbers.push(num)
  }
  
  // Remove duplicates and sort
  const unique = [...new Set(numbers)].sort((a, b) => a - b)
  
  if (unique.length === 0) return null
  return unique
}
