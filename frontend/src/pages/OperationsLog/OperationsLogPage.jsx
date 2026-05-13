import { useEffect, useState, useCallback } from 'react'
import {
  Table, Select, DatePicker, Button, Typography, Tag, Space, message,
} from 'antd'
import { HistoryOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { getOperationsLog } from '../../api/operationsLog'
import { getProducts } from '../../api/references'
import { OPERATION_LABELS } from '../../constants'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

const OPERATION_COLORS = {
  supply:      'green',
  requirement: 'blue',
  sampling:    'purple',
  writeoff:    'orange',
}

const STATUS_COLORS = {
  confirmed: 'green',
  active:    'default',
  cancelled: 'red',
}

const STATUS_LABELS = {
  confirmed: 'Подтверждена',
  active:    'Активна',
  cancelled: 'Отменена',
}

const PAGE_SIZE = 50

export default function OperationsLogPage() {
  const [rows, setRows]           = useState([])
  const [total, setTotal]         = useState(0)
  const [loading, setLoading]     = useState(false)
  const [products, setProducts]   = useState([])
  const [skip, setSkip]           = useState(0)

  // filters
  const [dates, setDates]           = useState(null)
  const [opType, setOpType]         = useState(null)
  const [productId, setProductId]   = useState(null)

  useEffect(() => {
    getProducts().then(r => setProducts(r.data)).catch(() => {})
  }, [])

  const load = useCallback(async (currentSkip = skip) => {
    setLoading(true)
    try {
      const params = { skip: currentSkip, limit: PAGE_SIZE }
      if (dates?.[0]) params.date_from = dates[0].format('YYYY-MM-DD')
      if (dates?.[1]) params.date_to   = dates[1].format('YYYY-MM-DD')
      if (opType)     params.operation_type = opType
      if (productId)  params.product_id = productId
      const r = await getOperationsLog(params)
      setRows(r.data.items)
      setTotal(r.data.total)
    } catch {
      message.error('Ошибка загрузки журнала')
    } finally {
      setLoading(false)
    }
  }, [dates, opType, productId, skip])

  useEffect(() => { load(0) }, []) // initial load

  const handleSearch = () => {
    setSkip(0)
    load(0)
  }

  const handlePageChange = (page) => {
    const newSkip = (page - 1) * PAGE_SIZE
    setSkip(newSkip)
    load(newSkip)
  }

  const productOptions = products.map(p => ({
    value: p.id,
    label: `${p.name}${p.nomenclature_code ? ` (${p.nomenclature_code})` : ''}`,
  }))

  const opTypeOptions = Object.entries(OPERATION_LABELS).map(([v, l]) => ({ value: v, label: l }))

  const columns = [
    {
      title: 'Дата',
      dataIndex: 'date',
      width: 130,
      render: v => dayjs(v).format('DD.MM.YYYY HH:mm'),
    },
    {
      title: 'Операция',
      dataIndex: 'operation_type',
      width: 150,
      render: v => (
        <Tag color={OPERATION_COLORS[v] ?? 'default'}>
          {OPERATION_LABELS[v] ?? v}
        </Tag>
      ),
    },
    {
      title: 'Товар',
      dataIndex: 'product_name',
    },
    {
      title: 'Ед.',
      dataIndex: 'unit',
      width: 60,
    },
    {
      title: 'Количество',
      dataIndex: 'quantity',
      width: 110,
      render: (v, row) =>
        row.direction === 'income'
          ? <Text type="success">+{v}</Text>
          : <Text type="danger">−{v}</Text>,
    },
    {
      title: 'Контрагент',
      dataIndex: 'counterparty',
      width: 150,
    },
    {
      title: 'Документ',
      dataIndex: 'document_number',
      width: 140,
      render: v => v ?? '—',
    },
    {
      title: 'Кто создал',
      dataIndex: 'created_by',
      width: 150,
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      width: 120,
      render: v => <Tag color={STATUS_COLORS[v] ?? 'default'}>{STATUS_LABELS[v] ?? v}</Tag>,
    },
  ]

  return (
    <>
      <Title level={4} style={{ marginTop: 0 }}>
        <HistoryOutlined style={{ marginRight: 8 }} />
        Журнал операций
      </Title>

      <Space wrap style={{ marginBottom: 16 }}>
        <RangePicker
          format="DD.MM.YYYY"
          onChange={setDates}
          placeholder={['Дата с', 'Дата по']}
        />
        <Select
          allowClear
          placeholder="Тип операции"
          style={{ width: 180 }}
          options={opTypeOptions}
          onChange={setOpType}
        />
        <Select
          allowClear
          showSearch
          optionFilterProp="label"
          placeholder="Товар"
          style={{ width: 240 }}
          options={productOptions}
          onChange={setProductId}
        />
        <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
          Применить
        </Button>
        <Button icon={<ReloadOutlined />} onClick={handleSearch}>
          Обновить
        </Button>
      </Space>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={rows}
        loading={loading}
        size="small"
        pagination={{
          total,
          pageSize: PAGE_SIZE,
          current: Math.floor(skip / PAGE_SIZE) + 1,
          onChange: handlePageChange,
          showTotal: (t) => `Всего: ${t}`,
          showSizeChanger: false,
        }}
        rowClassName={r => r.status === 'cancelled' ? 'op-log-row-cancelled' : ''}
        locale={{ emptyText: 'Нет операций' }}
      />
    </>
  )
}
