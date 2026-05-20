import { useEffect, useState, useCallback, useMemo } from 'react'
import {
  Table, Button, Modal, Form, Input, Select,
  Typography, Space, Tag, message, DatePicker,
} from 'antd'
import { PlusOutlined, StopOutlined, ExportOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { getExpenses, createExpense, cancelExpense } from '../../api/expense'
import { getProducts } from '../../api/references'
import { useAuthStore } from '../../store/authStore'
import { ROLES, DEPARTMENTS, EXPENSE_TYPE_LABELS } from '../../constants'

const { Title, Text } = Typography
const canEdit = (role) => [ROLES.admin, ROLES.omts].includes(role)

export default function ExpensePage() {
  const role = useAuthStore(s => s.user?.role)
  const [rows, setRows]           = useState([])
  const [loading, setLoading]     = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [cancelModal, setCancelModal] = useState(null)
  const [products, setProducts]   = useState([])
  const [cancelReason, setCancelReason] = useState('')
  const [form] = Form.useForm()

  // filters
  const [filterType, setFilterType]       = useState(null)
  const [filterStatus, setFilterStatus]   = useState(null)
  const [search, setSearch]               = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try { const r = await getExpenses(); setRows(r.data) }
    catch { message.error('Ошибка загрузки') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load] )

  const openCreate = async () => {
    const r = await getProducts()
    setProducts(r.data)
    setCreateOpen(true)
  }

  const handleCreate = async (vals) => {
    const payload = {
      ...vals,
      expense_date: vals.expense_date?.toISOString(),
      quantity: Number(vals.quantity),
    }
    try {
      await createExpense(payload)
      message.success('Расход создан')
      form.resetFields(); setCreateOpen(false); load()
    } catch (e) { message.error(e.response?.data?.detail || 'Ошибка') }
  }

  const handleCancel = async () => {
    if (!cancelReason.trim()) { message.warning('Укажите причину'); return }
    try {
      await cancelExpense(cancelModal.id, cancelReason)
      message.success('Запись отменена')
      setCancelModal(null); setCancelReason(''); load()
    } catch (e) { message.error(e.response?.data?.detail || 'Ошибка') }
  }

  const expenseTypes   = Object.entries(EXPENSE_TYPE_LABELS).map(([v, l]) => ({ value: v, label: l }))
  const productOptions = products.map(p => ({
    value: p.id,
    label: `${p.name}${p.nomenclature_code ? ` (${p.nomenclature_code})` : ''}`,
  }))

  const canCreateExpense = ![ROLES.workshop_afs, ROLES.workshop_gls, ROLES.planning].includes(role)

  const allowedExpenseTypes = [ROLES.quality, ROLES.quality_assurance].includes(role)
    ? expenseTypes.filter(t => t.value === 'sampling')
    : expenseTypes

  const filtered = useMemo(() => rows.filter(r => {
    if (filterType   && r.expense_type !== filterType) return false
    if (filterStatus === 'active'    && r.is_cancelled)  return false
    if (filterStatus === 'cancelled' && !r.is_cancelled) return false
    if (search) {
      const q = search.toLowerCase()
      return r.product_name?.toLowerCase().includes(q)
    }
    return true
  }), [rows, filterType, filterStatus, search])

  const cols = [
    { title: '№', width: 60, render: (_, __, index) => index + 1 },
    { title: 'Товар', dataIndex: 'product_name' },
    { title: 'Подразделение', dataIndex: 'department', render: v => DEPARTMENTS.find(d => d.value === v)?.label ?? v },
    { title: 'Тип', dataIndex: 'expense_type', render: v => EXPENSE_TYPE_LABELS[v] ?? v },
    { title: 'Кол-во', dataIndex: 'quantity', width: 80 },
    { title: 'Партия', dataIndex: 'batch_number', width: 100, render: v => v || '—' },
    { title: 'Ид. номер', dataIndex: 'identification_number', width: 110, render: v => v || '—' },
    { title: 'Остаток', dataIndex: 'balance', width: 90, render: v => v ?? '—' },
    { title: 'Дата', dataIndex: 'expense_date', width: 110, render: v => v ? dayjs(v).format('DD.MM.YYYY') : '—' },
    { title: 'Создал', dataIndex: 'created_by_name' },
    {
      title: 'Статус', dataIndex: 'is_cancelled', width: 110,
      render: v => v ? <Tag color="red">Отменён</Tag> : <Tag color="green">Активен</Tag>,
    },
    canEdit(role) && {
      title: '', width: 100,
      render: (_, r) => !r.is_cancelled && (
        <Button size="small" danger icon={<StopOutlined />}
          onClick={() => { setCancelModal(r); setCancelReason('') }}>
          Отменить
        </Button>
      ),
    },
  ].filter(Boolean)

  return (
    <>
      <Title level={4} style={{ marginTop: 0 }}>
        <ExportOutlined style={{ marginRight: 8 }} />
        Расход товара
      </Title>

      <Space wrap style={{ marginBottom: 12 }}>
        {canCreateExpense && (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Оформить расход
          </Button>
        )}
        <Input.Search
          placeholder="Поиск по товару"
          allowClear style={{ width: 220 }}
          value={search} onChange={e => setSearch(e.target.value)}
        />
        <Select allowClear placeholder="Тип операции" style={{ width: 180 }}
          value={filterType} onChange={setFilterType} options={expenseTypes} />
        <Select allowClear placeholder="Статус" style={{ width: 140 }}
          value={filterStatus} onChange={setFilterStatus}
          options={[
            { value: 'active',    label: 'Активен' },
            { value: 'cancelled', label: 'Отменён' },
          ]}
        />
      </Space>

      <Table
        rowKey="id" columns={cols} dataSource={filtered}
        loading={loading} size="small"
        pagination={{ pageSize: 20, showTotal: t => `Всего: ${t}` }}
      />

      <Modal title="Новый расход" open={createOpen}
        onCancel={() => { setCreateOpen(false); form.resetFields() }}
        onOk={form.submit} destroyOnHidden width={520}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="product_id" label="Товар" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label" options={productOptions} />
          </Form.Item>
          <Space style={{ width: '100%' }} size={8} align="start">
            <Form.Item name="department" label="Подразделение" rules={[{ required: true }]} style={{ width: 220 }}>
              <Select options={DEPARTMENTS} />
            </Form.Item>
            <Form.Item name="expense_type" label="Тип операции" rules={[{ required: true }]} style={{ width: 220 }}>
              <Select options={allowedExpenseTypes} />
            </Form.Item>
          </Space>
          <Space style={{ width: '100%' }} size={8} align="start">
            <Form.Item name="quantity" label="Количество" rules={[{ required: true }]} style={{ width: 160 }}>
              <Input type="number" />
            </Form.Item>
            <Form.Item name="expense_date" label="Дата" style={{ width: 200 }}>
              <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} />
            </Form.Item>
          </Space>
          <Form.Item name="purpose" label="Назначение">
            <Input />
          </Form.Item>
          <Form.Item name="document_number" label="№ документа">
            <Input />
          </Form.Item>
          <Space style={{ width: '100%' }} size={8} align="start">
            <Form.Item name="batch_number" label="Партия поставщика" style={{ width: 240 }}>
              <Input />
            </Form.Item>
            <Form.Item name="identification_number" label="Идентификационный номер" style={{ width: 240 }}>
              <Input />
            </Form.Item>
          </Space>
          <Form.Item name="note" label="Примечание">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="Отмена записи" open={!!cancelModal}
        onCancel={() => setCancelModal(null)}
        onOk={handleCancel} okText="Отменить запись" okButtonProps={{ danger: true }}>
        <Text>Товар: <b>{cancelModal?.product_name}</b>, кол-во: <b>{cancelModal?.quantity}</b></Text>
        <Form layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item label="Причина отмены" required>
            <Input.TextArea rows={3} value={cancelReason} onChange={e => setCancelReason(e.target.value)} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
