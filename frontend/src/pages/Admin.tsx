/**
 * Admin Page
 * 
 * Admin dashboard with system stats and user management.
 * Only accessible to users with is_admin=true.
 */

import { useEffect, useState, useCallback } from 'react'
import {
  Users,
  BookOpen,
  CalendarDays,
  Activity,
  RefreshCw,
  Search,
  Shield,
  ShieldOff,
  UserX,
  UserCheck,
  Trash2,
  ChevronLeft,
  ChevronRight,
  X,
  AlertTriangle,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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
import { useToast } from '@/hooks/use-toast'
import {
  getAdminStats,
  getAdminUsers,
  getAdminUserDetail,
  updateAdminUser,
  deleteAdminUser,
  getAdminTraffic,
  type AdminStats,
  type AdminUserListItem,
  type AdminUserDetail,
  type AdminTrafficStats,
} from '@/lib/api'
import { cn, formatDate } from '@/lib/utils'

type Tab = 'dashboard' | 'users'

export function Admin() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard')
  
  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Admin Panel</h1>
        <p className="text-sm sm:text-base text-muted-foreground mt-1">
          System management and user administration
        </p>
      </div>
      
      {/* Tab Navigation */}
      <div className="flex gap-2 border-b">
        <button
          onClick={() => setActiveTab('dashboard')}
          className={cn(
            'px-4 py-2 text-sm font-medium border-b-2 transition-colors',
            activeTab === 'dashboard'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          <Activity className="h-4 w-4 inline-block mr-2" />
          Dashboard
        </button>
        <button
          onClick={() => setActiveTab('users')}
          className={cn(
            'px-4 py-2 text-sm font-medium border-b-2 transition-colors',
            activeTab === 'users'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          )}
        >
          <Users className="h-4 w-4 inline-block mr-2" />
          Users
        </button>
      </div>
      
      {/* Tab Content */}
      {activeTab === 'dashboard' ? <AdminDashboard /> : <UserManagement />}
    </div>
  )
}

/**
 * Admin Dashboard with stats
 */
function AdminDashboard() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [traffic, setTraffic] = useState<AdminTrafficStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [statsData, trafficData] = await Promise.all([
        getAdminStats(),
        getAdminTraffic(24),
      ])
      setStats(statsData)
      setTraffic(trafficData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load stats')
    } finally {
      setLoading(false)
    }
  }, [])
  
  useEffect(() => {
    fetchData()
  }, [fetchData])
  
  if (loading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[...Array(8)].map((_, i) => (
          <Card key={i}>
            <CardContent className="py-6">
              <div className="h-16 bg-slate-200 rounded animate-pulse" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }
  
  if (error) {
    return (
      <Card className="border-destructive/50 bg-destructive/5">
        <CardContent className="flex items-center gap-3 py-6">
          <AlertTriangle className="h-5 w-5 text-destructive" />
          <p className="text-sm text-destructive">{error}</p>
          <Button variant="outline" size="sm" onClick={fetchData} className="ml-auto">
            Retry
          </Button>
        </CardContent>
      </Card>
    )
  }
  
  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={Users}
          label="Total Users"
          value={stats?.total_users ?? 0}
          description={`${stats?.admin_count ?? 0} admins, ${stats?.disabled_users ?? 0} disabled`}
          iconColor="text-blue-600"
          iconBg="bg-blue-100"
        />
        <StatCard
          icon={BookOpen}
          label="Total Subjects"
          value={stats?.total_subjects ?? 0}
          description={`${stats?.subjects_created_last_7_days ?? 0} created this week`}
          iconColor="text-green-600"
          iconBg="bg-green-100"
        />
        <StatCard
          icon={CalendarDays}
          label="Reviews Due Today"
          value={stats?.reviews_due_today_total ?? 0}
          description="Across all users"
          iconColor="text-orange-600"
          iconBg="bg-orange-100"
        />
        <StatCard
          icon={Activity}
          label="Active Users (7d)"
          value={stats?.active_users_last_7_days ?? 0}
          description="Logged in this week"
          iconColor="text-purple-600"
          iconBg="bg-purple-100"
        />
      </div>
      
      {/* Traffic Stats */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg">Traffic (Last 24h)</CardTitle>
              <CardDescription>Request metrics and performance</CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={fetchData}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="p-4 rounded-lg bg-slate-50">
              <p className="text-sm text-muted-foreground">Total Requests</p>
              <p className="text-2xl font-bold">{traffic?.request_count_total ?? 0}</p>
            </div>
            <div className="p-4 rounded-lg bg-slate-50">
              <p className="text-sm text-muted-foreground">Avg Latency</p>
              <p className="text-2xl font-bold">{traffic?.avg_latency_ms?.toFixed(1) ?? 0}ms</p>
            </div>
            <div className="p-4 rounded-lg bg-slate-50">
              <p className="text-sm text-muted-foreground">P95 Latency</p>
              <p className="text-2xl font-bold">{traffic?.p95_latency_ms?.toFixed(1) ?? 0}ms</p>
            </div>
            <div className="p-4 rounded-lg bg-slate-50">
              <p className="text-sm text-muted-foreground">Req/min</p>
              <p className="text-2xl font-bold">{traffic?.requests_per_minute?.toFixed(1) ?? 0}</p>
            </div>
          </div>
          
          {/* Status Code Distribution */}
          {traffic && Object.keys(traffic.status_code_counts).length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium mb-2">Status Codes</p>
              <div className="flex gap-2 flex-wrap">
                {Object.entries(traffic.status_code_counts).map(([code, count]) => (
                  <Badge
                    key={code}
                    variant={code === '2xx' ? 'default' : code === '4xx' ? 'secondary' : 'destructive'}
                  >
                    {code}: {count}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

/**
 * Stat card component
 */
function StatCard({
  icon: Icon,
  label,
  value,
  description,
  iconColor,
  iconBg,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: number
  description: string
  iconColor: string
  iconBg: string
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 py-4">
        <div className={cn('p-3 rounded-full', iconBg)}>
          <Icon className={cn('h-5 w-5', iconColor)} />
        </div>
        <div>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-sm font-medium">{label}</p>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
      </CardContent>
    </Card>
  )
}

/**
 * User Management component
 */
function UserManagement() {
  const [users, setUsers] = useState<AdminUserListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [selectedUser, setSelectedUser] = useState<AdminUserDetail | null>(null)
  const [userToDelete, setUserToDelete] = useState<AdminUserListItem | null>(null)
  const { toast } = useToast()
  
  const limit = 10
  
  const fetchUsers = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getAdminUsers(page * limit, limit, search || undefined)
      setUsers(data.users)
      setTotal(data.total)
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to load users',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }, [page, search, toast])
  
  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])
  
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(0)
    fetchUsers()
  }
  
  const handleViewUser = async (userId: string) => {
    try {
      const data = await getAdminUserDetail(userId)
      setSelectedUser(data)
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to load user details',
        variant: 'destructive',
      })
    }
  }
  
  const handleToggleAdmin = async (user: AdminUserListItem) => {
    try {
      await updateAdminUser(user.id, { is_admin: !user.is_admin })
      toast({
        title: 'Success',
        description: `${user.email} is ${user.is_admin ? 'no longer' : 'now'} an admin`,
      })
      fetchUsers()
      if (selectedUser?.id === user.id) {
        setSelectedUser({ ...selectedUser, is_admin: !user.is_admin })
      }
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to update user',
        variant: 'destructive',
      })
    }
  }
  
  const handleToggleDisabled = async (user: AdminUserListItem) => {
    try {
      await updateAdminUser(user.id, { is_disabled: !user.is_disabled })
      toast({
        title: 'Success',
        description: `${user.email} has been ${user.is_disabled ? 'enabled' : 'disabled'}`,
      })
      fetchUsers()
      if (selectedUser?.id === user.id) {
        setSelectedUser({ ...selectedUser, is_disabled: !user.is_disabled })
      }
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to update user',
        variant: 'destructive',
      })
    }
  }
  
  const handleDeleteUser = async () => {
    if (!userToDelete) return
    
    try {
      await deleteAdminUser(userToDelete.id)
      toast({
        title: 'User Deleted',
        description: `${userToDelete.email} has been deleted`,
      })
      setUserToDelete(null)
      fetchUsers()
      if (selectedUser?.id === userToDelete.id) {
        setSelectedUser(null)
      }
    } catch (err) {
      toast({
        title: 'Error',
        description: err instanceof Error ? err.message : 'Failed to delete user',
        variant: 'destructive',
      })
    }
  }
  
  const totalPages = Math.ceil(total / limit)
  
  return (
    <div className="space-y-4">
      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search by email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button type="submit" variant="outline">
          Search
        </Button>
        {search && (
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              setSearch('')
              setPage(0)
            }}
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </form>
      
      {/* Users Table/Cards */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground mx-auto" />
            </div>
          ) : users.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              No users found
            </div>
          ) : (
            <>
              {/* Desktop Table */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-medium">Email</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Subjects</th>
                      <th className="px-4 py-3 text-left text-sm font-medium">Last Login</th>
                      <th className="px-4 py-3 text-right text-sm font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((user) => (
                      <tr key={user.id} className="border-b last:border-0 hover:bg-slate-50">
                        <td className="px-4 py-3">
                          <button
                            onClick={() => handleViewUser(user.id)}
                            className="font-medium hover:underline text-left"
                          >
                            {user.email}
                          </button>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-1">
                            {user.is_admin && (
                              <Badge variant="default" className="text-xs">Admin</Badge>
                            )}
                            {user.is_disabled && (
                              <Badge variant="destructive" className="text-xs">Disabled</Badge>
                            )}
                            {!user.is_admin && !user.is_disabled && (
                              <Badge variant="secondary" className="text-xs">User</Badge>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm">{user.subject_count}</td>
                        <td className="px-4 py-3 text-sm text-muted-foreground">
                          {user.last_login_at ? formatDate(user.last_login_at) : 'Never'}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleToggleAdmin(user)}
                              title={user.is_admin ? 'Remove admin' : 'Make admin'}
                            >
                              {user.is_admin ? (
                                <ShieldOff className="h-4 w-4" />
                              ) : (
                                <Shield className="h-4 w-4" />
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleToggleDisabled(user)}
                              title={user.is_disabled ? 'Enable' : 'Disable'}
                            >
                              {user.is_disabled ? (
                                <UserCheck className="h-4 w-4" />
                              ) : (
                                <UserX className="h-4 w-4" />
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => setUserToDelete(user)}
                              className="text-destructive hover:text-destructive"
                              title="Delete user"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {/* Mobile Cards */}
              <div className="md:hidden divide-y">
                {users.map((user) => (
                  <div key={user.id} className="p-4 space-y-3">
                    <div className="flex items-start justify-between">
                      <button
                        onClick={() => handleViewUser(user.id)}
                        className="font-medium hover:underline text-left"
                      >
                        {user.email}
                      </button>
                      <div className="flex gap-1">
                        {user.is_admin && <Badge variant="default" className="text-xs">Admin</Badge>}
                        {user.is_disabled && <Badge variant="destructive" className="text-xs">Disabled</Badge>}
                      </div>
                    </div>
                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                      <span>{user.subject_count} subjects</span>
                      <span>{user.last_login_at ? formatDate(user.last_login_at) : 'Never logged in'}</span>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleToggleAdmin(user)}
                      >
                        {user.is_admin ? <ShieldOff className="h-4 w-4 mr-1" /> : <Shield className="h-4 w-4 mr-1" />}
                        {user.is_admin ? 'Remove Admin' : 'Make Admin'}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleToggleDisabled(user)}
                      >
                        {user.is_disabled ? <UserCheck className="h-4 w-4 mr-1" /> : <UserX className="h-4 w-4 mr-1" />}
                        {user.is_disabled ? 'Enable' : 'Disable'}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setUserToDelete(user)}
                        className="text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>
      
      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {page * limit + 1}-{Math.min((page + 1) * limit, total)} of {total}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
      
      {/* User Detail Dialog */}
      <Dialog open={!!selectedUser} onOpenChange={() => setSelectedUser(null)}>
        <DialogContent className="max-w-md max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>User Details</DialogTitle>
            <DialogDescription>{selectedUser?.email}</DialogDescription>
          </DialogHeader>
          {selectedUser && (
            <div className="space-y-4">
              <div className="flex gap-2">
                {selectedUser.is_admin && <Badge>Admin</Badge>}
                {selectedUser.is_disabled && <Badge variant="destructive">Disabled</Badge>}
                {!selectedUser.is_admin && !selectedUser.is_disabled && <Badge variant="secondary">User</Badge>}
              </div>
              
              <div className="grid gap-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Created</span>
                  <span>{selectedUser.created_at ? formatDate(selectedUser.created_at) : 'Unknown'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Last Login</span>
                  <span>{selectedUser.last_login_at ? formatDate(selectedUser.last_login_at) : 'Never'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Failed Logins</span>
                  <span>{selectedUser.failed_login_attempts}</span>
                </div>
                {selectedUser.locked_until && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Locked Until</span>
                    <span>{formatDate(selectedUser.locked_until)}</span>
                  </div>
                )}
              </div>
              
              <div>
                <p className="font-medium mb-2">Subjects ({selectedUser.subject_count})</p>
                {selectedUser.subjects.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No subjects</p>
                ) : (
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {selectedUser.subjects.map((subject) => (
                      <div
                        key={subject.id}
                        className="text-sm p-2 bg-slate-50 rounded flex justify-between"
                      >
                        <span>{subject.name}</span>
                        <Badge variant="outline" className="text-xs">{subject.category}</Badge>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedUser(null)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!userToDelete} onOpenChange={() => setUserToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete User?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete <strong>{userToDelete?.email}</strong> and all their data.
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteUser}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
