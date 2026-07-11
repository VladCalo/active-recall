/**
 * Subject Dialog Component
 *
 * Modal dialog for creating and editing chapters (name + start date only -
 * category/stage are managed entirely by the adaptive Active Recall engine).
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
import { createSubject, updateSubject, type Subject } from '@/lib/api'
import { useToast } from '@/hooks/use-toast'

interface SubjectDialogProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  subject: Subject | null
}

export function SubjectDialog({ open, onClose, onSuccess, subject }: SubjectDialogProps) {
  const [name, setName] = useState('')
  const [startDate, setStartDate] = useState('')
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  const { toast } = useToast()
  const isEditing = !!subject

  useEffect(() => {
    if (open) {
      if (subject) {
        setName(subject.name)
        setStartDate(subject.start_date)
      } else {
        const today = new Date().toISOString().split('T')[0]
        setName('')
        setStartDate(today)
      }
      setErrors({})
    }
  }, [open, subject])

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}
    if (!name.trim()) newErrors.name = 'Name is required'
    if (!startDate) newErrors.startDate = 'Start date is required'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return

    setSaving(true)
    try {
      const data = { name: name.trim(), start_date: startDate }

      if (isEditing && subject) {
        await updateSubject(subject.id, data)
        toast({ title: 'Chapter updated', description: `"${data.name}" has been updated.` })
      } else {
        await createSubject(data)
        toast({ title: 'Chapter created', description: `"${data.name}" has been created.` })
      }

      onSuccess()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An error occurred'

      if (message.toLowerCase().includes('already exists')) {
        setErrors({ name: message })
      } else {
        toast({ title: 'Error', description: message, variant: 'destructive' })
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-[95vw] sm:max-w-[425px] max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit}>
          <DialogHeader className="pb-4">
            <DialogTitle className="text-lg sm:text-xl">
              {isEditing ? 'Edit Chapter' : 'Add Chapter'}
            </DialogTitle>
            <DialogDescription className="text-sm">
              {isEditing
                ? 'Update the chapter details below.'
                : 'New chapters start at Medium difficulty - the app adjusts from there based on how each review goes.'}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label htmlFor="name" className="text-sm font-medium">
                Name
              </Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Cardiology"
                className={`h-11 ${errors.name ? 'border-destructive' : ''}`}
              />
              {errors.name && <p className="text-sm text-destructive">{errors.name}</p>}
            </div>

            <div className="grid gap-2">
              <Label htmlFor="startDate" className="text-sm font-medium">
                Start Date
              </Label>
              <Input
                id="startDate"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className={`h-11 ${errors.startDate ? 'border-destructive' : ''}`}
              />
              {errors.startDate && <p className="text-sm text-destructive">{errors.startDate}</p>}
            </div>
          </div>

          <DialogFooter className="flex-col-reverse sm:flex-row gap-2 pt-4">
            <Button type="button" variant="outline" onClick={onClose} disabled={saving} className="w-full sm:w-auto">
              Cancel
            </Button>
            <Button type="submit" disabled={saving} className="w-full sm:w-auto">
              {saving ? 'Saving...' : isEditing ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
