/**
 * Dashboard Page
 * 
 * The main dashboard showing today's reviews.
 * Responsive design with cards that stack on mobile.
 */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Calendar, BookOpen, Clock, Sparkles, RefreshCw, AlertTriangle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { getTodayReviews, completeReviewEvent, rescheduleReviewEvent, type ReviewEvent, type TodayReviewsResponse } from '@/lib/api'
import { formatDate } from '@/lib/utils'

export function Dashboard() {
  const [data, setData] = useState<TodayReviewsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isRateLimited, setIsRateLimited] = useState(false)

  const fetchReviews = async () => {
    setLoading(true)
    setError(null)
    setIsRateLimited(false)
    try {
      const response = await getTodayReviews('Europe/Bucharest')
      setData(response)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load reviews'
      setError(message)
      if (message.toLowerCase().includes('too many') || message.toLowerCase().includes('429')) {
        setIsRateLimited(true)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchReviews()
  }, [])

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-sm sm:text-base text-muted-foreground mt-1">
            Your daily review schedule at a glance
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

      {/* Today's Date Card */}
      {data && (
        <Card className="bg-gradient-to-r from-primary/5 to-primary/10 border-primary/20">
          <CardContent className="flex items-center gap-3 sm:gap-4 py-3 sm:py-4">
            <div className="p-2.5 sm:p-3 rounded-full bg-primary/10 flex-shrink-0">
              <Calendar className="h-5 w-5 sm:h-6 sm:w-6 text-primary" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs sm:text-sm text-muted-foreground">Today&apos;s Date</p>
              <p className="text-base sm:text-lg font-semibold truncate">{formatDate(data.today)}</p>
              <p className="text-xs text-muted-foreground">Timezone: {data.timezone}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Today's Reviews Section */}
      <Card>
        <CardHeader className="pb-3 sm:pb-6">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
            <CardTitle className="text-lg sm:text-xl">Today&apos;s Reviews</CardTitle>
          </div>
          <CardDescription className="text-sm">
          {data ? `${data.count} event${data.count !== 1 ? 's' : ''} to review today` : 'Loading...'}
          </CardDescription>
        </CardHeader>
        <CardContent className="p-3 sm:p-6 pt-0 sm:pt-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <div className="text-center py-12 px-4">
              {isRateLimited ? (
                <>
                  <AlertTriangle className="h-8 w-8 text-yellow-500 mx-auto mb-4" />
                  <p className="text-muted-foreground mb-2">Too many requests</p>
                  <p className="text-sm text-muted-foreground mb-4">
                    Please wait a moment before refreshing.
                  </p>
                </>
              ) : (
                <p className="text-destructive mb-4">{error}</p>
              )}
              <Button variant="outline" onClick={fetchReviews} disabled={isRateLimited}>
                Try Again
              </Button>
            </div>
          ) : data && data.events.length > 0 ? (
            <div className="grid gap-3 sm:gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.events.map((event) => (
                <SubjectReviewCard key={`${event.subject_id}-${event.due_date}`} event={event} onRefresh={fetchReviews} />
              ))}
            </div>
          ) : (
            <EmptyState />
          )}
        </CardContent>
      </Card>

      {/* Quick Stats */}
      {data && data.count > 0 && (
        <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
          <Card>
            <CardContent className="flex items-center gap-3 sm:gap-4 py-3 sm:py-4">
              <div className="p-2 rounded-full bg-blue-100 flex-shrink-0">
                <BookOpen className="h-4 w-4 sm:h-5 sm:w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-xl sm:text-2xl font-bold">{data.count}</p>
                <p className="text-xs sm:text-sm text-muted-foreground">Reviews Due</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

/**
 * Helper function to format subject name with revision number.
 */
function formatSubjectWithRevision(event: ReviewEvent): string {
  if (event.is_completed) {
    return `${event.subject_name} ✓`
  }
  return `${event.subject_name} ${event.revision_number}`
}

/**
 * Card component for a single subject due for review.
 */
function SubjectReviewCard({
  event,
  onRefresh,
}: {
  event: ReviewEvent
  onRefresh: () => void
}) {
  const [isUpdating, setIsUpdating] = useState(false)
  const [showReschedule, setShowReschedule] = useState(false)
  const [newDate, setNewDate] = useState<string>('')

  const handleToggleComplete = async () => {
    setIsUpdating(true)
    try {
      await completeReviewEvent(event.subject_id, event.due_date, !event.is_completed)
      onRefresh()
    } finally {
      setIsUpdating(false)
    }
  }

  const handleReschedule = async () => {
    if (!newDate) return
    setIsUpdating(true)
    try {
      await rescheduleReviewEvent(event.subject_id, event.due_date, newDate)
      setShowReschedule(false)
      setNewDate('')
      onRefresh()
    } finally {
      setIsUpdating(false)
    }
  }

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-2 px-3 sm:px-6 pt-3 sm:pt-6">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base sm:text-lg leading-tight">
            <span className={event.is_completed ? 'line-through text-muted-foreground' : ''}>
              {formatSubjectWithRevision(event)}
            </span>
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="icon"
              onClick={handleToggleComplete}
              disabled={isUpdating}
              className="h-7 w-7"
              aria-label={event.is_completed ? 'Mark incomplete' : 'Mark complete'}
            >
              {event.is_completed ? '✓' : ''}
            </Button>
            <Badge 
              variant={event.schedule_type === 'CUSTOM' ? 'secondary' : 'outline'}
              className="text-xs flex-shrink-0"
            >
              {event.schedule_type}
            </Badge>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <p className="text-xs text-muted-foreground">
            Review {event.revision_number} of {event.total_revisions}
          </p>
          {event.is_missed && (
            <Badge variant="destructive" className="text-xs">
              Missed → moved to today
            </Badge>
          )}
        </div>
        {event.is_missed && (
          <Button
            variant="outline"
            size="sm"
            className="mt-2 w-fit"
            onClick={() => setShowReschedule(true)}
          >
            Reschedule
          </Button>
        )}
        {!event.is_missed && !event.is_completed && (
          <p className="text-xs text-muted-foreground">
            Due date: {formatDate(event.due_date)}
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-1.5 sm:space-y-2 px-3 sm:px-6 pb-3 sm:pb-6">
        <div className="flex items-center gap-2 text-xs sm:text-sm text-muted-foreground">
          <Calendar className="h-3.5 w-3.5 sm:h-4 sm:w-4 flex-shrink-0" />
          <span className="truncate">Started: {formatDate(event.start_date)}</span>
        </div>
        <div className="flex items-center gap-2 text-xs sm:text-sm text-muted-foreground">
          <Clock className="h-3.5 w-3.5 sm:h-4 sm:w-4 flex-shrink-0" />
          <span className="truncate">
            Original due: {formatDate(event.due_date)}
          </span>
        </div>
      </CardContent>
      {showReschedule && (
        <div className="px-3 sm:px-6 pb-3 sm:pb-6">
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={newDate}
              onChange={(e) => setNewDate(e.target.value)}
              className="border rounded px-2 py-1 text-sm"
            />
            <Button size="sm" onClick={handleReschedule} disabled={!newDate || isUpdating}>
              Save
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setShowReschedule(false)}>
              Cancel
            </Button>
          </div>
        </div>
      )}
    </Card>
  )
}

/**
 * Empty state component shown when no reviews are due.
 */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-10 sm:py-12 text-center px-4">
      <div className="p-3 sm:p-4 rounded-full bg-green-100 mb-3 sm:mb-4">
        <Sparkles className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
      </div>
      <h3 className="text-base sm:text-lg font-semibold mb-2">All caught up!</h3>
      <p className="text-sm text-muted-foreground mb-4 sm:mb-6 max-w-md">
        You have no subjects to review today. Great job staying on top of your studies!
      </p>
      <Link to="/subjects">
        <Button size="default">
          <BookOpen className="h-4 w-4 mr-2" />
          View All Subjects
        </Button>
      </Link>
    </div>
  )
}
