/**
 * Metrics Page
 *
 * Category distribution pie chart plus a few other at-a-glance stats.
 */

import { useEffect, useState } from 'react'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { RefreshCw } from 'lucide-react'
import { getMetrics, type Metrics } from '@/lib/api'

const CATEGORY_COLORS: Record<string, string> = {
  Hard: '#ef4444',
  Medium: '#eab308',
  Easy: '#22c55e',
}

export function MetricsPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMetrics()
      .then(setMetrics)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!metrics) {
    return <p className="text-center text-muted-foreground py-12">Failed to load metrics.</p>
  }

  const pieData = [
    { name: 'Hard', value: metrics.category_distribution.HARD },
    { name: 'Medium', value: metrics.category_distribution.MEDIUM },
    { name: 'Easy', value: metrics.category_distribution.EASY },
  ]
  const hasChapters = metrics.total_chapters > 0

  return (
    <div className="space-y-4 sm:space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Metrics</h1>
        <p className="text-sm sm:text-base text-muted-foreground mt-1">
          An overview of where your chapters stand.
        </p>
      </div>

      <div className="grid gap-3 sm:gap-4 grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Chapters" value={metrics.total_chapters} />
        <StatCard label="Overdue" value={metrics.overdue_count} />
        <StatCard label="Avg Sessions / Chapter" value={metrics.average_sessions_per_chapter} />
        <StatCard label="Total Sessions" value={metrics.total_sessions} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Category Distribution</CardTitle>
          <CardDescription>Hard / Medium / Easy across all chapters</CardDescription>
        </CardHeader>
        <CardContent>
          {hasChapters ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label>
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={CATEGORY_COLORS[entry.name]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-12">No chapters yet.</p>
          )}
        </CardContent>
      </Card>

      {metrics.final_recall_reached_count > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Final Reread Progress</CardTitle>
            <CardDescription>Chapters that reached their Final Active Recall</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">{metrics.reread_completed_count}</span> of{' '}
              <span className="font-medium text-foreground">{metrics.final_recall_reached_count}</span> completed
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <CardContent className="py-3 sm:py-4">
        <p className="text-xl sm:text-2xl font-bold">{value}</p>
        <p className="text-xs sm:text-sm text-muted-foreground">{label}</p>
      </CardContent>
    </Card>
  )
}
