import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, theme as antTheme } from 'antd'
import ruRU from 'antd/locale/ru_RU'
import { useThemeStore } from './store/themeStore'
import ProtectedRoute from './components/ProtectedRoute'
import AppLayout from './components/AppLayout'
import LoginPage from './pages/Login/LoginPage'
import SupplyPage from './pages/Supply/SupplyPage'
import ExpensePage from './pages/Expense/ExpensePage'
import LimitCardPage from './pages/LimitCard/LimitCardPage'
import RequestsPage from './pages/Requests/RequestsPage'
import ReportsPage from './pages/Reports/ReportsPage'
import ReferencesPage from './pages/References/ReferencesPage'
import OperationsLogPage from './pages/OperationsLog/OperationsLogPage'
import DashboardPage from './pages/Dashboard/DashboardPage'
import UsersPage from './pages/Users/UsersPage'

export default function App() {
  const isDark = useThemeStore((s) => s.isDark)

  return (
    <ConfigProvider
      locale={ruRU}
      theme={{
        algorithm: isDark ? antTheme.darkAlgorithm : antTheme.defaultAlgorithm,
        token: {
          colorPrimary: '#00531c',
          borderRadius: 6,
        },
      }}
    >
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="supply"     element={<SupplyPage />} />
            <Route path="expense"    element={<ExpensePage />} />
            <Route path="limit-card" element={<LimitCardPage />} />
            <Route path="requests"   element={<RequestsPage />} />
            <Route path="reports"    element={<ReportsPage />} />
            <Route path="references"      element={<ReferencesPage />} />
            <Route path="operations-log"  element={<OperationsLogPage />} />
            <Route path="users"           element={<UsersPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  )
}
