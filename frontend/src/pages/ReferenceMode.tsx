/**
 * Reference Mode page (Phase 2: Final Rereading).
 *
 * Shown automatically instead of the Dashboard once the exam-cycle cutoff
 * is reached. No scheduling here - just the final category snapshot per
 * chapter, a recommended reread intensity, and a completion tracker.
 */

import { useEffect, useState } from 'react'
import { RefreshCw, CheckCircle2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  getReferenceMode,
  getReferenceModeSummary,
  completeReread,
  type ReferenceModeChapter,
  type ReferenceModeSummary,
  type Category,
} from '@/lib/api'
import { formatDate } from '@/lib/utils'

const CATEGORY_STYLES: Record<Category, string> = {
  HARD: 'bg-red-100 text-red-700 border-red-200',
  MEDIUM: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  EASY: 'bg-green-100 text-green-700 border-green-200',
}

export function ReferenceMode() {
  const [chapters, setChapters] = useState<ReferenceModeChapter[]>([])
  const [summary, setSummary] = useState<ReferenceModeSummary | null>(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const [list, sum] = await Promise.all([getReferenceMode(), getReferenceModeSummary()])
      setChapters(list.chapters)
      setSummary(sum)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleComplete = async (subjectId: string) => {
    await completeReread(subjectId)
    load()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Final Rereading</h1>
        <p className="text-sm sm:text-base text-muted-foreground mt-1">
          You decide how to reread each chapter - the app just guides the intensity.
        </p>
      </div>

      {summary && (
        <div className="grid gap-3 sm:gap-4 grid-cols-2 lg:grid-cols-4">
          <StatCard label="Completed" value={summary.chapters_completed} />
          <StatCard label="Remaining" value={summary.chapters_remaining} />
          <StatCard label="Progress" value={`${summary.percentage_completed}%`} />
          <StatCard label="Days to Exam" value={summary.days_remaining_until_exam} />
        </div>
      )}

      <div className="grid gap-3 sm:gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {chapters.map((chapter) => (
          <Card key={chapter.subject_id} className={chapter.reread_completed ? 'opacity-60' : ''}>
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between gap-2">
                <CardTitle className="text-base sm:text-lg leading-tight">{chapter.subject_name}</CardTitle>
                <Badge className={`text-xs border ${CATEGORY_STYLES[chapter.final_category]}`}>
                  {chapter.final_category}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Last Active Recall: {chapter.last_active_recall_date ? formatDate(chapter.last_active_recall_date) : '-'}
                {' · '}
                {chapter.total_active_recall_count} session{chapter.total_active_recall_count !== 1 ? 's' : ''}
              </p>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <p className="text-sm font-semibold">{chapter.recommended_intensity_label}</p>
                <ul className="text-xs text-muted-foreground list-disc list-inside mt-1 space-y-0.5">
                  {chapter.recommended_focus.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              </div>
              {chapter.reread_completed ? (
                <div className="flex items-center gap-2 text-sm text-green-700">
                  <CheckCircle2 className="h-4 w-4" />
                  Final Reread Completed
                </div>
              ) : (
                <Button size="sm" className="w-full" onClick={() => handleComplete(chapter.subject_id)}>
                  ✓ Final Reread Completed
                </Button>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {chapters.length === 0 && (
        <p className="text-center text-muted-foreground py-12">
          No chapters have reached their Final Active Recall yet.
        </p>
      )}
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <CardContent className="py-3 sm:py-4">
        <p className="text-xl sm:text-2xl font-bold">{value}</p>
        <p className="text-xs sm:text-sm text-muted-foreground">{label}</p>
      </CardContent>
    </Card>
  )
}
