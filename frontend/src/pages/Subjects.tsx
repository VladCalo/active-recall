/**
 * Subjects Page
 * 
 * Lists all study subjects with options to add, edit, and delete.
 * Shows computed next due date for each subject.
 */

import { useEffect, useState } from 'react'
import { Plus, Pencil, Trash2, Calendar, Clock, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { SubjectDialog } from '@/components/SubjectDialog'
import { getSubjects, deleteSubject, type Subject } from '@/lib/api'
import { formatDate, formatIntervals } from '@/lib/utils'
import { useToast } from '@/hooks/use-toast'

export function Subjects() {
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingSubject, setEditingSubject] = useState<Subject | null>(null)
  
  // Delete confirmation state
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  
  const { toast } = useToast()

  const fetchSubjects = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getSubjects()
      setSubjects(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load subjects')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSubjects()
  }, [])

  const handleAddClick = () => {
    setEditingSubject(null)
    setDialogOpen(true)
  }

  const handleEditClick = (subject: Subject) => {
    setEditingSubject(subject)
    setDialogOpen(true)
  }

  const handleDialogClose = () => {
    setDialogOpen(false)
    setEditingSubject(null)
  }

  const handleSaveSuccess = () => {
    fetchSubjects()
    handleDialogClose()
  }

  const handleDeleteClick = (id: string) => {
    setDeleteId(id)
  }

  const handleDeleteConfirm = async () => {
    if (!deleteId) return
    
    setDeleting(true)
    try {
      await deleteSubject(deleteId)
      toast({
        title: 'Subject deleted',
        description: 'The subject has been successfully deleted.',
      })
      fetchSubjects()
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to delete subject',
        variant: 'destructive',
      })
    } finally {
      setDeleting(false)
      setDeleteId(null)
    }
  }

  const subjectToDelete = subjects.find(s => s.id === deleteId)

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Subjects</h1>
          <p className="text-muted-foreground mt-1">
            Manage your study subjects and their review schedules
          </p>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={fetchSubjects}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button onClick={handleAddClick}>
            <Plus className="h-4 w-4 mr-2" />
            Add Subject
          </Button>
        </div>
      </div>

      {/* Subjects List */}
      <Card>
        <CardHeader>
          <CardTitle>All Subjects</CardTitle>
          <CardDescription>
            {subjects.length} subject{subjects.length !== 1 ? 's' : ''} total
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
              <Button variant="outline" onClick={fetchSubjects}>
                Try Again
              </Button>
            </div>
          ) : subjects.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground mb-4">
                No subjects yet. Add your first subject to get started!
              </p>
              <Button onClick={handleAddClick}>
                <Plus className="h-4 w-4 mr-2" />
                Add Subject
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b text-left">
                    <th className="pb-3 font-medium">Name</th>
                    <th className="pb-3 font-medium hidden sm:table-cell">Start Date</th>
                    <th className="pb-3 font-medium hidden md:table-cell">Schedule</th>
                    <th className="pb-3 font-medium hidden lg:table-cell">Intervals</th>
                    <th className="pb-3 font-medium">Next Due</th>
                    <th className="pb-3 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {subjects.map((subject) => (
                    <SubjectRow
                      key={subject.id}
                      subject={subject}
                      onEdit={() => handleEditClick(subject)}
                      onDelete={() => handleDeleteClick(subject.id)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add/Edit Dialog */}
      <SubjectDialog
        open={dialogOpen}
        onClose={handleDialogClose}
        onSuccess={handleSaveSuccess}
        subject={editingSubject}
      />

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteId} onOpenChange={(open) => !open && setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Subject</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;{subjectToDelete?.name}&quot;? 
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              disabled={deleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleting ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

/**
 * Table row component for a single subject.
 */
function SubjectRow({ 
  subject, 
  onEdit, 
  onDelete 
}: { 
  subject: Subject
  onEdit: () => void
  onDelete: () => void 
}) {
  return (
    <tr className="border-b last:border-0 hover:bg-muted/50">
      <td className="py-4">
        <div className="font-medium">{subject.name}</div>
        <div className="text-sm text-muted-foreground sm:hidden">
          Started: {formatDate(subject.start_date)}
        </div>
      </td>
      <td className="py-4 hidden sm:table-cell">
        <div className="flex items-center gap-2 text-sm">
          <Calendar className="h-4 w-4 text-muted-foreground" />
          {formatDate(subject.start_date)}
        </div>
      </td>
      <td className="py-4 hidden md:table-cell">
        <Badge variant={subject.schedule_type === 'CUSTOM' ? 'secondary' : 'outline'}>
          {subject.schedule_type}
        </Badge>
      </td>
      <td className="py-4 hidden lg:table-cell">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Clock className="h-4 w-4" />
          {formatIntervals(subject.intervals)}
        </div>
      </td>
      <td className="py-4">
        {subject.next_due_date ? (
          <Badge variant="default" className="whitespace-nowrap">
            {formatDate(subject.next_due_date)}
          </Badge>
        ) : (
          <span className="text-sm text-muted-foreground">Completed</span>
        )}
      </td>
      <td className="py-4">
        <div className="flex items-center justify-end gap-2">
          <Button variant="ghost" size="icon" onClick={onEdit}>
            <Pencil className="h-4 w-4" />
            <span className="sr-only">Edit</span>
          </Button>
          <Button variant="ghost" size="icon" onClick={onDelete}>
            <Trash2 className="h-4 w-4 text-destructive" />
            <span className="sr-only">Delete</span>
          </Button>
        </div>
      </td>
    </tr>
  )
}
