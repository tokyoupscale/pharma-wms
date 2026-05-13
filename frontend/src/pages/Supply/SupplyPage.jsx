import { useEffect, useState, useCallback, useMemo } from 'react'
import {
  Table, Button, Modal, Form, Input, Select, DatePicker,
  Typography, Space, Tag, Popconfirm, message, Drawer,
  Checkbox, Divider,
} from 'antd'
import {
  PlusOutlined, CheckOutlined, DeleteOutlined, InboxOutlined,
  EyeOutlined, FilePdfOutlined, EditOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { getSupplies, createSupply, confirmSupply, deleteSupply, downloadSupplyPdf, updateSupply } from '../../api/supply'
import { getSuppliers, getProducts } from '../../api/references'
import { useAuthStore } from '../../store/authStore'
import { ROLES, SUPPLY_STATUS_LABELS, SUPPLY_STATUS_COLORS } from '../../constants'

const { Title, Text } = Typography
const canEdit = (role) => [ROLES.admin, ROLES.omts].includes(role)

/* ── вне компонента, иначе React размонтирует Form при каждом ре-рендере ── */
function ItemsForm({ itemList, updater, adder, remover, productOptions }) {
  return (
    <>
      {itemList.map((it, idx) => (
        <Space key={idx} style={{ width: '100%', marginBottom: 8 }} size={4} align="start" wrap>
          <Select
            showSearch optionFilterProp="label"
            placeholder="Товар" style={{ width: 220 }}
            options={productOptions}
            value={it.product_id}
            onChange={v => updater(idx, 'product_id', v)}
          />
          <Input placeholder="Кол-во" style={{ width: 80 }} type="number"
            value={it.quantity} onChange={e => updater(idx, 'quantity', e.target.value)} />
          <Input placeholder="Серия" style={{ width: 100 }}
            value={it.batch_code} onChange={e => updater(idx, 'batch_code', e.target.value)} />
          <Input placeholder="Ид. номер" style={{ width: 110 }}
            value={it.identification_number || ''}
            onChange={e => updater(idx, 'identification_number', e.target.value)} />
          <DatePicker placeholder="Годен до" format="DD.MM.YYYY" style={{ width: 130 }}
            value={it.expiry_date} onChange={v => updater(idx, 'expiry_date', v)} />
          <Input placeholder="Уп." style={{ width: 60 }} type="number"
            value={it.package_count || ''}
            onChange={e => updater(idx, 'package_count', e.target.value)} />
          {itemList.length > 1 && (
            <Button size="small" danger onClick={() => remover(idx)}>✕</Button>
          )}
        </Space>
      ))}
      <Button size="small" onClick={adder} icon={<PlusOutlined />}>Добавить позицию</Button>
    </>
  )
}

function SupplyFormFields({ form, onFinish, suppliers }) {
  return (
    <Form form={form} layout="vertical" onFinish={onFinish}>
      <Space style={{ width: '100%' }} size={8} align="start">
        <Form.Item name="invoice_number" label="№ накладной" rules={[{ required: true }]} style={{ width: 220 }}>
          <Input />
        </Form.Item>
        <Form.Item name="invoice_date" label="Дата" style={{ width: 160 }}>
          <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="edo_flag" valuePropName="checked" label=" " style={{ paddingTop: 4 }}>
          <Checkbox>ЭДО</Checkbox>
        </Form.Item>
      </Space>
      <Space style={{ width: '100%' }} size={8} align="start">
        <Form.Item name="supplier_id" label="Поставщик" rules={[{ required: true }]} style={{ width: 300 }}>
          <Select showSearch optionFilterProp="label"
            options={suppliers.map(s => ({ value: s.id, label: s.name }))} />
        </Form.Item>
        <Form.Item name="manufacturer_id" label="Производитель" style={{ width: 300 }}>
          <Select showSearch allowClear optionFilterProp="label"
            options={suppliers.map(s => ({ value: s.id, label: s.name }))} />
        </Form.Item>
      </Space>
      <Form.Item name="notes" label="Примечание">
        <Input.TextArea rows={1} />
      </Form.Item>
    </Form>
  )
}
/* ──────────────────────────────────────────────────────────────────────── */

export default function SupplyPage() {
  const role = useAuthStore(s => s.user?.role)
  const [rows, setRows]           = useState([])
  const [loading, setLoading]     = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [editOpen, setEditOpen]   = useState(false)
  const [editTarget, setEditTarget] = useState(null)
  const [detailRow, setDetailRow] = useState(null)
  const [suppliers, setSuppliers] = useState([])
  const [products, setProducts]   = useState([])
  const [pdfLoading, setPdfLoading] = useState({})
  const [search, setSearch]       = useState('')
  const [filterStatus, setFilterStatus] = useState(null)
  const [items, setItems]         = useState([{ product_id: null, quantity: '', batch_code: '', identification_number: '', expiry_date: null }])
  const [editItems, setEditItems] = useState([])
  const [form]     = Form.useForm()
  const [editForm] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try { const r = await getSupplies(); setRows(r.data) }
    catch { message.error('Ошибка загрузки') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const loadRefs = async () => {
    const [s, p] = await Promise.all([getSuppliers(), getProducts()])
    setSuppliers(s.data)
    setProducts(p.data)
  }

  const openCreate = async () => {
    await loadRefs()
    setItems([{ product_id: null, quantity: '', batch_code: '', identification_number: '', expiry_date: null }])
    form.resetFields()
    setCreateOpen(true)
  }

  const openEdit = async (row) => {
    await loadRefs()
    editForm.setFieldsValue({
      invoice_number:  row.invoice_number,
      invoice_date:    row.invoice_date ? dayjs(row.invoice_date) : null,
      supplier_id:     row.supplier_id,
      manufacturer_id: row.manufacturer_id,
      edo_flag:        row.edo_flag,
      notes:           row.notes,
    })
    setEditItems(row.items.map(it => ({
      product_id:           it.product_id,
      quantity:             String(it.quantity),
      batch_code:           it.batch_code,
      identification_number: it.identification_number || '',
      expiry_date:          it.expiry_date ? dayjs(it.expiry_date) : null,
      manufacture_date:     it.manufacture_date ? dayjs(it.manufacture_date) : null,
      package_count:        it.package_count ? String(it.package_count) : '',
      notes:                it.notes || '',
    })))
    setEditTarget(row)
    setEditOpen(true)
  }

  const buildPayload = (vals, itemList) => ({
    ...vals,
    invoice_date: vals.invoice_date
      ? (vals.invoice_date.format ? vals.invoice_date.format('YYYY-MM-DD') : vals.invoice_date)
      : null,
    items: itemList.map(it => ({
      ...it,
      expiry_date:      it.expiry_date ? (it.expiry_date.format ? it.expiry_date.format('YYYY-MM-DD') : it.expiry_date) : null,
      manufacture_date: it.manufacture_date ? (it.manufacture_date.format ? it.manufacture_date.format('YYYY-MM-DD') : it.manufacture_date) : null,
      quantity:         Number(it.quantity),
      package_count:    it.package_count ? Number(it.package_count) : null,
    })),
  })

  const handleCreate = async (vals) => {
    const validItems = items.filter(it => it.product_id && it.quantity)
    if (!validItems.length) { message.warning('Добавьте хотя бы одну позицию'); return }
    try {
      await createSupply(buildPayload(vals, validItems))
      message.success('Поставка создана')
      form.resetFields(); setCreateOpen(false); load()
    } catch (e) { message.error(e.response?.data?.detail || 'Ошибка') }
  }

  const handleEdit = async (vals) => {
    const validItems = editItems.filter(it => it.product_id && it.quantity)
    if (!validItems.length) { message.warning('Добавьте хотя бы одну позицию'); return }
    try {
      await updateSupply(editTarget.id, buildPayload(vals, validItems))
      message.success('Поставка обновлена')
      editForm.resetFields(); setEditOpen(false); setEditTarget(null); load()
    } catch (e) { message.error(e.response?.data?.detail || 'Ошибка') }
  }

  const handleConfirm = async (id) => {
    try {
      await confirmSupply(id)
      message.success('Подтверждено')
      load()
      setDetailRow(prev => prev?.id === id ? { ...prev, status: 'confirmed' } : prev)
    } catch (e) { message.error(e.response?.data?.detail || 'Ошибка') }
  }

  const handleDelete = async (id) => {
    try { await deleteSupply(id); message.success('Удалено'); load() }
    catch (e) { message.error(e.response?.data?.detail || 'Ошибка') }
  }

  const handleDownloadPdf = async (id, invoiceNumber) => {
    setPdfLoading(prev => ({ ...prev, [id]: true }))
    try {
      const r = await downloadSupplyPdf(id)
      const url = URL.createObjectURL(new Blob([r.data], { type: 'application/pdf' }))
      const a = document.createElement('a'); a.href = url; a.download = `supply_${invoiceNumber}.pdf`; a.click()
      URL.revokeObjectURL(url)
    } catch { message.error('Ошибка скачивания PDF') }
    finally { setPdfLoading(prev => ({ ...prev, [id]: false })) }
  }

  const makeUpdater = (setter) => (idx, field, val) =>
    setter(prev => prev.map((it, i) => i === idx ? { ...it, [field]: val } : it))

  const productOptions = products.map(p => ({
    value: p.id,
    label: `${p.name}${p.nomenclature_code ? ` (${p.nomenclature_code})` : ''}`,
  }))

  const filtered = useMemo(() => rows.filter(r => {
    if (filterStatus && r.status !== filterStatus) return false
    if (search) {
      const q = search.toLowerCase()
      return r.invoice_number?.toLowerCase().includes(q) ||
             r.supplier_name?.toLowerCase().includes(q)
    }
    return true
  }), [rows, search, filterStatus])

  const cols = [
    { title: '№ накладной', dataIndex: 'invoice_number', width: 150 },
    { title: 'Дата', dataIndex: 'invoice_date', width: 110, render: v => v ? dayjs(v).format('DD.MM.YYYY') : '—' },
    { title: 'Поставщик', dataIndex: 'supplier_name' },
    { title: 'Позиций', width: 80, render: (_, r) => r.items?.length ?? 0 },
    {
      title: 'Статус', dataIndex: 'status', width: 130,
      render: v => <Tag color={SUPPLY_STATUS_COLORS[v]}>{SUPPLY_STATUS_LABELS[v] ?? v}</Tag>,
    },
    {
      title: 'Действия', width: 230,
      render: (_, r) => (
        <Space size={4}>
          <Button size="small" icon={<EyeOutlined />} onClick={() => setDetailRow(r)}>Детали</Button>
          <Button size="small" icon={<FilePdfOutlined />}
            loading={!!pdfLoading[r.id]}
            onClick={() => handleDownloadPdf(r.id, r.invoice_number)}>PDF</Button>
          {canEdit(role) && r.status === 'draft' && (
            <>
              <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>Ред.</Button>
              <Popconfirm title="Подтвердить поставку? Это необратимо." onConfirm={() => handleConfirm(r.id)}>
                <Button size="small" type="primary" icon={<CheckOutlined />}>Принять</Button>
              </Popconfirm>
              <Popconfirm title="Удалить черновик?" onConfirm={() => handleDelete(r.id)}>
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ]

  return (
    <>
      <Title level={4} style={{ marginTop: 0 }}>
        <InboxOutlined style={{ marginRight: 8 }} />
        Приход товара
      </Title>

      <Space wrap style={{ marginBottom: 12 }}>
        {canEdit(role) && (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Новая поставка
          </Button>
        )}
        <Input.Search
          placeholder="Поиск по накладной или поставщику"
          allowClear style={{ width: 280 }}
          value={search} onChange={e => setSearch(e.target.value)}
        />
        <Select allowClear placeholder="Статус" style={{ width: 150 }}
          value={filterStatus} onChange={setFilterStatus}
          options={[
            { value: 'draft',     label: 'Черновик' },
            { value: 'confirmed', label: 'Подтверждена' },
          ]}
        />
      </Space>

      <Table rowKey="id" columns={cols} dataSource={filtered} loading={loading}
        size="small" pagination={{ pageSize: 20, showTotal: t => `Всего: ${t}` }} />

      {/* Create modal */}
      <Modal title="Новая поставка" open={createOpen}
        onCancel={() => { setCreateOpen(false); form.resetFields() }}
        onOk={form.submit} width={700}>
        <SupplyFormFields form={form} onFinish={handleCreate} suppliers={suppliers} />
        <Divider>Позиции</Divider>
        <ItemsForm
          itemList={items}
          updater={makeUpdater(setItems)}
          adder={() => setItems(prev => [...prev, { product_id: null, quantity: '', batch_code: '', identification_number: '', expiry_date: null }])}
          remover={(idx) => setItems(prev => prev.filter((_, i) => i !== idx))}
          productOptions={productOptions}
        />
      </Modal>

      {/* Edit modal */}
      <Modal title={`Редактировать черновик № ${editTarget?.invoice_number ?? ''}`}
        open={editOpen}
        onCancel={() => { setEditOpen(false); editForm.resetFields() }}
        onOk={editForm.submit} width={700}>
        <SupplyFormFields form={editForm} onFinish={handleEdit} suppliers={suppliers} />
        <Divider>Позиции</Divider>
        <ItemsForm
          itemList={editItems}
          updater={makeUpdater(setEditItems)}
          adder={() => setEditItems(prev => [...prev, { product_id: null, quantity: '', batch_code: '', identification_number: '', expiry_date: null }])}
          remover={(idx) => setEditItems(prev => prev.filter((_, i) => i !== idx))}
          productOptions={productOptions}
        />
      </Modal>

      {/* Detail drawer */}
      <Drawer title={`Поставка ${detailRow?.invoice_number ?? ''}`}
        open={!!detailRow} onClose={() => setDetailRow(null)} width={520}>
        {detailRow && (
          <>
            <Space direction="vertical" size={2} style={{ width: '100%', marginBottom: 16 }}>
              <Text><b>Статус:</b> <Tag color={SUPPLY_STATUS_COLORS[detailRow.status]}>{SUPPLY_STATUS_LABELS[detailRow.status]}</Tag></Text>
              <Text><b>Поставщик:</b> {detailRow.supplier_name || '—'}</Text>
              <Text><b>Дата накладной:</b> {detailRow.invoice_date ? dayjs(detailRow.invoice_date).format('DD.MM.YYYY') : '—'}</Text>
              <Text><b>ЭДО:</b> {detailRow.edo_flag ? 'Да' : 'Нет'}</Text>
              {detailRow.notes && <Text><b>Примечание:</b> {detailRow.notes}</Text>}
            </Space>
            <Table rowKey="id" size="small" pagination={false} dataSource={detailRow.items}
              columns={[
                { title: 'Товар',         dataIndex: 'product_name' },
                { title: 'Кол-во',        dataIndex: 'quantity',            width: 80 },
                { title: 'Кол-во мест',   dataIndex: 'package_count',       width: 100, render: v => v ?? '—' },
                { title: 'Серия',         dataIndex: 'batch_code',          width: 100 },
                { title: 'Ид. номер',     dataIndex: 'identification_number', width: 110, render: v => v || '—' },
                { title: 'Годен до',      dataIndex: 'expiry_date',         width: 100, render: v => v ? dayjs(v).format('DD.MM.YYYY') : '—' },
              ]}
            />
          </>
        )}
      </Drawer>
    </>
  )
}
