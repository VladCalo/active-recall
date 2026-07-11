/**
 * Calendar Page
 *
 * Shows each chapter's single upcoming next_due_date plus completed-session
 * history. Unlike the old static schedule, future intervals depend on a
 * rating that hasn't happened yet, so this can't project a whole future
 * schedule - only what's already known.
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
import { getReviewsInRange, type RangeReviewsResponse, type CalendarItem, type Category } from '@/lib/api'
import { cn } from '@/lib/utils'

type ViewMode = 'month' | 'agenda'

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
]

const CATEGORY_STYLES: Record<Category, string> = {
  HARD: 'bg-red-100 text-red-800 border-red-200',
  MEDIUM: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  EASY: 'bg-green-100 text-green-800 border-green-200',
}

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

function formatDateKey(date: Date): string {
  return date.toISOString().split('T')[0]
}

function formatDisplayDate(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00')
  return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
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

  const calendarDays = useMemo(() => getCalendarDays(year, month), [year, month])

  const dateRange = useMemo(() => {
    const firstDay = calendarDays[0][0].date
    const lastWeek = calendarDays[calendarDays.length - 1]
    const lastDay = lastWeek[lastWeek.length - 1].date
    return { start: formatDateKey(firstDay), end: formatDateKey(lastDay) }
  }, [calendarDays])

  const fetchReviews = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await getReviewsInRange(dateRange.start, dateRange.end, 'Europe/Bucharest')
      setData(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load calendar')
    } finally {
      setLoading(false)
    }
  }, [dateRange])

  useEffect(() => {
    fetchReviews()
  }, [fetchReviews])

  const filteredItems = useMemo(() => {
    if (!data?.items) return {}
    if (!searchQuery.trim()) return data.items

    const query = searchQuery.toLowerCase()
    const filtered: Record<string, CalendarItem[]> = {}
    for (const [date, items] of Object.entries(data.items)) {
      const matching = items.filter((s) => s.subject_name.toLowerCase().includes(query))
      if (matching.length > 0) filtered[date] = matching
    }
    return filtered
  }, [data?.items, searchQuery])

  const getItemsForDay = (date: Date): CalendarItem[] => filteredItems[formatDateKey(date)] || []

  const reviewDates = useMemo(() => Object.keys(filteredItems).sort(), [filteredItems])

  const goToPrevMonth = () => setCurrentDate(new Date(year, month - 1, 1))
  const goToNextMonth = () => setCurrentDate(new Date(year, month + 1, 1))
  const goToToday = () => setCurrentDate(new Date())

  const selectedDayItems = selectedDay ? (filteredItems[selectedDay] || []) : []

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Calendar</h1>
          <p className="text-sm sm:text-base text-muted-foreground mt-1">
            Each chapter's next review date, plus completed-session history
          </p>
        </div>
        <Button variant="outline" size="default" onClick={fetchReviews} disabled={loading} className="w-full sm:w-auto">
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <Card>
        <CardContent className="p-3 sm:p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
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

            <div className="flex items-center gap-2">
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

              <div className="relative flex-1 sm:flex-none sm:w-48">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  type="text"
                  placeholder="Filter chapters..."
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

      {viewMode === 'month' ? (
        <MonthView
          calendarDays={calendarDays}
          loading={loading}
          getItemsForDay={getItemsForDay}
          onDayClick={(date) => setSelectedDay(formatDateKey(date))}
        />
      ) : (
        <AgendaView
          reviewDates={reviewDates}
          filteredItems={filteredItems}
          loading={loading}
          currentMonth={month}
          currentYear={year}
        />
      )}

      <Dialog open={!!selectedDay} onOpenChange={() => setSelectedDay(null)}>
        <DialogContent className="max-w-md max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedDay && formatDisplayDate(selectedDay)}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 mt-2">
            {selectedDayItems.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">Nothing on this day</p>
            ) : (
              selectedDayItems.map((item) => (
                <div key={`${item.subject_id}-${item.type}`} className={cn('p-3 rounded-lg border', CATEGORY_STYLES[item.category])}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{item.subject_name}</span>
                    <Badge variant="outline" className="text-xs">
                      {item.type === 'completed' ? item.rating : 'upcoming'}
                    </Badge>
                  </div>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function MonthView({
  calendarDays,
  loading,
  getItemsForDay,
  onDayClick,
}: {
  calendarDays: ReturnType<typeof getCalendarDays>
  loading: boolean
  getItemsForDay: (date: Date) => CalendarItem[]
  onDayClick: (date: Date) => void
}) {
  return (
    <Card>
      <CardContent className="p-2 sm:p-4">
        <div className="grid grid-cols-7 mb-2">
          {WEEKDAYS.map((day) => (
            <div key={day} className="text-center text-xs sm:text-sm font-medium text-muted-foreground py-2">
              <span className="hidden sm:inline">{day}</span>
              <span className="sm:hidden">{day.charAt(0)}</span>
            </div>
          ))}
        </div>

        <div className="space-y-1">
          {calendarDays.map((week, weekIndex) => (
            <div key={weekIndex} className="grid grid-cols-7 gap-1">
              {week.map((day) => {
                const items = getItemsForDay(day.date)
                const hasItems = items.length > 0

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
                    <span className={cn('text-xs sm:text-sm font-medium', day.isToday && 'text-primary font-bold')}>
                      {day.date.getDate()}
                    </span>

                    {!loading && hasItems && (
                      <div className="mt-1 space-y-0.5 overflow-hidden">
                        {items.slice(0, 2).map((item) => (
                          <div
                            key={`${item.subject_id}-${item.type}`}
                            className={cn('text-[10px] sm:text-xs px-1 py-0.5 rounded truncate border', CATEGORY_STYLES[item.category])}
                          >
                            {item.type === 'completed' ? '✓ ' : ''}
                            {item.subject_name}
                          </div>
                        ))}
                        {items.length > 2 && (
                          <div className="text-[10px] sm:text-xs text-muted-foreground px-1">
                            +{items.length - 2} more
                          </div>
                        )}
                      </div>
                    )}

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

function AgendaView({
  reviewDates,
  filteredItems,
  loading,
  currentMonth,
  currentYear,
}: {
  reviewDates: string[]
  filteredItems: Record<string, CalendarItem[]>
  loading: boolean
  currentMonth: number
  currentYear: number
}) {
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
            <h3 className="text-lg font-semibold mb-2">Nothing this month</h3>
            <p className="text-sm text-muted-foreground">
              No upcoming reviews or completed sessions in {MONTHS[currentMonth]}.
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-3">
      {monthDates.map((dateStr) => {
        const items = filteredItems[dateStr] || []
        const date = new Date(dateStr + 'T00:00:00')
        const isToday = new Date().toDateString() === date.toDateString()

        return (
          <Card key={dateStr} className={cn(isToday && 'ring-2 ring-primary')}>
            <CardHeader className="pb-2 px-4 pt-4">
              <CardTitle className="text-base flex items-center gap-2">
                {formatDisplayDate(dateStr)}
                {isToday && <Badge variant="default" className="text-xs">Today</Badge>}
                <Badge variant="secondary" className="ml-auto text-xs">
                  {items.length} item{items.length !== 1 ? 's' : ''}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <div className="space-y-2">
                {items.map((item) => (
                  <div
                    key={`${item.subject_id}-${item.type}`}
                    className={cn('flex items-center justify-between p-2 rounded-md border', CATEGORY_STYLES[item.category])}
                  >
                    <span className="font-medium text-sm">
                      {item.type === 'completed' ? '✓ ' : ''}
                      {item.subject_name}
                    </span>
                    <Badge variant="outline" className="text-xs">
                      {item.type === 'completed' ? item.rating : item.category}
                    </Badge>
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
