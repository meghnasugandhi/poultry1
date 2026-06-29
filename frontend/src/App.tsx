import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import { LanguageProvider } from './contexts/LanguageContext'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import InventoryPage from './pages/InventoryPage'
import DocumentsPage from './pages/DocumentsPage'
import FinancePage from './pages/FinancePage'
import ReportsPage from './pages/ReportsPage'
import CalculatorPage from './pages/CalculatorPage'
import AssistantPage from './pages/AssistantPage'
import NotificationsPage from './pages/NotificationsPage'
import SettingsPage from './pages/SettingsPage'
import VoicePage from './pages/VoicePage'

function AppRoutes() {
  return (
    <LanguageProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/inventory" element={<InventoryPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/finance" element={<FinancePage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/calculator" element={<CalculatorPage />} />
            <Route path="/assistant" element={<AssistantPage />} />
            <Route path="/notifications" element={<NotificationsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/voice" element={<VoicePage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </LanguageProvider>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ThemeProvider>
          <AppRoutes />
        </ThemeProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
