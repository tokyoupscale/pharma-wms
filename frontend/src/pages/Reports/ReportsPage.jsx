import { useEffect, useState } from 'react'
import {
  Table, Button, Select, Typography, Space, Tag,
  DatePicker, Collapse, Empty, message, Tabs,
} from 'antd'
import { BarChartOutlined, ReloadOutlined, SearchOutlined, WarningOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { getProductCard, getStockBySubgroup, getLowStock } from '../../api/reports'
import { getOperationsLog } from '../../api/operationsLog'
import { getProducts } from '../../api/references'
import { OPERATION_LABELS, OPERATION_COLORS } from '../../constants'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

/* ─── Карточка учёта товара ─── */
function ProductCardTab() {
  const [products, setProducts]   = useState([])
  const [productId, setProductId] = useState(null)
  const [dates, setDates]         = useState(null)
  const [report, setReport]       = useState(null)
  const [loading, setLoading]     = useState(false)

  useEffect(() => {
    getProducts().then(r => setProducts(r.data)).catch(() => {})
  }, [])

  const run = async () => {
    if (!productId) { message.warning('Выберите товар'); return }
    setLoading(true)
    try {
      const params = {}
      if (dates?.[0]) params.date_from = dates[0].format('YYYY-MM-DD')
      if (dates?.[1]) params.date_to   = dates[1].format('YYYY-MM-DD')
      const r = await getProductCard(productId, params)
      setReport(r.data)
    } catch { message.error('Ошибка получения данных') }
    finally { setLoading(false) }
  }

  const cols = [
    { title: 'Дата', dataIndex: 'date', width: 110, render: v => dayjs(v).format('DD.MM.YYYY') },
    { title: 'Документ', dataIndex: 'document_number', width: 140, render: v => v ?? '—' },
    { title: 'Контрагент', dataIndex: 'counterparty' },
    {
      title: 'Операция', dataIndex: 'operation',
      render: v => <Tag color={OPERATION_COLORS?.[v] ?? 'default'}>{OPERATION_LABELS[v] ?? v}</Tag>,
    },
    { title: 'Приход', dataIndex: 'income', width: 90, render: v => v ? <Text type="success">+{v}</Text> : '—' },
    { title: 'Расход', dataIndex: 'expense', width: 90, render: v => v ? <Text type="danger">−{v}</Text> : '—' },
    { title: 'Остаток', dataIndex: 'balance', width: 90, render: v => <Text strong>{v}</Text> },
    { title: 'Кто создал', dataIndex: 'created_by', width: 150, render: v => v ?? '—' },
  ]

  const productOptions = products.map(p => ({
    value: p.id,
    label: `${p.name}${p.nomenclature_code ? ` (${p.nomenclature_code})` : ''}`,
  }))

  return (
    <>
      <Space style={{ marginBottom: 16 }} wrap>
        <Select showSearch optionFilterProp="label" placeholder="Выберите товар"
          style={{ width: 300 }} options={productOptions} onChange={setProductId} />
        <RangePicker format="DD.MM.YYYY" onChange={setDates} />
        <Button type="primary" icon={<SearchOutlined />} onClick={run} loading={loading}>
          Построить
        </Button>
      </Space>

      {report ? (
        <>
          <Space style={{ marginBottom: 12 }} size={24}>
            <Text><b>Товар:</b> {report.product_name}</Text>
            <Text><b>Код:</b> {report.nomenclature_code ?? '—'}</Text>
            <Text><b>Ед.:</b> {report.unit}</Text>
            <Text><b>Текущий остаток:</b> <Text strong>{report.current_balance}</Text></Text>
          </Space>
          <Table rowKey={(_, i) => i} columns={cols} dataSource={report.entries}
            size="small" pagination={{ pageSize: 50 }} />
        </>
      ) : (
        <Empty description="Выберите товар и нажмите «Построить»" />
      )}
    </>
  )
}

/* ─── Остатки по подгруппам ─── */
function StockBySubgroupTab() {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try { const r = await getStockBySubgroup(); setData(r.data) }
    catch { message.error('Ошибка загрузки') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const cols = [
    { title: 'Код', dataIndex: 'nomenclature_code', width: 100 },
    { title: 'Название', dataIndex: 'name' },
    { title: 'Ед.', dataIndex: 'unit', width: 60 },
    { title: 'Остаток', dataIndex: 'current_stock', width: 90 },
    { title: 'Мин.', dataIndex: 'min_stock', width: 70 },
    {
      title: '', dataIndex: 'low_stock', width: 90,
      render: v => v ? <Tag color="red" icon={<WarningOutlined />}>Мало</Tag> : null,
    },
  ]

  const items = data
    ? Object.entries(data).map(([group, products]) => ({
        key: group,
        label: <Text strong>{group} ({products.length})</Text>,
        children: (
          <Table rowKey="id" columns={cols} dataSource={products} size="small"
            pagination={false}
            rowClassName={r => r.low_stock ? 'ant-table-row-low-stock' : ''}
          />
        ),
      }))
    : []

  return (
    <>
      <Button icon={<ReloadOutlined />} onClick={load} loading={loading} style={{ marginBottom: 12 }}>
        Обновить
      </Button>
      {data
        ? (items.length ? <Collapse items={items} defaultActiveKey={items.map(i => i.key)} /> : <Empty />)
        : <Empty description="Загрузка..." />}
    </>
  )
}

/* ─── Малый остаток ─── */
function LowStockTab() {
  const [rows, setRows]       = useState([])
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try { const r = await getLowStock(); setRows(r.data) }
    catch { message.error('Ошибка загрузки') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const cols = [
    { title: 'Код', dataIndex: 'nomenclature_code', width: 100 },
    { title: 'Название', dataIndex: 'name' },
    { title: 'Ед.', dataIndex: 'unit', width: 60 },
    { title: 'Остаток', dataIndex: 'current_stock', width: 90, render: v => <Text type="danger" strong>{v}</Text> },
    { title: 'Минимум', dataIndex: 'min_stock', width: 90 },
    {
      title: 'Дефицит', width: 100,
      render: (_, r) => <Text type="danger">−{(r.min_stock - r.current_stock).toFixed(2)}</Text>,
    },
  ]

  return (
    <>
      <Button icon={<ReloadOutlined />} onClick={load} loading={loading} style={{ marginBottom: 12 }}>
        Обновить
      </Button>
      {rows.length > 0 && (
        <Tag color="red" style={{ marginBottom: 12, marginLeft: 8 }}>
          <WarningOutlined /> Позиций с малым остатком: {rows.length}
        </Tag>
      )}
      <Table rowKey="id" columns={cols} dataSource={rows} loading={loading}
        size="small" pagination={false} locale={{ emptyText: '✓ Всё в норме' }} />
    </>
  )
}

/* ─── История по товару (операционный журнал) ─── */
const OP_STATUS_COLORS = { confirmed: 'green', active: 'default', cancelled: 'red' }
const OP_STATUS_LABELS = { confirmed: 'Подтверждена', active: 'Активна', cancelled: 'Отменена' }

function ProductHistoryTab() {
  const [products, setProducts]   = useState([])
  const [productId, setProductId] = useState(null)
  const [rows, setRows]           = useState([])
  const [total, setTotal]         = useState(0)
  const [loading, setLoading]     = useState(false)
  const [page, setPage]           = useState(1)
  const PAGE_SIZE = 50

  useEffect(() => {
    getProducts().then(r => setProducts(r.data)).catch(() => {})
  }, [])

  const load = async (pid = productId, p = page) => {
    if (!pid) return
    setLoading(true)
    try {
      const r = await getOperationsLog({ product_id: pid, skip: (p - 1) * PAGE_SIZE, limit: PAGE_SIZE })
      setRows(r.data.items)
      setTotal(r.data.total)
    } catch { message.error('Ошибка загрузки') }
    finally { setLoading(false) }
  }

  const handleProduct = (id) => {
    setProductId(id)
    setPage(1)
    load(id, 1)
  }

  const cols = [
    { title: 'Дата', dataIndex: 'date', width: 130, render: v => dayjs(v).format('DD.MM.YYYY HH:mm') },
    {
      title: 'Операция', dataIndex: 'operation_type', width: 150,
      render: v => <Tag color={OPERATION_COLORS?.[v] ?? 'default'}>{OPERATION_LABELS[v] ?? v}</Tag>,
    },
    {
      title: 'Количество', dataIndex: 'quantity', width: 110,
      render: (v, r) => r.direction === 'income'
        ? <Text type="success">+{v}</Text>
        : <Text type="danger">−{v}</Text>,
    },
    { title: 'Контрагент', dataIndex: 'counterparty' },
    { title: 'Документ', dataIndex: 'document_number', width: 130, render: v => v ?? '—' },
    { title: 'Кто создал', dataIndex: 'created_by', width: 150 },
    {
      title: 'Статус', dataIndex: 'status', width: 120,
      render: v => <Tag color={OP_STATUS_COLORS[v] ?? 'default'}>{OP_STATUS_LABELS[v] ?? v}</Tag>,
    },
  ]

  const productOptions = products.map(p => ({
    value: p.id,
    label: `${p.name}${p.nomenclature_code ? ` (${p.nomenclature_code})` : ''}`,
  }))

  return (
    <>
      <Space style={{ marginBottom: 16 }} wrap>
        <Select showSearch optionFilterProp="label" placeholder="Выберите товар"
          style={{ width: 300 }} options={productOptions} onChange={handleProduct} />
      </Space>

      {productId ? (
        <Table
          rowKey="id"
          columns={cols}
          dataSource={rows}
          loading={loading}
          size="small"
          pagination={{
            total, pageSize: PAGE_SIZE, current: page,
            onChange: p => { setPage(p); load(productId, p) },
            showTotal: t => `Всего: ${t}`,
          }}
          locale={{ emptyText: 'Нет операций по этому товару' }}
        />
      ) : (
        <Empty description="Выберите товар для просмотра истории" />
      )}
    </>
  )
}

/* ─── Main ─── */
export default function ReportsPage() {
  const tabItems = [
    { key: 'card',     label: 'Карточка учёта',        children: <ProductCardTab /> },
    { key: 'subgroup', label: 'Остатки по подгруппам',  children: <StockBySubgroupTab /> },
    { key: 'lowstock', label: <><WarningOutlined /> Малый остаток</>, children: <LowStockTab /> },
    { key: 'history',  label: 'История по товару',      children: <ProductHistoryTab /> },
  ]

  return (
    <>
      <Title level={4} style={{ marginTop: 0 }}>
        <BarChartOutlined style={{ marginRight: 8 }} />
        Отчёты
      </Title>
      <Tabs items={tabItems} />
    </>
  )
}
