import { useEffect, useState } from 'react'
import { Row, Col, Card, Statistic, Typography, Spin, theme as antTheme } from 'antd'
import {
  InboxOutlined, MinusCircleOutlined, OrderedListOutlined, WarningOutlined,
  DashboardOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { getDashboardStats } from '../../api/reports'
import { useThemeStore } from '../../store/themeStore'

const { Title, Text } = Typography

export default function DashboardPage() {
  const [stats, setStats]     = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate  = useNavigate()
  const isDark    = useThemeStore(s => s.isDark)
  const { token } = antTheme.useToken()

  useEffect(() => {
    getDashboardStats()
      .then(r => setStats(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const cardStyle = (accentColor) => ({
    light: { bg: token.colorBgContainer, border: accentColor },
    dark:  { bg: token.colorBgElevated,  border: accentColor },
  })[isDark ? 'dark' : 'light']

  const cards = stats ? [
    {
      title: 'Приходов за месяц',
      value: stats.supplies_this_month,
      icon:  <InboxOutlined style={{ fontSize: 28, color: '#52c41a' }} />,
      accent: '#52c41a',
      path: '/supply',
    },
    {
      title: 'Расходов за месяц',
      value: stats.expenses_this_month,
      icon:  <MinusCircleOutlined style={{ fontSize: 28, color: '#00531c' }} />,
      accent: '#00531c',
      path: '/expense',
    },
    {
      title: 'Заявок в ожидании',
      value: stats.pending_requests,
      icon:  <OrderedListOutlined style={{ fontSize: 28, color: '#fa8c16' }} />,
      accent: '#fa8c16',
      path: '/requests',
    },
    {
      title: 'Позиций с малым остатком',
      value: stats.low_stock_count,
      icon:  <WarningOutlined style={{ fontSize: 28, color: stats.low_stock_count > 0 ? '#ff4d4f' : token.colorTextDisabled }} />,
      accent: stats.low_stock_count > 0 ? '#ff4d4f' : token.colorBorderSecondary,
      path: '/reports',
    },
  ] : []

  return (
    <>
      <Title level={4} style={{ marginTop: 0, marginBottom: 24 }}>
        <DashboardOutlined style={{ marginRight: 8 }} />
        Сводка по складу
      </Title>

      {loading ? (
        <Spin size="large" style={{ display: 'block', marginTop: 60, textAlign: 'center' }} />
      ) : (
        <Row gutter={[16, 16]}>
          {cards.map(c => {
            const { bg, border } = cardStyle(c.accent)
            return (
              <Col key={c.title} xs={24} sm={12} xl={6}>
                <Card
                  style={{ borderColor: border, background: bg, cursor: 'pointer' }}
                  styles={{ body: { padding: '20px 24px' } }}
                  onClick={() => navigate(c.path)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <Text type="secondary" style={{ fontSize: 13 }}>{c.title}</Text>
                      <Statistic
                        value={c.value}
                        valueStyle={{ fontSize: 36, fontWeight: 700, lineHeight: 1.2, color: token.colorText }}
                      />
                    </div>
                    <div style={{ marginTop: 4 }}>{c.icon}</div>
                  </div>
                </Card>
              </Col>
            )
          })}
        </Row>
      )}

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Текущий месяц · нажмите на карточку для перехода
          </Text>
        </Col>
      </Row>
    </>
  )
}
