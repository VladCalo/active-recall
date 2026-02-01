/**
 * Calendar Page
 * 
 * Displays upcoming review due dates in a calendar view.
 * Features:
 * - Month grid view with day navigation
 * - Agenda/list view alternative
 * - Subject filtering
 * - Responsive design for mobile/desktop
 */

import { useEffect, useState, useMemo, useCallback } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  CalendarDays,
  List,
  Search,
  X,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  getReviewsInRange,
  completeReviewEvent,
  type RangeReviewsResponse,
  type CalendarSubject,
} from '@/lib/api'
import { cn } from '@/lib/utils'

type ViewMode = 'month' | 'agenda'

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
]

/**
 * Format subject name with revision number.
 */
function formatSubjectWithRevision(subject: CalendarSubject): string {
  return `${subject.subject_name} ${subject.revision_number}`
}

/**
 * Generate a stable color for a subject based on its ID.
 * Returns a subtle background color class.
 */
function getSubjectColor(subjectId: string): string {
  const colors = [
    'bg-blue-100 text-blue-800 border-blue-200',
    'bg-green-100 text-green-800 border-green-200',
    'bg-purple-100 text-purple-800 border-purple-200',
    'bg-orange-100 text-orange-800 border-orange-200',
    'bg-pink-100 text-pink-800 border-pink-200',
    'bg-teal-100 text-teal-800 border-teal-200',
    'bg-indigo-100 text-indigo-800 border-indigo-200',
    'bg-amber-100 text-amber-800 border-amber-200',
  ]
  
  // Simple hash from subject ID
  let hash = 0
  for (let i = 0; i < subjectId.length; i++) {
    hash = ((hash << 5) - hash) + subjectId.charCodeAt(i)
    hash = hash & hash
  }
  
  return colors[Math.abs(hash) % colors.length]
}

/**
 * Get calendar grid data for a given month.
 * Returns array of weeks, each containing 7 day objects.
 */
function getCalendarDays(year: number, month: number): Array<Array<{
  date: Date
  isCurrentMonth: boolean
  isToday: boolean
}>> {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  
  const startDate = new Date(firstDay)
  startDate.setDate(startDate.getDate() - startDate.getDay())
  
  const endDate = new Date(lastDay)
  endDate.setDate(endDate.getDate() + (6 - endDate.getDay()))
  
  const weeks: Array<Array<{ date: Date; isCurrentMonth: boolean; isToday: boolean }>> = []
  let currentDate = new Date(startDate)
  
  while (currentDate <= endDate) {
    const week: Array<{ date: Date; isCurrentMonth: boolean; isToday: boolean }> = []
    
    for (let i = 0; i < 7; i++) {
      week.push({
        date: new Date(currentDate),
        isCurrentMonth: currentDate.getMonth() === month,
        isToday: currentDate.getTime() === today.getTime(),
      })
      currentDate.setDate(currentDate.getDate() + 1)
    }
    
    weeks.push(week)
  }
  
  return weeks
}

/**
 * Format date as YYYY-MM-DD for API.
 */
function formatDateKey(date: Date): string {
  return date.toISOString().split('T')[0]
}

/**
 * Format date for display.
 */
function formatDisplayDate(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00')
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
}

