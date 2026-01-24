/**
 * Root Application Component
 * 
 * This component sets up the main layout and routing for the application.
 * It provides the navigation header and routes to different pages.
 */

import { Routes, Route } from 'react-router-dom'
import { Toaster } from '@/components/ui/toaster'
import { Layout } from '@/components/Layout'
import { Dashboard } from '@/pages/Dashboard'
import { Subjects } from '@/pages/Subjects'

function App() {
  return (
    <>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/subjects" element={<Subjects />} />
        </Routes>
      </Layout>
      <Toaster />
    </>
  )
}

export default App
