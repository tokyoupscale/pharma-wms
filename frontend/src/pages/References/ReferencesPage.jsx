import { useEffect, useState, useCallback } from 'react'
import {
  Tabs, Table, Button, Modal, Form, Input, Select,
  Typography, Space, Tag, Popconfirm, message,
} from 'antd'
import { PlusOutlined, DeleteOutlined, AppstoreOutlined } from '@ant-design/icons'
import {
  getCategories, createCategory, deleteCategory,
  getSubgroups, createSubgroup,
  getSuppliers, createSupplier, deleteSupplier,
  getProducts, createProduct, deleteProduct,
} from '../../api/references'
import { useAuthStore } from '../../store/authStore'
import { ROLES } from '../../constants'

const { Title } = Typography
const canEdit = (role) => [ROLES.admin, ROLES.omts].includes(role)

/* ─── Categories ─── */
function CategoriesTab({ role, onChanged }) {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try { const r = await getCategories(); setRows(r.data) }
    catch { message.error('Ошибка загрузки категорий') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const handleAdd = async (vals) => {
    try {
      await createCategory(vals)
      message.success('Категория добавлена')
      form.resetFields(); setOpen(false); load(); onChanged?.()
    } catch (e) { message.error(e.response?.data?.detail || 'Ошибка') }
  }

  const handleDel = async (id) => {
    try { await deleteCategory(id); message.success('Удалено'); load(); onChanged?.() }
    catch (e) { message.error(e.response?.data?.detail || 'Ошибка') }
  }

  const cols = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: 'Название', dataIndex: 'name' },
    canEdit(role) && {
      title: '', width: 60,
      render: (_, r) => (
        <Popconfirm title="Деактивировать?" onConfirm={() => handleDel(r.id)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ].filter(Boolean)

  return (
    <>
      {canEdit(role) && (
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)} style={{ marginBottom: 12 }}>
          Добавить
        </Button>
      )}
      <Table rowKey="id" columns={cols} dataSource={rows} loading={loading} size="small" pagination={false} />
      <Modal title="Новая категория" open={open} onCancel={() => setOpen(false)} onOk={form.submit} destroyOnClose>
        <Form form={form} layout="vertical" onFinish={handleAdd}>
          <Form.Item name="name" label="Название" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

/* ─── Subgroups ─── */
function SubgroupsTab({ role, categories, onChanged }) {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try { const r = await getSubgroups(); setRows(r.data) }
    catch { message.error('Ошибка загрузки подгрупп') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const handleAdd = async (vals) => {
    try {
      await createSubgroup(vals)
      message.success('Подгруппа добавлена')
      form.resetFields(); setOpen(false); load(); onChanged?.()
    } catch (e) { message.error(e.response?.data?.detail || 'Ошибка') }
  }

  const cols = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: 'Название', dataIndex: 'name' },
    {
      title: 'Категория', dataIndex: 'category_id',
      render: (id) => categories.find(c => c.id === id)?.name || id,
    },
  ]

  return (
    <>
      {canEdit(role) && (
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)} style={{ marginBottom: 12 }}>
          Добавить
        </Button>
      )}
      <Table rowKey="id" columns={cols} dataSource={rows} loading={loading} size="small" pagination={false} />
      <Modal title="Новая подгруппа" open={open} onCancel={() => setOpen(false)} onOk={form.submit} destroyOnClose>
        <Form form={form} layout="vertical" onFinish={handleAdd}>
          <Form.Item name="category_id" label="Категория" rules={[{ required: true }]}>
            <Select options={categories.map(c => ({ value: c.id, label: c.name }))} />
          </Form.Item>
          <Form.Item name="name" label="Название" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

/* ─── Suppliers ─── */
function SuppliersTab({ role }) {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try { const r = await getSuppliers(); setRows(r.data) }
    catch { message.error('Ошибка загрузки поставщиков') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const handleAdd = async (vals) => {
    try {
      await createSupplier(vals)
      message.success('Поставщик добавлен')
      form.resetFields(); setOpen(false); load()
    } catch (e) { message.error(e.response?.data?.detail || 'Ошибка') }
  }

  const handleDel = async (id) => {
    try { await deleteSupplier(id); message.success('Удалено'); load() }
    catch (e) { message.error(e.response?.data?.detail || 'Ошибка') }
  }

  const cols = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: 'Название', dataIndex: 'name' },
    { title: 'ИНН', dataIndex: 'inn' },
    { title: 'Контакт', dataIndex: 'contact_info' },
    canEdit(role) && {
      title: '', width: 60,
      render: (_, r) => (
        <Popconfirm title="Деактивировать?" onConfirm={() => handleDel(r.id)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ].filter(Boolean)

  return (
    <>
      {canEdit(role) && (
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)} style={{ marginBottom: 12 }}>
          Добавить
        </Button>
      )}
      <Table rowKey="id" columns={cols} dataSource={rows} loading={loading} size="small" pagination={{ pageSize: 20 }} />
      <Modal title="Новый поставщик" open={open} onCancel={() => setOpen(false)} onOk={form.submit} destroyOnClose>
        <Form form={form} layout="vertical" onFinish={handleAdd}>
          <Form.Item name="name" label="Название" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="inn" label="ИНН">
            <Input />
          </Form.Item>
          <Form.Item name="contact_info" label="Контактная информация">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

/* ─── Products ─── */
function ProductsTab({ role, categories, subgroups }) {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [filterCat, setFilterCat] = useState(null)
  const [form] = Form.useForm()
  const catId = Form.useWatch('category_id', form)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = {}
      if (search) params.search = search
      if (filterCat) params.category_id = filterCat
      const r = await getProducts(params)
      setRows(r.data)
    } catch { message.error('Ошибка загрузки товаров') }
    finally { setLoading(false) }
  }, [search, filterCat])

  useEffect(() => { load() }, [load])

  const handleAdd = async (vals) => {
    try {
      await createProduct(vals)
      message.success('Товар добавлен')
      form.resetFields(); setOpen(false); load()
    } catch (e) { message.error(e.response?.data?.detail || 'Ошибка') }
  }

  const handleDel = async (id) => {
    try { await deleteProduct(id); message.success('Удалено'); load() }
    catch (e) { message.error(e.response?.data?.detail || 'Ошибка') }
  }

  const filteredSubgroups = subgroups.filter(s => !catId || s.category_id === catId)

  const cols = [
    { title: 'Код', dataIndex: 'nomenclature_code', width: 100 },
    { title: 'Название', dataIndex: 'name' },
    { title: 'Категория', dataIndex: 'category_id', render: (id) => categories.find(c => c.id === id)?.name || '—' },
    { title: 'Ед.', dataIndex: 'unit', width: 60 },
    { title: 'Остаток', dataIndex: 'current_stock', width: 90 },
    { title: 'Мин', dataIndex: 'min_stock', width: 70 },
    {
      title: 'Статус', dataIndex: 'low_stock', width: 100,
      render: (v) => v ? <Tag color="red">Мало</Tag> : <Tag color="green">Норма</Tag>,
    },
    canEdit(role) && {
      title: '', width: 60,
      render: (_, r) => (
        <Popconfirm title="Деактивировать?" onConfirm={() => handleDel(r.id)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ].filter(Boolean)

  return (
    <>
      <Space style={{ marginBottom: 12 }} wrap>
        <Input.Search
          placeholder="Поиск по названию / коду"
          allowClear
          style={{ width: 280 }}
          onSearch={setSearch}
          onChange={e => !e.target.value && setSearch('')}
        />
        <Select
          allowClear placeholder="Категория"
          style={{ width: 200 }}
          options={categories.map(c => ({ value: c.id, label: c.name }))}
          onChange={setFilterCat}
        />
        {canEdit(role) && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>
            Добавить
          </Button>
        )}
      </Space>
      <Table rowKey="id" columns={cols} dataSource={rows} loading={loading} size="small" pagination={{ pageSize: 20 }} />
      <Modal title="Новый товар" open={open} onCancel={() => { setOpen(false); form.resetFields() }} onOk={form.submit} destroyOnClose width={560}>
        <Form form={form} layout="vertical" onFinish={handleAdd}>
          <Form.Item name="name" label="Название" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="nomenclature_code" label="Код номенклатуры">
            <Input />
          </Form.Item>
          <Space.Compact style={{ width: '100%' }}>
            <Form.Item name="category_id" label="Категория" style={{ width: '50%', marginRight: 8 }} rules={[{ required: true }]}>
              <Select options={categories.map(c => ({ value: c.id, label: c.name }))} onChange={() => form.setFieldValue('subgroup_id', null)} />
            </Form.Item>
            <Form.Item name="subgroup_id" label="Подгруппа" style={{ width: '50%' }}>
              <Select allowClear options={filteredSubgroups.map(s => ({ value: s.id, label: s.name }))} />
            </Form.Item>
          </Space.Compact>
          <Space style={{ width: '100%' }} size={8}>
            <Form.Item name="unit" label="Ед. измерения" rules={[{ required: true }]}>
              <Select style={{ width: 140 }} options={[
                { value: 'kg', label: 'кг' },
                { value: 'g',  label: 'г' },
                { value: 'l',  label: 'л' },
                { value: 'ml', label: 'мл' },
                { value: 'pcs', label: 'шт' },
                { value: 'pack', label: 'уп' },
              ]} />
            </Form.Item>
            <Form.Item name="min_stock" label="Мин. остаток" initialValue={0}>
              <Input type="number" style={{ width: 140 }} />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </>
  )
}

/* ─── Main Page ─── */
export default function ReferencesPage() {
  const role = useAuthStore(s => s.user?.role)
  const [categories, setCategories] = useState([])
  const [subgroups, setSubgroups] = useState([])

  const reloadCategories = useCallback(() => {
    getCategories().then(r => setCategories(r.data)).catch(() => {})
  }, [])

  const reloadSubgroups = useCallback(() => {
    getSubgroups().then(r => setSubgroups(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    reloadCategories()
    reloadSubgroups()
  }, [reloadCategories, reloadSubgroups])

  const items = [
    { key: 'categories', label: 'Категории',  children: <CategoriesTab role={role} onChanged={reloadCategories} /> },
    { key: 'subgroups',  label: 'Подгруппы',  children: <SubgroupsTab role={role} categories={categories} onChanged={reloadSubgroups} /> },
    { key: 'suppliers',  label: 'Поставщики', children: <SuppliersTab role={role} /> },
    { key: 'products',   label: 'Товары',     children: <ProductsTab role={role} categories={categories} subgroups={subgroups} /> },
  ]

  return (
    <>
      <Title level={4} style={{ marginTop: 0 }}>
        <AppstoreOutlined style={{ marginRight: 8 }} />
        Справочники
      </Title>
      <Tabs items={items} />
    </>
  )
}
