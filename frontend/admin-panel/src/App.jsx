import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import Layout from './components/layout/Layout'
import LoginPage from './pages/auth/LoginPage'
import DashboardPage from './pages/dashboard/DashboardPage'
import BriefsPage from './pages/briefs/BriefsPage'
import BriefEditPage from './pages/briefs/BriefEditPage'
import KnowledgePage from './pages/knowledge/KnowledgePage'
import DialogsPage from './pages/dialogs/DialogsPage'
import AnalyticsPage from './pages/analytics/AnalyticsPage'
import SettingsPage from './pages/settings/SettingsPage'

function PrivateRoute({ children }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  return isAuthenticated ? children : <Navigate to="/login" />
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Layout />
          </PrivateRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="briefs" element={<BriefsPage />} />
        <Route path="briefs/:id" element={<BriefEditPage />} />
        <Route path="briefs/new" element={<BriefEditPage />} />
        <Route path="knowledge" element={<KnowledgePage />} />
        <Route path="dialogs" element={<DialogsPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}

export default App
