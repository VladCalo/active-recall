/**
 * Dashboard Page
 *
 * Phase 1 (Adaptive Active Recall): today's due chapters, sorted by
 * overdue-priority (Hard, then Medium, then Easy). Automatically defers to
 * the Reference Mode view once the exam-cycle cutoff is reached.
 */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Calendar, BookOpen, Clock, Sparkles, RefreshCw, AlertTriangle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  getTodayReviews,
  completeReview,
  getReferenceModeSummary,
  type DueItem,
  type TodayReviewsResponse,
  type Rating,
  type Category,
} from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { ReferenceMode } from '@/pages/ReferenceMode'

const CATEGORY_STYLES: Record<Category, string> = {
  HARD: 'bg-red-100 text-red-700 border-red-200',
  MEDIUM: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  EASY: 'bg-green-100 text-green-700 border-green-200',
}

const RATINGS: { value: Rating; label: string }[] = [
  { value: 'MAJOR_GAPS', label: 'Major gaps' },
  { value: 'MANY_CONFUSIONS', label: 'Many confusions' },
  { value: 'GOOD_MINOR_HESITATION', label: 'Good, minor hesitation' },
  { value: 'EXCELLENT', label: 'Excellent' },
]

export function Dashboard() {
  const [checkingMode, setCheckingMode] = useState(true)
  const [isReferenceMode, setIsReferenceMode] = useState(false)

  useEffect(() => {
    getReferenceModeSummary()
      .then((s) => setIsReferenceMode(s.is_reference_mode))
      .catch(() => setIsReferenceMode(false))
      .finally(() => setCheckingMode(false))
  }, [])

  if (checkingMode) {
    return (
      <div className="flex items-center justify-center py-24">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (isReferenceMode) {
    return <ReferenceMode />
  }

  return <ActiveRecallDashboard />
}

function ActiveRecallDashboard() {
  const [data, setData] = useState<TodayReviewsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isRateLimited, setIsRateLimited] = useState(false)
  const [banner, setBanner] = useState<string | null>(null)

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
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-sm sm:text-base text-muted-foreground mt-1">
            Your daily review schedule, sorted by priority
          </p>
        </div>
        <Button variant="outline" size="default" onClick={fetchReviews} disabled={loading} className="w-full sm:w-auto">
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {banner && (
        <Card className="bg-amber-50 border-amber-300">
          <CardContent className="flex items-start gap-3 py-3 sm:py-4">
            <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-amber-800">{banner}</p>
          </CardContent>
        </Card>
      )}

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

      <Card>
        <CardHeader className="pb-3 sm:pb-6">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
            <CardTitle className="text-lg sm:text-xl">Today&apos;s Reviews</CardTitle>
          </div>
          <CardDescription className="text-sm">
            {data ? `${data.count} chapter${data.count !== 1 ? 's' : ''} due (overdue Hard first)` : 'Loading...'}
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
                  <p className="text-sm text-muted-foreground mb-4">Please wait a moment before refreshing.</p>
                </>
              ) : (
                <p className="text-destructive mb-4">{error}</p>
              )}
              <Button variant="outline" onClick={fetchReviews} disabled={isRateLimited}>
                Try Again
              </Button>
            </div>
          ) : data && data.items.length > 0 ? (
            <div className="grid gap-3 sm:gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.items.map((item) => (
                <SubjectReviewCard
                  key={item.subject_id}
                  item={item}
                  onRefresh={fetchReviews}
                  onFinalRecall={(msg) => setBanner(msg)}
                />
              ))}
            </div>
          ) : (
            <EmptyState />
          )}
        </CardContent>
      </Card>

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

function SubjectReviewCard({
  item,
  onRefresh,
  onFinalRecall,
}: {
  item: DueItem
  onRefresh: () => void
  onFinalRecall: (message: string) => void
}) {
  const [isUpdating, setIsUpdating] = useState(false)

  const handleRate = async (rating: Rating) => {
    setIsUpdating(true)
    try {
      const result = await completeReview(item.subject_id, rating)
      if (result.is_final_recall && result.banner_message) {
        onFinalRecall(`${item.subject_name}: ${result.banner_message}`)
      }
      onRefresh()
    } finally {
      setIsUpdating(false)
    }
  }

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-2 px-3 sm:px-6 pt-3 sm:pt-6">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base sm:text-lg leading-tight">{item.subject_name}</CardTitle>
          <Badge className={`text-xs flex-shrink-0 border ${CATEGORY_STYLES[item.category]}`}>
            {item.category}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          {item.is_overdue ? (
            <Badge variant="destructive" className="text-xs">
              Overdue since {formatDate(item.due_date)}
            </Badge>
          ) : (
            <p className="text-xs text-muted-foreground">Due today</p>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-2 px-3 sm:px-6 pb-3 sm:pb-6">
        <p className="text-xs text-muted-foreground mb-1">How did this session go?</p>
        <div className="grid grid-cols-2 gap-1.5">
          {RATINGS.map((r) => (
            <Button
              key={r.value}
              variant="outline"
              size="sm"
              className="text-xs h-auto py-1.5 whitespace-normal"
              disabled={isUpdating}
              onClick={() => handleRate(r.value)}
            >
              {r.label}
            </Button>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-10 sm:py-12 text-center px-4">
      <div className="p-3 sm:p-4 rounded-full bg-green-100 mb-3 sm:mb-4">
        <Sparkles className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
      </div>
      <h3 className="text-base sm:text-lg font-semibold mb-2">All caught up!</h3>
      <p className="text-sm text-muted-foreground mb-4 sm:mb-6 max-w-md">
        You have no chapters to review today. Great job staying on top of your studies!
      </p>
      <Link to="/subjects">
        <Button size="default">
          <BookOpen className="h-4 w-4 mr-2" />
          View All Chapters
        </Button>
      </Link>
    </div>
  )
}
