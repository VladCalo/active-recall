/**
 * Subjects Page
 * 
 * Lists all study subjects with options to add, edit, and delete.
 * Responsive design: Cards on mobile, table on desktop.
 */

import { useEffect, useState } from 'react'
import { Plus, Pencil, Trash2, Calendar, Clock, RefreshCw, ChevronRight } from 'lucide-react'
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
import { formatDate } from '@/lib/utils'
import { useToast } from '@/hooks/use-toast'

const CATEGORY_STYLES: Record<string, string> = {
  HARD: 'bg-red-100 text-red-700 border-red-200',
  MEDIUM: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  EASY: 'bg-green-100 text-green-700 border-green-200',
}

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
    <div className="space-y-4 sm:space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Subjects</h1>
          <p className="text-sm sm:text-base text-muted-foreground mt-1">
            Manage your study subjects and their review schedules
          </p>
        </div>
        <div className="flex flex-col sm:flex-row gap-2 sm:gap-2">
          <Button 
            variant="outline" 
            size="default"
            onClick={fetchSubjects}
            disabled={loading}
            className="w-full sm:w-auto"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button onClick={handleAddClick} className="w-full sm:w-auto">
            <Plus className="h-4 w-4 mr-2" />
            Add Subject
          </Button>
        </div>
      </div>

      {/* Subjects List/Table */}
      <Card>
        <CardHeader className="pb-3 sm:pb-6">
          <CardTitle className="text-lg sm:text-xl">All Subjects</CardTitle>
          <CardDescription>
            {subjects.length} subject{subjects.length !== 1 ? 's' : ''} total
          </CardDescription>
        </CardHeader>
        <CardContent className="p-3 sm:p-6 pt-0 sm:pt-0">
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
            <>
              {/* Mobile: Card List */}
              <div className="block lg:hidden space-y-3">
                {subjects.map((subject) => (
                  <SubjectCard
                    key={subject.id}
                    subject={subject}
                    onEdit={() => handleEditClick(subject)}
                    onDelete={() => handleDeleteClick(subject.id)}
                  />
                ))}
              </div>
              
              {/* Desktop: Table */}
              <div className="hidden lg:block overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-3 font-medium">Name</th>
                      <th className="pb-3 font-medium">Start Date</th>
                      <th className="pb-3 font-medium">Category</th>
                      <th className="pb-3 font-medium">Sessions</th>
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
            </>
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
        <AlertDialogContent className="max-w-[95vw] sm:max-w-lg mx-auto">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Subject</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;{subjectToDelete?.name}&quot;? 
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="flex-col sm:flex-row gap-2">
            <AlertDialogCancel disabled={deleting} className="w-full sm:w-auto">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              disabled={deleting}
              className="w-full sm:w-auto bg-destructive text-destructive-foreground hover:bg-destructive/90"
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
 * Mobile card view for a subject.
 */
function SubjectCard({ 
  subject, 
  onEdit, 
  onDelete 
}: { 
  subject: Subject
  onEdit: () => void
  onDelete: () => void 
}) {
  return (
    <div className="border rounded-lg p-4 hover:bg-muted/50 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-medium truncate">{subject.name}</h3>
            <Badge className={`text-xs border ${CATEGORY_STYLES[subject.category]}`}>
              {subject.is_final_recall_reached ? 'FINAL' : subject.category}
            </Badge>
          </div>
          
          <div className="mt-2 space-y-1.5 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <Calendar className="h-3.5 w-3.5 flex-shrink-0" />
              <span>Started: {formatDate(subject.start_date)}</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="h-3.5 w-3.5 flex-shrink-0" />
              <span className="truncate">{subject.total_active_recall_count} session{subject.total_active_recall_count !== 1 ? 's' : ''}</span>
            </div>
            <div className="flex items-center gap-2">
              <ChevronRight className="h-3.5 w-3.5 flex-shrink-0" />
              <span>
                Next: {subject.next_due_date ? (
                  <Badge variant="default" className="ml-1 text-xs">
                    {formatDate(subject.next_due_date)}
                  </Badge>
                ) : (
                  <span className="text-muted-foreground">Completed</span>
                )}
              </span>
            </div>
          </div>
        </div>
        
        <div className="flex flex-col gap-1">
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={onEdit}
            className="h-9 w-9"
          >
            <Pencil className="h-4 w-4" />
            <span className="sr-only">Edit</span>
          </Button>
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={onDelete}
            className="h-9 w-9"
          >
            <Trash2 className="h-4 w-4 text-destructive" />
            <span className="sr-only">Delete</span>
          </Button>
        </div>
      </div>
    </div>
  )
}

/**
 * Desktop table row for a subject.
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
      </td>
      <td className="py-4">
        <div className="flex items-center gap-2 text-sm">
          <Calendar className="h-4 w-4 text-muted-foreground" />
          {formatDate(subject.start_date)}
        </div>
      </td>
      <td className="py-4">
        <Badge className={`border ${CATEGORY_STYLES[subject.category]}`}>
          {subject.is_final_recall_reached ? 'FINAL' : subject.category}
        </Badge>
      </td>
      <td className="py-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Clock className="h-4 w-4" />
          {subject.total_active_recall_count}
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
        <div className="flex items-center justify-end gap-1">
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
