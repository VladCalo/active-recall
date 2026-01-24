/**
 * Dashboard Page
 * 
 * The main dashboard showing today's reviews.
 * Fetches subjects due today based on the Europe/Bucharest timezone.
 */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Calendar, BookOpen, Clock, Sparkles, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { getTodayReviews, type Subject, type TodayReviewsResponse } from '@/lib/api'
import { formatDate, formatIntervals } from '@/lib/utils'

export function Dashboard() {
  const [data, setData] = useState<TodayReviewsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchReviews = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await getTodayReviews('Europe/Bucharest')
      setData(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load reviews')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchReviews()
  }, [])

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Your daily review schedule at a glance
          </p>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={fetchReviews}
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Today's Date Card */}
      {data && (
        <Card className="bg-gradient-to-r from-primary/5 to-primary/10 border-primary/20">
          <CardContent className="flex items-center gap-4 py-4">
            <div className="p-3 rounded-full bg-primary/10">
              <Calendar className="h-6 w-6 text-primary" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Today&apos;s Date</p>
              <p className="text-lg font-semibold">{formatDate(data.today)}</p>
              <p className="text-xs text-muted-foreground">Timezone: {data.timezone}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Today's Reviews Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-primary" />
            <CardTitle>Today&apos;s Reviews</CardTitle>
          </div>
          <CardDescription>
            {data ? `${data.count} subject${data.count !== 1 ? 's' : ''} to review today` : 'Loading...'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <p className="text-destructive mb-4">{error}</p>
              <Button variant="outline" onClick={fetchReviews}>
                Try Again
              </Button>
            </div>
          ) : data && data.subjects.length > 0 ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.subjects.map((subject) => (
                <SubjectReviewCard key={subject.id} subject={subject} />
              ))}
            </div>
          ) : (
            <EmptyState />
          )}
        </CardContent>
      </Card>

      {/* Quick Stats */}
      {data && data.count > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Card>
            <CardContent className="flex items-center gap-4 py-4">
              <div className="p-2 rounded-full bg-blue-100">
                <BookOpen className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{data.count}</p>
                <p className="text-sm text-muted-foreground">Reviews Due</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

/**
 * Card component for a single subject due for review.
 */
function SubjectReviewCard({ subject }: { subject: Subject }) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-lg">{subject.name}</CardTitle>
          <Badge variant={subject.schedule_type === 'CUSTOM' ? 'secondary' : 'outline'}>
            {subject.schedule_type}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Calendar className="h-4 w-4" />
          <span>Started: {formatDate(subject.start_date)}</span>
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Clock className="h-4 w-4" />
          <span>Intervals: {formatIntervals(subject.intervals)} days</span>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * Empty state component shown when no reviews are due.
 */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="p-4 rounded-full bg-green-100 mb-4">
        <Sparkles className="h-8 w-8 text-green-600" />
      </div>
      <h3 className="text-lg font-semibold mb-2">All caught up!</h3>
      <p className="text-muted-foreground mb-6 max-w-md">
        You have no subjects to review today. Great job staying on top of your studies!
      </p>
      <Link to="/subjects">
        <Button>
          <BookOpen className="h-4 w-4 mr-2" />
          View All Subjects
        </Button>
      </Link>
    </div>
  )
}
