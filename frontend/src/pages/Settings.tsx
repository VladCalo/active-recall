/**
 * Settings Page
 *
 * - Exam date: Final Active Recall cutoff (31 days before) and Reference
 *   Mode end (1 day before) are derived automatically.
 * - Interval ladders per category: fully customizable, defaults to the
 *   built-in Hard/Medium/Easy day sequences until changed.
 * - No-revision-day rule: which weekday (if any) gets pushed to the next day.
 */

import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { getExamSettings, updateExamSettings, type ExamSettings, type Ladders, type Category } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { useToast } from '@/hooks/use-toast'

const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

const CATEGORY_LABELS: { key: Category; label: string }[] = [
  { key: 'HARD', label: 'Hard' },
  { key: 'MEDIUM', label: 'Medium' },
  { key: 'EASY', label: 'Easy' },
]

export function Settings() {
  const [settings, setSettings] = useState<ExamSettings | null>(null)
  const [examDate, setExamDate] = useState('')
  const [ladders, setLadders] = useState<Ladders>({ HARD: [0, 0, 0, 0], MEDIUM: [0, 0, 0, 0], EASY: [0, 0, 0, 0] })
  const [noRevisionEnabled, setNoRevisionEnabled] = useState(true)
  const [noRevisionWeekday, setNoRevisionWeekday] = useState(6)
  const [loading, setLoading] = useState(true)
  const [savingExam, setSavingExam] = useState(false)
  const [savingRules, setSavingRules] = useState(false)
  const { toast } = useToast()

  const load = async () => {
    setLoading(true)
    try {
      const data = await getExamSettings()
      setSettings(data)
      setExamDate(data.exam_date)
      setLadders(data.ladders)
      setNoRevisionEnabled(data.no_revision_enabled)
      setNoRevisionWeekday(data.no_revision_weekday)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleSaveExamDate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSavingExam(true)
    try {
      const updated = await updateExamSettings({ exam_date: examDate })
      setSettings(updated)
      toast({ title: 'Exam date updated', description: 'Final Recall cutoff and Reference Mode end were recalculated.' })
    } catch (err) {
      toast({ title: 'Error', description: err instanceof Error ? err.message : 'Failed to update exam date', variant: 'destructive' })
    } finally {
      setSavingExam(false)
    }
  }

  const handleLadderChange = (category: Category, stage: number, value: string) => {
    const n = parseInt(value, 10)
    setLadders((prev) => {
      const next = { ...prev, [category]: [...prev[category]] }
      next[category][stage] = isNaN(n) ? 0 : n
      return next
    })
  }

  const handleSaveRules = async () => {
    setSavingRules(true)
    try {
      const updated = await updateExamSettings({
        ladders,
        no_revision_enabled: noRevisionEnabled,
        no_revision_weekday: noRevisionWeekday,
      })
      setSettings(updated)
      setLadders(updated.ladders)
      toast({ title: 'Rules updated', description: 'Scheduling rules saved.' })
    } catch (err) {
      toast({ title: 'Error', description: err instanceof Error ? err.message : 'Failed to update rules', variant: 'destructive' })
    } finally {
      setSavingRules(false)
    }
  }

  const handleResetLadders = async () => {
    setSavingRules(true)
    try {
      const updated = await updateExamSettings({ reset_ladders_to_default: true })
      setSettings(updated)
      setLadders(updated.ladders)
      toast({ title: 'Reset to defaults', description: 'Interval ladders reset to the built-in values.' })
    } catch (err) {
      toast({ title: 'Error', description: err instanceof Error ? err.message : 'Failed to reset', variant: 'destructive' })
    } finally {
      setSavingRules(false)
    }
  }

  if (loading) {
    return <p className="text-muted-foreground py-12 text-center">Loading...</p>
  }

  return (
    <div className="space-y-4 sm:space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-sm sm:text-base text-muted-foreground mt-1">
          Defaults work out of the box - customize anything below if you want.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Exam Date</CardTitle>
          <CardDescription>Must be more than 31 days from today.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSaveExamDate} className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="examDate">Exam Date</Label>
              <Input
                id="examDate"
                type="date"
                value={examDate}
                onChange={(e) => setExamDate(e.target.value)}
                className="h-11"
              />
            </div>
            <Button type="submit" disabled={savingExam}>
              {savingExam ? 'Saving...' : 'Save Exam Date'}
            </Button>
          </form>

          {settings && (
            <div className="mt-6 space-y-1.5 text-sm text-muted-foreground border-t pt-4">
              <p>Final Active Recall cutoff: <span className="font-medium text-foreground">{formatDate(settings.final_recall_cutoff_date)}</span></p>
              <p>Reference Mode ends: <span className="font-medium text-foreground">{formatDate(settings.reference_mode_end_date)}</span></p>
              <p>Exam day: <span className="font-medium text-foreground">{formatDate(settings.exam_date)}</span></p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Interval Ladders</CardTitle>
          <CardDescription>
            Days until the next review for each stage, per category.
            {settings && !settings.is_ladders_customized && ' Currently using the built-in defaults.'}
            {settings && settings.is_ladders_customized && ' Currently customized.'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {CATEGORY_LABELS.map(({ key, label }) => (
            <div key={key} className="grid gap-2">
              <Label>{label}</Label>
              <div className="grid grid-cols-4 gap-2">
                {ladders[key].map((day, stage) => (
                  <Input
                    key={stage}
                    type="number"
                    min={1}
                    value={day}
                    onChange={(e) => handleLadderChange(key, stage, e.target.value)}
                    className="h-10"
                  />
                ))}
              </div>
            </div>
          ))}

          <div className="flex flex-col sm:flex-row gap-2 pt-2">
            <Button onClick={handleSaveRules} disabled={savingRules}>
              {savingRules ? 'Saving...' : 'Save Ladders'}
            </Button>
            <Button variant="outline" onClick={handleResetLadders} disabled={savingRules}>
              Reset to Defaults
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>No-Revision Day</CardTitle>
          <CardDescription>If a review lands on this day, it's pushed to the next day.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={noRevisionEnabled}
              onChange={(e) => setNoRevisionEnabled(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
            />
            Enable no-revision day
          </label>

          {noRevisionEnabled && (
            <div className="grid gap-2 max-w-[200px]">
              <Label>Day to skip</Label>
              <Select value={String(noRevisionWeekday)} onValueChange={(v) => setNoRevisionWeekday(parseInt(v, 10))}>
                <SelectTrigger className="h-10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {WEEKDAYS.map((day, i) => (
                    <SelectItem key={day} value={String(i)}>{day}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <Button onClick={handleSaveRules} disabled={savingRules}>
            {savingRules ? 'Saving...' : 'Save'}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