export function Calendar() {
  const [currentDate, setCurrentDate] = useState(() => new Date())
  const [viewMode, setViewMode] = useState<ViewMode>('month')
  const [searchQuery, setSearchQuery] = useState('')
  const [data, setData] = useState<RangeReviewsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedDay, setSelectedDay] = useState<string | null>(null)
  
  const year = currentDate.getFullYear()
  const month = currentDate.getMonth()
  
  // Calculate date range for current view (including overflow days)
  const calendarDays = useMemo(() => getCalendarDays(year, month), [year, month])
  
  const dateRange = useMemo(() => {
    const firstDay = calendarDays[0][0].date
    const lastWeek = calendarDays[calendarDays.length - 1]
    const lastDay = lastWeek[lastWeek.length - 1].date
    
    return {
      start: formatDateKey(firstDay),
      end: formatDateKey(lastDay),
    }
  }, [calendarDays])
  
  // Fetch reviews for current range
  const fetchReviews = useCallback(async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await getReviewsInRange(
        dateRange.start,
        dateRange.end,
        'Europe/Bucharest'
      )
      setData(response)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load calendar'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [dateRange])

  const handleToggleComplete = useCallback(
    async (event: CalendarSubject) => {
      try {
        await completeReviewEvent(event.subject_id, event.due_date, !event.is_completed)
        fetchReviews()
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update event'
        setError(message)
      }
    },
    [fetchReviews]
  )
  
  useEffect(() => {
    fetchReviews()
  }, [fetchReviews])
  
  // Filter items by search query
  const filteredItems = useMemo(() => {
    if (!data?.items) return {}
    if (!searchQuery.trim()) return data.items
    
    const query = searchQuery.toLowerCase()
    const filtered: Record<string, CalendarSubject[]> = {}
    
    for (const [date, subjects] of Object.entries(data.items)) {
      const matchingSubjects = subjects.filter(s =>
        s.subject_name.toLowerCase().includes(query)
      )
      if (matchingSubjects.length > 0) {
        filtered[date] = matchingSubjects
      }
    }
    
    return filtered
  }, [data?.items, searchQuery])
  
  // Get subjects for a specific day
  const getSubjectsForDay = (date: Date): CalendarSubject[] => {
    const key = formatDateKey(date)
    return filteredItems[key] || []
  }
  
  // Get all dates with reviews, sorted
  const reviewDates = useMemo(() => {
    return Object.keys(filteredItems).sort()
  }, [filteredItems])
  
  // Navigation handlers
  const goToPrevMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1))
  }
  
  const goToNextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1))
  }
  
  const goToToday = () => {
    setCurrentDate(new Date())
  }
  
  // Selected day's subjects for dialog
  const selectedDaySubjects = selectedDay ? (filteredItems[selectedDay] || []) : []
  
  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Calendar</h1>
          <p className="text-sm sm:text-base text-muted-foreground mt-1">
            View your upcoming review schedule
          </p>
        </div>
        <Button 
          variant="outline" 
          size="default"
          onClick={fetchReviews}
          disabled={loading}
          className="w-full sm:w-auto"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>
      
      {/* Controls Card */}
      <Card>
        <CardContent className="p-3 sm:p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            {/* Month Navigation */}
            <div className="flex items-center gap-2">
              <Button variant="outline" size="icon" onClick={goToPrevMonth}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon" onClick={goToNextMonth}>
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={goToToday}>
                Today
              </Button>
              <span className="font-semibold text-sm sm:text-base ml-2">
                {MONTHS[month]} {year}
              </span>
            </div>
            
            {/* View Toggle & Search */}
            <div className="flex items-center gap-2">
              {/* View Toggle */}
              <div className="flex rounded-md border">
                <Button
                  variant={viewMode === 'month' ? 'secondary' : 'ghost'}
                  size="sm"
                  className="rounded-r-none"
                  onClick={() => setViewMode('month')}
                >
                  <CalendarDays className="h-4 w-4 sm:mr-1" />
                  <span className="hidden sm:inline">Month</span>
                </Button>
                <Button
                  variant={viewMode === 'agenda' ? 'secondary' : 'ghost'}
                  size="sm"
                  className="rounded-l-none border-l"
                  onClick={() => setViewMode('agenda')}
                >
                  <List className="h-4 w-4 sm:mr-1" />
                  <span className="hidden sm:inline">Agenda</span>
                </Button>
              </div>
              
              {/* Search */}
              <div className="relative flex-1 sm:flex-none sm:w-48">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  type="text"
                  placeholder="Filter subjects..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 pr-8 h-9"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Error State */}
      {error && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="flex items-center gap-3 py-4">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <p className="text-sm text-destructive">{error}</p>
            <Button variant="outline" size="sm" onClick={fetchReviews} className="ml-auto">
              Retry
            </Button>
          </CardContent>
        </Card>
      )}
      
      {/* Calendar Views */}
      {viewMode === 'month' ? (
        <MonthView
          calendarDays={calendarDays}
          loading={loading}
          getSubjectsForDay={getSubjectsForDay}
          onDayClick={(date) => setSelectedDay(formatDateKey(date))}
          onToggleComplete={handleToggleComplete}
        />
      ) : (
        <AgendaView
          reviewDates={reviewDates}
          filteredItems={filteredItems}
          loading={loading}
          currentMonth={month}
          currentYear={year}
          onToggleComplete={handleToggleComplete}
        />
      )}
      
      {/* Day Detail Dialog */}
      <Dialog open={!!selectedDay} onOpenChange={() => setSelectedDay(null)}>
        <DialogContent className="max-w-md max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {selectedDay && formatDisplayDate(selectedDay)}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 mt-2">
            {selectedDaySubjects.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                No reviews scheduled for this day
              </p>
            ) : (
              selectedDaySubjects.map((subject) => (
                <div
                  key={subject.subject_id}
                  className={cn(
                    'p-3 rounded-lg border',
                    getSubjectColor(subject.subject_id)
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className={cn("font-medium", subject.is_completed && "line-through text-muted-foreground")}>
                      {formatSubjectWithRevision(subject)}
                    </span>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => handleToggleComplete(subject)}
                        aria-label={subject.is_completed ? "Mark incomplete" : "Mark complete"}
                      >
                        {subject.is_completed ? "✓" : ""}
                      </Button>
                      <Badge variant="outline" className="text-xs">
                        {subject.revision_number}/{subject.total_revisions}
                      </Badge>
                    </div>
                  </div>
                  {subject.is_missed && (
                    <Badge variant="destructive" className="text-xs w-fit">
                      Missed → moved
                    </Badge>
                  )}
                  <p className="text-xs mt-1 opacity-75">
                    Started: {formatDisplayDate(subject.start_date)}
                  </p>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

/**
 * Month grid view component.
 */
function MonthView({
  calendarDays,
  loading,
  getSubjectsForDay,
  onDayClick,
  onToggleComplete,
}: {
  calendarDays: ReturnType<typeof getCalendarDays>
  loading: boolean
  getSubjectsForDay: (date: Date) => CalendarSubject[]
  onDayClick: (date: Date) => void
  onToggleComplete: (event: CalendarSubject) => void
}) {
  return (
    <Card>
      <CardContent className="p-2 sm:p-4">
        {/* Weekday Headers */}
        <div className="grid grid-cols-7 mb-2">
          {WEEKDAYS.map((day) => (
            <div
              key={day}
              className="text-center text-xs sm:text-sm font-medium text-muted-foreground py-2"
            >
              <span className="hidden sm:inline">{day}</span>
              <span className="sm:hidden">{day.charAt(0)}</span>
            </div>
          ))}
        </div>
        
        {/* Calendar Grid */}
        <div className="space-y-1">
          {calendarDays.map((week, weekIndex) => (
            <div key={weekIndex} className="grid grid-cols-7 gap-1">
              {week.map((day) => {
                const subjects = getSubjectsForDay(day.date)
                const hasReviews = subjects.length > 0
                
                return (
                  <button
                    key={day.date.toISOString()}
                    onClick={() => onDayClick(day.date)}
                    disabled={loading}
                    className={cn(
                      'relative min-h-[60px] sm:min-h-[80px] p-1 sm:p-2 rounded-md border text-left transition-colors',
                      'hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1',
                      day.isCurrentMonth ? 'bg-white' : 'bg-slate-50/50',
                      day.isToday && 'ring-2 ring-primary ring-offset-1',
                      !day.isCurrentMonth && 'opacity-50'
                    )}
                  >
                    {/* Day Number */}
                    <span
                      className={cn(
                        'text-xs sm:text-sm font-medium',
                        day.isToday && 'text-primary font-bold'
                      )}
                    >
                      {day.date.getDate()}
                    </span>
                    
                    {/* Subject Badges */}
                    {!loading && hasReviews && (
                      <div className="mt-1 space-y-0.5 overflow-hidden">
                        {subjects.slice(0, 2).map((subject) => (
                          <div
                            key={subject.subject_id}
                            className={cn(
                              'text-[10px] sm:text-xs px-1 py-0.5 rounded truncate border',
                              getSubjectColor(subject.subject_id)
                            )}
                          >
                            <button
                              type="button"
                              className="mr-1 h-4 w-4 border rounded text-[10px] flex items-center justify-center"
                              onClick={(e) => {
                                e.stopPropagation()
                                onToggleComplete(subject)
                              }}
                              aria-label={subject.is_completed ? "Mark incomplete" : "Mark complete"}
                            >
                              {subject.is_completed ? "✓" : ""}
                            </button>
                            <span className={cn(subject.is_completed && "line-through opacity-70")}>
                              {formatSubjectWithRevision(subject)}
                            </span>
                          </div>
                        ))}
                        {subjects.length > 2 && (
                          <div className="text-[10px] sm:text-xs text-muted-foreground px-1">
                            +{subjects.length - 2} more
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* Loading skeleton */}
                    {loading && (
                      <div className="mt-1 space-y-1">
                        <div className="h-3 sm:h-4 bg-slate-200 rounded animate-pulse" />
                      </div>
                    )}
                  </button>
                )
              })}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Agenda/list view component.
 */
function AgendaView({
  reviewDates,
  filteredItems,
  loading,
  currentMonth,
  currentYear,
  onToggleComplete,
}: {
  reviewDates: string[]
  filteredItems: Record<string, CalendarSubject[]>
  loading: boolean
  currentMonth: number
  currentYear: number
  onToggleComplete: (event: CalendarSubject) => void
}) {
  // Filter to only show dates in current month
  const monthDates = reviewDates.filter((dateStr) => {
    const date = new Date(dateStr + 'T00:00:00')
    return date.getMonth() === currentMonth && date.getFullYear() === currentYear
  })
  
  if (loading) {
    return (
      <Card>
        <CardContent className="py-12">
          <div className="flex items-center justify-center">
            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    )
  }
  
  if (monthDates.length === 0) {
    return (
      <Card>
        <CardContent className="py-12">
          <div className="text-center">
            <CalendarDays className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No reviews this month</h3>
            <p className="text-sm text-muted-foreground">
              You don't have any subjects scheduled for review in {MONTHS[currentMonth]}.
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }
  
  return (
    <div className="space-y-3">
      {monthDates.map((dateStr) => {
        const subjects = filteredItems[dateStr] || []
        const date = new Date(dateStr + 'T00:00:00')
        const isToday = new Date().toDateString() === date.toDateString()
        
        return (
          <Card key={dateStr} className={cn(isToday && 'ring-2 ring-primary')}>
            <CardHeader className="pb-2 px-4 pt-4">
              <CardTitle className="text-base flex items-center gap-2">
                {formatDisplayDate(dateStr)}
                {isToday && (
                  <Badge variant="default" className="text-xs">Today</Badge>
                )}
                <Badge variant="secondary" className="ml-auto text-xs">
                  {subjects.length} review{subjects.length !== 1 ? 's' : ''}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <div className="space-y-2">
                {subjects.map((subject) => (
                  <div
                    key={subject.subject_id}
                    className={cn(
                      'flex items-center justify-between p-2 rounded-md border',
                      getSubjectColor(subject.subject_id)
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => onToggleComplete(subject)}
                        aria-label={subject.is_completed ? "Mark incomplete" : "Mark complete"}
                      >
                        {subject.is_completed ? "✓" : ""}
                      </Button>
                      <span className={cn("font-medium text-sm", subject.is_completed && "line-through text-muted-foreground")}>
                        {formatSubjectWithRevision(subject)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {subject.is_missed && (
                        <Badge variant="destructive" className="text-xs">Missed</Badge>
                      )}
                      <Badge variant="outline" className="text-xs">
                        {subject.revision_number}/{subject.total_revisions}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
