import { useEffect, useState, useCallback, useMemo } from 'react'
import {
  Table, Button, Modal, Form, Input, Select,
  Typography, Space, Tag, message, Drawer, Popconfirm,
} from 'antd'
import { PlusOutlined, CheckOutlined, CloseOutlined, OrderedListOutlined, FilePdfOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { getRequests, createRequest, approveRequest, rejectRequest, downloadRequestPdf } from '../../api/requests'
import { getProducts } from '../../api/references'
import { useAuthStore } from '../../store/authStore'
import { ROLES, REQUEST_STATUS_LABELS, REQUEST_STATUS_COLORS, DEPARTMENTS } from '../../constants'

const { Title, Text } = Typography
const canEdit   = (role) => [ROLES.admin, ROLES.omts].includes(role)
const canCreate = (role) => [ROLES.admin, ROLES.omts, ROLES.workshop_afs, ROLES.workshop_gls].includes(role)

export default function RequestsPage() {
  const role = useAuthStore(s => s.user?.role)
  const [rows, setRows]           = useState([])
  const [loading, setLoading]     = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [rejectModal, setRejectModal] = useState(null)
  const [detailRow, setDetailRow] = useState(null)
  const [products, setProducts]   = useState([])
  const [rejectReason, setRejectReason] = useState('')
  const [items, setItems]         = useState([{ product_id: null, quantity: '' }])
  const [pdfLoading, setPdfLoading] = useState({})
  const [form] = Form.useForm()

  // filters
  const [filterStatus, setFilterStatus] = useState(null)
  const [filterDept, setFilterDept]     = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try { const r = await getRequests(); setRows(r.data) }
    catch { message.error('Ошибка загрузки') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const openCreate = async () => {
    const r = await getProducts()
    setProducts(r.data)
    setItems([{ product_id: null, quantity: '' }])
    setCreateOpen(true)
  }

  const handleCreate = async (vals) => {
    const payload = {
      notes: vals.notes,
      items: items
        .filter(it => it.product_id && it.quantity)
        .map(it => ({ product_id: it.product_id, quantity: Number(it.quantity), notes: it.notes || '' })),
    }
    if (!payload.items.length) { message.warning('Добавьте хотя бы одну позицию'); return }
    try {
      await createRequest(payload)
      message.success('Заявка создана')
      form.resetFields(); setCreateOpen(false); load()
    } catch (e) { message.error(e.response?.data?.detail || 'Ошибка') }
  }

  const handleApprove = async (id) => {
    try { await approveRequest(id); message.success('Заявка утверждена'); load() }
    catch (e) { message.error(e.response?.data?.detail || 'Ошибка') }
  }

  const handleReject = async () => {
    if (!rejectReason.trim()) { message.warning('Укажите причину'); return }
    try {
      await rejectRequest(rejectModal.id, rejectReason)
      message.success('Заявка отклонена')
      setRejectModal(null); setRejectReason(''); load()
    } catch (e) { message.error(e.response?.data?.detail || 'Ошибка') }
  }

  const handleDownloadPdf = async (id) => {
    setPdfLoading(prev => ({ ...prev, [id]: true }))
    try {
      const r = await downloadRequestPdf(id)
      const url = URL.createObjectURL(new Blob([r.data], { type: 'application/pdf' }))
      const a = document.createElement('a'); a.href = url; a.download = `request_${id}.pdf`; a.click()
      URL.revokeObjectURL(url)
    } catch { message.error('Ошибка скачивания PDF') }
    finally { setPdfLoading(prev => ({ ...prev, [id]: false })) }
  }

  const updateItem = (idx, field, val) =>
    setItems(prev => prev.map((it, i) => i === idx ? { ...it, [field]: val } : it))
  const addItem    = () => setItems(prev => [...prev, { product_id: null, quantity: '' }])
  const removeItem = (idx) => setItems(prev => prev.filter((_, i) => i !== idx))

  const productOptions = products.map(p => ({
    value: p.id,
    label: `${p.name}${p.nomenclature_code ? ` (${p.nomenclature_code})` : ''}`,
  }))

  const filtered = useMemo(() => rows.filter(r => {
    if (filterStatus && r.status !== filterStatus) return false
    if (filterDept   && r.department !== filterDept) return false
    return true
  }), [rows, filterStatus, filterDept])

  const cols = [
    { title: '№', width: 60, render: (_, __, index) => index + 1 },
    { title: 'Подразделение', dataIndex: 'department', render: v => DEPARTMENTS.find(d => d.value === v)?.label ?? v },
    { title: 'Создал', dataIndex: 'created_by_name' },
    { title: 'Позиций', width: 80, render: (_, r) => r.items?.length ?? 0 },
    { title: 'Дата', dataIndex: 'created_at', width: 110, render: v => v ? dayjs(v).format('DD.MM.YYYY') : '—' },
    {
      title: 'Статус', dataIndex: 'status', width: 150,
      render: v => <Tag color={REQUEST_STATUS_COLORS[v]}>{REQUEST_STATUS_LABELS[v] ?? v}</Tag>,
    },
    {
      title: 'Действия', width: 240,
      render: (_, r) => (
        <Space size={4}>
          <Button size="small" onClick={() => setDetailRow(r)}>Детали</Button>
          <Button size="small" icon={<FilePdfOutlined />}
            loading={!!pdfLoading[r.id]}
            onClick={() => handleDownloadPdf(r.id)}>PDF</Button>
          {canEdit(role) && r.status === 'pending' && (
            <>
              <Popconfirm
                title="Утвердить заявку?"
                description="Остатки будут списаны. Действие необратимо."
                onConfirm={() => handleApprove(r.id)}
                okText="Утвердить"
              >
                <Button size="small" type="primary" icon={<CheckOutlined />}>Утвердить</Button>
              </Popconfirm>
              <Button size="small" danger icon={<CloseOutlined />}
                onClick={() => { setRejectModal(r); setRejectReason('') }}>
                Отклонить
              </Button>
            </>
          )}
        </Space>
      ),
    },
  ]

  return (
    <>
      <Title level={4} style={{ marginTop: 0 }}>
        <OrderedListOutlined style={{ marginRight: 8 }} />
        Заявки подразделений
      </Title>

      <Space wrap style={{ marginBottom: 12 }}>
        {canCreate(role) && (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Создать заявку
          </Button>
        )}
        <Select
          allowClear placeholder="Статус"
          style={{ width: 170 }}
          value={filterStatus} onChange={setFilterStatus}
          options={[
            { value: 'pending',  label: 'На рассмотрении' },
            { value: 'approved', label: 'Утверждена' },
            { value: 'rejected', label: 'Отклонена' },
          ]}
        />
        <Select
          allowClear placeholder="Подразделение"
          style={{ width: 170 }}
          value={filterDept} onChange={setFilterDept}
          options={DEPARTMENTS}
        />
      </Space>

      <Table
        rowKey="id" columns={cols} dataSource={filtered}
        loading={loading} size="small"
        pagination={{ pageSize: 20, showTotal: t => `Всего: ${t}` }}
      />

      {/* Create modal */}
      <Modal title="Новая заявка" open={createOpen}
        onCancel={() => { setCreateOpen(false); form.resetFields() }}
        onOk={form.submit} destroyOnHidden width={600}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="notes" label="Примечание">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Text strong>Позиции</Text>
          <div style={{ marginTop: 8 }}>
            {items.map((it, idx) => (
              <Space key={idx} style={{ width: '100%', marginBottom: 6 }} size={4} align="start">
                <Select showSearch optionFilterProp="label" placeholder="Товар" style={{ width: 280 }}
                  options={productOptions} value={it.product_id}
                  onChange={v => updateItem(idx, 'product_id', v)} />
                <Input placeholder="Кол-во" style={{ width: 100 }} type="number"
                  value={it.quantity} onChange={e => updateItem(idx, 'quantity', e.target.value)} />
                <Input placeholder="Примечание" style={{ width: 140 }}
                  value={it.notes} onChange={e => updateItem(idx, 'notes', e.target.value)} />
                {items.length > 1 && (
                  <Button size="small" danger onClick={() => removeItem(idx)}>✕</Button>
                )}
              </Space>
            ))}
            <Button size="small" onClick={addItem} icon={<PlusOutlined />} style={{ marginTop: 4 }}>
              Добавить позицию
            </Button>
          </div>
        </Form>
      </Modal>

      {/* Reject modal */}
      <Modal title="Отклонить заявку" open={!!rejectModal}
        onCancel={() => setRejectModal(null)}
        onOk={handleReject} okText="Отклонить" okButtonProps={{ danger: true }}>
        <Text>Заявка №{rejectModal?.id} от {rejectModal?.created_by_name}</Text>
        <Form layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item label="Причина отклонения" required>
            <Input.TextArea rows={3} value={rejectReason} onChange={e => setRejectReason(e.target.value)} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Detail drawer */}
      <Drawer title={`Заявка №${detailRow?.id}`} open={!!detailRow}
        onClose={() => setDetailRow(null)} width={500}>
        {detailRow && (
          <>
            <Space direction="vertical" size={2} style={{ marginBottom: 16 }}>
              <Text><b>Подразделение:</b> {DEPARTMENTS.find(d => d.value === detailRow.department)?.label ?? detailRow.department}</Text>
              <Text><b>Создал:</b> {detailRow.created_by_name}</Text>
              <Text><b>Статус:</b> <Tag color={REQUEST_STATUS_COLORS[detailRow.status]}>{REQUEST_STATUS_LABELS[detailRow.status]}</Tag></Text>
              {detailRow.approved_by_name && <Text><b>Обработал:</b> {detailRow.approved_by_name}</Text>}
              {detailRow.reject_reason && <Text type="danger"><b>Причина отказа:</b> {detailRow.reject_reason}</Text>}
              {detailRow.notes && <Text><b>Примечание:</b> {detailRow.notes}</Text>}
            </Space>
            <Table rowKey="id" size="small" pagination={false} dataSource={detailRow.items}
              columns={[
                { title: 'Товар', dataIndex: 'product_name' },
                { title: 'Кол-во', dataIndex: 'quantity', width: 80 },
                { title: 'Примечание', dataIndex: 'notes' },
              ]}
            />
          </>
        )}
      </Drawer>
    </>
  )
}
