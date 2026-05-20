import { useEffect, useState, useCallback } from 'react'
import {
  Table, Button, Modal, Form, Input, Select,
  Typography, Space, Tag, message, Drawer, Popconfirm,
} from 'antd'
import { FileTextOutlined, LockOutlined, FilePdfOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { getLimitCards, closeLimitCard, setAllocation, downloadLimitCardPdf } from '../../api/limitCard'
import { getProducts } from '../../api/references'
import { useAuthStore } from '../../store/authStore'
import { ROLES, DEPARTMENTS } from '../../constants'

const { Title, Text } = Typography
const canEdit = (role) => [ROLES.admin, ROLES.omts].includes(role)

const MONTH_NAMES = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']

export default function LimitCardPage() {
  const role = useAuthStore(s => s.user?.role)
  const [rows, setRows]           = useState([])
  const [loading, setLoading]     = useState(false)
  const [detailCard, setDetailCard] = useState(null)
  const [allocOpen, setAllocOpen] = useState(false)
  const [products, setProducts]   = useState([])
  const [pdfLoading, setPdfLoading] = useState({})
  const [allocForm] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try { const r = await getLimitCards(); setRows(r.data) }
    catch { message.error('Ошибка загрузки') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const handleClose = async (id) => {
    try {
      await closeLimitCard(id)
      message.success('ЛЗК закрыта')
      load()
      setDetailCard(prev => prev?.id === id ? { ...prev, status: 'closed' } : prev)
    } catch (e) { message.error(e.response?.data?.detail || 'Ошибка') }
  }

  const handleDownloadPdf = async (id) => {
    setPdfLoading(prev => ({ ...prev, [id]: true }))
    try {
      const r = await downloadLimitCardPdf(id)
      const url = URL.createObjectURL(new Blob([r.data], { type: 'application/pdf' }))
      const a = document.createElement('a'); a.href = url; a.download = `limit_card_${id}.pdf`; a.click()
      URL.revokeObjectURL(url)
    } catch { message.error('Ошибка скачивания PDF') }
    finally { setPdfLoading(prev => ({ ...prev, [id]: false })) }
  }

  const openAlloc = async () => {
    const r = await getProducts()
    setProducts(r.data)
    setAllocOpen(true)
  }

  const handleAlloc = async (vals) => {
    try {
      await setAllocation(detailCard.id, { ...vals, limit_quantity: Number(vals.limit_quantity) })
      message.success('Лимит установлен')
      allocForm.resetFields(); setAllocOpen(false)
      const r = await getLimitCards()
      const updated = r.data.find(c => c.id === detailCard.id)
      if (updated) setDetailCard(updated)
      setRows(r.data)
    } catch (e) { message.error(e.response?.data?.detail || 'Ошибка') }
  }

  const productOptions = products.map(p => ({
    value: p.id,
    label: `${p.name}${p.nomenclature_code ? ` (${p.nomenclature_code})` : ''}`,
  }))

  const cols = [
    { title: 'Подразделение', dataIndex: 'department', render: v => DEPARTMENTS.find(d => d.value === v)?.label ?? v },
    { title: 'Период', render: (_, r) => `${MONTH_NAMES[r.month - 1]} ${r.year}` },
    { title: 'Позиций', render: (_, r) => r.items?.length ?? 0 },
    { title: 'Лимитов', render: (_, r) => r.allocations?.length ?? 0 },
    {
      title: 'Статус', dataIndex: 'status', width: 120,
      render: v => v === 'open' ? <Tag color="blue">Открыта</Tag> : <Tag color="default">Закрыта</Tag>,
    },
    {
      title: '', width: 80,
      render: (_, r) => <Button size="small" onClick={() => setDetailCard(r)}>Открыть</Button>,
    },
  ]

  const drawerTitle = detailCard
    ? `ЛЗК — ${DEPARTMENTS.find(d => d.value === detailCard.department)?.label ?? detailCard.department}, ${MONTH_NAMES[(detailCard.month ?? 1) - 1]} ${detailCard.year}`
    : ''

  return (
    <>
      <Title level={4} style={{ marginTop: 0 }}>
        <FileTextOutlined style={{ marginRight: 8 }} />
        Лимитно-заборные карты
      </Title>

      <Table rowKey="id" columns={cols} dataSource={rows} loading={loading} size="small" pagination={{ pageSize: 20, showTotal: t => `Всего: ${t}` }} />

      <Drawer
        title={drawerTitle}
        open={!!detailCard}
        onClose={() => setDetailCard(null)}
        width={640}
        extra={
          <Space>
            <Button
              icon={<FilePdfOutlined />}
              loading={!!pdfLoading[detailCard?.id]}
              onClick={() => handleDownloadPdf(detailCard?.id)}
            >PDF</Button>
            {canEdit(role) && detailCard?.status === 'open' && (
              <>
                <Button onClick={openAlloc}>Установить лимит</Button>
                <Popconfirm
                  title="Закрыть ЛЗК?"
                  description="Закрытую карту нельзя изменить."
                  onConfirm={() => handleClose(detailCard.id)}
                  okText="Закрыть"
                  okButtonProps={{ danger: true }}
                >
                  <Button danger icon={<LockOutlined />}>Закрыть ЛЗК</Button>
                </Popconfirm>
              </>
            )}
          </Space>
        }
      >
        {detailCard && (
          <>
            <Text strong>Установленные лимиты</Text>
            <Table
              rowKey="id" size="small" pagination={false}
              style={{ marginTop: 8, marginBottom: 20 }}
              dataSource={detailCard.allocations}
              columns={[
                { title: 'Товар', dataIndex: 'product_name' },
                { title: 'Лимит', dataIndex: 'limit_quantity', width: 100 },
              ]}
              locale={{ emptyText: 'Лимиты не установлены' }}
            />

            <Text strong>Фактический расход</Text>
            <Table
              rowKey="id" size="small" pagination={false}
              style={{ marginTop: 8 }}
              dataSource={detailCard.items}
              columns={[
                { title: 'Дата', dataIndex: 'operation_date', width: 100, render: v => v ? dayjs(v).format('DD.MM.YYYY') : '—' },
                { title: 'Товар', dataIndex: 'product_name' },
                { title: 'Кол-во', dataIndex: 'quantity', width: 80 },
                { title: 'Примечание', dataIndex: 'notes' },
              ]}
              locale={{ emptyText: 'Расходов нет' }}
            />
          </>
        )}
      </Drawer>

      <Modal title="Установить лимит" open={allocOpen}
        onCancel={() => { setAllocOpen(false); allocForm.resetFields() }}
        onOk={allocForm.submit} destroyOnHidden>
        <Form form={allocForm} layout="vertical" onFinish={handleAlloc}>
          <Form.Item name="product_id" label="Товар" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label" options={productOptions} />
          </Form.Item>
          <Form.Item name="limit_quantity" label="Лимит (кол-во)" rules={[{ required: true }]}>
            <Input type="number" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
