/**
 * Subject Dialog Component
 * 
 * Modal dialog for creating and editing subjects.
 * Handles form validation and API calls.
 */

import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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
import { createSubject, updateSubject, type Subject, type ScheduleType } from '@/lib/api'
import { parseIntervals } from '@/lib/utils'
import { useToast } from '@/hooks/use-toast'

interface SubjectDialogProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  subject: Subject | null
}

const DEFAULT_INTERVALS = [1, 3, 7, 14, 30, 60, 120, 180]

export function SubjectDialog({ open, onClose, onSuccess, subject }: SubjectDialogProps) {
  const [name, setName] = useState('')
  const [startDate, setStartDate] = useState('')
  const [scheduleType, setScheduleType] = useState<ScheduleType>('DEFAULT')
  const [customIntervals, setCustomIntervals] = useState('')
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  
  const { toast } = useToast()
  const isEditing = !!subject

  // Reset form when dialog opens/closes or subject changes
  useEffect(() => {
    if (open) {
      if (subject) {
        setName(subject.name)
        setStartDate(subject.start_date)
        setScheduleType(subject.schedule_type)
        setCustomIntervals(
          subject.custom_intervals_days 
            ? subject.custom_intervals_days.join(', ') 
            : ''
        )
      } else {
        // Default to today's date for new subjects
        const today = new Date().toISOString().split('T')[0]
        setName('')
        setStartDate(today)
        setScheduleType('DEFAULT')
        setCustomIntervals('')
      }
      setErrors({})
    }
  }, [open, subject])

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!name.trim()) {
      newErrors.name = 'Name is required'
    }

    if (!startDate) {
      newErrors.startDate = 'Start date is required'
    }

    if (scheduleType === 'CUSTOM') {
      const intervals = parseIntervals(customIntervals)
      if (!intervals) {
        newErrors.customIntervals = 'Enter valid positive integers separated by commas (e.g., 1, 3, 7)'
      } else if (intervals.length > 50) {
        newErrors.customIntervals = 'Maximum 50 intervals allowed'
      }
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validate()) return

    setSaving(true)
    try {
      const data: {
        name: string
        start_date: string
        schedule_type: ScheduleType
        custom_intervals_days?: number[]
      } = {
        name: name.trim(),
        start_date: startDate,
        schedule_type: scheduleType,
      }

      if (scheduleType === 'CUSTOM') {
        const intervals = parseIntervals(customIntervals)
        if (intervals) {
          data.custom_intervals_days = intervals
        }
      }

      if (isEditing && subject) {
        await updateSubject(subject.id, data)
        toast({
          title: 'Subject updated',
          description: `"${data.name}" has been updated.`,
        })
      } else {
        await createSubject(data)
        toast({
          title: 'Subject created',
          description: `"${data.name}" has been created.`,
        })
      }

      onSuccess()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An error occurred'
      
      // Check if it's a name uniqueness error
      if (message.toLowerCase().includes('already exists')) {
        setErrors({ name: message })
      } else {
        toast({
          title: 'Error',
          description: message,
          variant: 'destructive',
        })
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="sm:max-w-[425px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>{isEditing ? 'Edit Subject' : 'Add Subject'}</DialogTitle>
            <DialogDescription>
              {isEditing 
                ? 'Update the subject details below.' 
                : 'Create a new study subject to track with active recall.'}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {/* Name */}
            <div className="grid gap-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Cardiology"
                className={errors.name ? 'border-destructive' : ''}
              />
              {errors.name && (
                <p className="text-sm text-destructive">{errors.name}</p>
              )}
            </div>

            {/* Start Date */}
            <div className="grid gap-2">
              <Label htmlFor="startDate">Start Date</Label>
              <Input
                id="startDate"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className={errors.startDate ? 'border-destructive' : ''}
              />
              {errors.startDate && (
                <p className="text-sm text-destructive">{errors.startDate}</p>
              )}
            </div>

            {/* Schedule Type */}
            <div className="grid gap-2">
              <Label htmlFor="scheduleType">Schedule Type</Label>
              <Select 
                value={scheduleType} 
                onValueChange={(value) => setScheduleType(value as ScheduleType)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="DEFAULT">
                    Default ({DEFAULT_INTERVALS.join(', ')} days)
                  </SelectItem>
                  <SelectItem value="CUSTOM">Custom Intervals</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Custom Intervals (shown only for CUSTOM schedule) */}
            {scheduleType === 'CUSTOM' && (
              <div className="grid gap-2">
                <Label htmlFor="customIntervals">Custom Intervals (days)</Label>
                <Input
                  id="customIntervals"
                  value={customIntervals}
                  onChange={(e) => setCustomIntervals(e.target.value)}
                  placeholder="e.g., 1, 3, 7, 14, 30"
                  className={errors.customIntervals ? 'border-destructive' : ''}
                />
                <p className="text-xs text-muted-foreground">
                  Enter positive integers separated by commas
                </p>
                {errors.customIntervals && (
                  <p className="text-sm text-destructive">{errors.customIntervals}</p>
                )}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? 'Saving...' : isEditing ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
