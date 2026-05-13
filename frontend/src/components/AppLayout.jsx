import { useEffect, useState } from 'react'
import { Layout, Menu, Button, Space, Typography, Avatar, theme as antTheme, Badge, Tooltip } from 'antd'
import {
  InboxOutlined,
  ExportOutlined,
  FileTextOutlined,
  OrderedListOutlined,
  BarChartOutlined,
  AppstoreOutlined,
  HistoryOutlined,
  DashboardOutlined,
  WarningOutlined,
  MoonOutlined,
  SunOutlined,
  LogoutOutlined,
  UserOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { useThemeStore } from '../store/themeStore'
import { getLowStock } from '../api/reports'
import { logoutApi } from '../api/auth'

const { Sider, Header, Content } = Layout
const { Text } = Typography

const ALL_NAV = [
  { key: '/dashboard',      icon: <DashboardOutlined />,    label: 'Сводка',            roles: null },
  { key: '/supply',         icon: <InboxOutlined />,        label: 'Приход',             roles: ['admin', 'omts'] },
  { key: '/expense',        icon: <ExportOutlined />,       label: 'Расход',             roles: ['admin', 'omts', 'quality', 'quality_assurance'] },
  { key: '/limit-card',     icon: <FileTextOutlined />,     label: 'ЛЗК',               roles: ['admin', 'omts'] },
  { key: '/requests',       icon: <OrderedListOutlined />,  label: 'Заявки',             roles: ['admin', 'omts', 'workshop_afs', 'workshop_gls'] },
  { key: '/reports',        icon: <BarChartOutlined />,     label: 'Отчёты',             roles: null },
  { key: '/operations-log', icon: <HistoryOutlined />,      label: 'Журнал операций',    roles: ['admin', 'omts', 'planning'] },
  { key: '/references',     icon: <AppstoreOutlined />,     label: 'Справочники',        roles: null },
  { key: '/users',          icon: <TeamOutlined />,         label: 'Пользователи',       roles: ['admin', 'omts'] },
]

function buildNavItems(role) {
  return ALL_NAV.filter(item => item.roles === null || item.roles.includes(role))
}

export default function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { logout, user } = useAuthStore()
  const { isDark, toggle } = useThemeStore()
  const { token } = antTheme.useToken()
  const [lowStockCount, setLowStockCount] = useState(0)

  const navItems = buildNavItems(user?.role)

  useEffect(() => {
    const fetchLowStock = () => {
      getLowStock()
        .then(r => setLowStockCount(r.data.length))
        .catch(() => {})
    }
    fetchLowStock()
    const id = setInterval(fetchLowStock, 60_000)
    return () => clearInterval(id)
  }, [])

  const handleLogout = () => {
    logoutApi().finally(() => {
      logout()
      navigate('/login')
    })
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={200}
        style={{ background: token.colorBgContainer, borderRight: `1px solid ${token.colorBorderSecondary}` }}
      >
        <div style={{ padding: '20px 16px 12px', borderBottom: `1px solid ${token.colorBorderSecondary}` }}>
          <Text strong style={{ fontSize: 14, color: token.colorPrimary }}>АО «Фармцентр ВИЛАР»</Text>
          <br />
          <Text type="secondary" style={{ fontSize: 11 }}>Складской учёт МТЗ</Text>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={navItems}
          onClick={({ key }) => navigate(key)}
          style={{ border: 'none', marginTop: 8 }}
        />
      </Sider>

      <Layout>
        <Header
          style={{
            background: token.colorBgContainer,
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            height: 52,
          }}
        >
          <Space size="middle">
            {lowStockCount > 0 && (
              <Tooltip title={`${lowStockCount} позиций с остатком ниже минимума`}>
                <Button
                  type="text"
                  danger
                  icon={
                    <Badge count={lowStockCount} size="small">
                      <WarningOutlined style={{ fontSize: 16, color: '#ff4d4f' }} />
                    </Badge>
                  }
                  onClick={() => navigate('/reports')}
                  style={{ paddingRight: 12 }}
                />
              </Tooltip>
            )}
            <Space size="small">
              <Avatar size="small" icon={<UserOutlined />} />
              <Text style={{ fontSize: 13 }}>{user?.full_name || user?.username || 'Пользователь'}</Text>
            </Space>
            <Button
              type="text"
              icon={isDark ? <SunOutlined /> : <MoonOutlined />}
              onClick={toggle}
              title={isDark ? 'Светлая тема' : 'Тёмная тема'}
            />
            <Button
              type="text"
              icon={<LogoutOutlined />}
              onClick={handleLogout}
              title="Выйти"
            />
          </Space>
        </Header>

        <Content style={{ padding: 24, background: token.colorBgLayout }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
