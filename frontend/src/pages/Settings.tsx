/**
 * Settings Page
 *
 * Lets the user set their exam date - Final Active Recall cutoff (31 days
 * before) and Reference Mode end (1 day before) are derived automatically.
 */

import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { getExamSettings, updateExamSettings, type ExamSettings } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { useToast } from '@/hooks/use-toast'

export function Settings() {
  const [settings, setSettings] = useState<ExamSettings | null>(null)
  const [examDate, setExamDate] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const { toast } = useToast()

  const load = async () => {
    setLoading(true)
    try {
      const data = await getExamSettings()
      setSettings(data)
      setExamDate(data.exam_date)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const updated = await updateExamSettings(examDate)
      setSettings(updated)
      toast({ title: 'Exam date updated', description: 'Final Recall cutoff and Reference Mode end were recalculated.' })
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to update exam date',
        variant: 'destructive',
      })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <p className="text-muted-foreground py-12 text-center">Loading...</p>
  }

  return (
    <div className="space-y-4 sm:space-y-6 max-w-lg">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-sm sm:text-base text-muted-foreground mt-1">
          Set your exam date - everything else follows from it.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Exam Date</CardTitle>
          <CardDescription>Must be more than 31 days from today.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSave} className="space-y-4">
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
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving...' : 'Save'}
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
    </div>
  )
}
