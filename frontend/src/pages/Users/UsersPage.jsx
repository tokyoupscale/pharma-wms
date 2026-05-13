import { useEffect, useState, useCallback } from 'react'
import {
  Table, Button, Modal, Form, Input, Select, Tag, Space,
  Popconfirm, message, Typography, Switch,
} from 'antd'
import { PlusOutlined, EditOutlined, KeyOutlined } from '@ant-design/icons'
import { getUsers, createUser, updateUser, resetPassword } from '../../api/auth'
import { useAuthStore } from '../../store/authStore'
import { ROLE_LABELS, ROLES } from '../../constants'

const { Title } = Typography

const ROLE_OPTIONS = Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }))

export default function UsersPage() {
  const { user: me } = useAuthStore()
  const isAdmin = me?.role === ROLES.admin

  const [users, setUsers]           = useState([])
  const [loading, setLoading]       = useState(false)
  const [modalOpen, setModalOpen]   = useState(false)
  const [pwdModalOpen, setPwdModal] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [saving, setSaving]         = useState(false)

  const [form]    = Form.useForm()
  const [pwdForm] = Form.useForm()

  const load = useCallback(() => {
    setLoading(true)
    getUsers()
      .then(r => setUsers(r.data))
      .catch(() => message.error('Не удалось загрузить пользователей'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const openCreate = () => {
    setEditingUser(null)
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = (record) => {
    setEditingUser(record)
    form.setFieldsValue({
      full_name:  record.full_name,
      username:   record.username,
      department: record.department,
      role:       record.role,
      is_active:  record.is_active,
    })
    setModalOpen(true)
  }

  const openResetPwd = (record) => {
    setEditingUser(record)
    pwdForm.resetFields()
    setPwdModal(true)
  }

  const handleSave = async (vals) => {
    setSaving(true)
    try {
      if (editingUser) {
        await updateUser(editingUser.id, {
          full_name:  vals.full_name,
          department: vals.department,
          role:       vals.role,
          is_active:  vals.is_active,
        })
        message.success('Пользователь обновлён')
      } else {
        await createUser(vals)
        message.success('Пользователь создан')
      }
      setModalOpen(false)
      load()
    } catch (e) {
      message.error(e?.response?.data?.detail || 'Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  const handleResetPwd = async (vals) => {
    setSaving(true)
    try {
      await resetPassword(editingUser.id, { new_password: vals.new_password })
      message.success('Пароль изменён')
      setPwdModal(false)
    } catch {
      message.error('Ошибка смены пароля')
    } finally {
      setSaving(false)
    }
  }

  const columns = [
    {
      title: 'ФИО',
      dataIndex: 'full_name',
      key: 'full_name',
      sorter: (a, b) => a.full_name.localeCompare(b.full_name),
    },
    {
      title: 'Логин',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: 'Роль',
      dataIndex: 'role',
      key: 'role',
      render: (role) => <Tag>{ROLE_LABELS[role] || role}</Tag>,
    },
    {
      title: 'Отдел',
      dataIndex: 'department',
      key: 'department',
      render: (v) => v || '—',
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (v) => v
        ? <Tag color="green">Активен</Tag>
        : <Tag color="red">Деактивирован</Tag>,
    },
    ...(isAdmin ? [{
      title: 'Действия',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            Изменить
          </Button>
          <Button size="small" icon={<KeyOutlined />} onClick={() => openResetPwd(record)}>
            Пароль
          </Button>
        </Space>
      ),
    }] : []),
  ]

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Пользователи</Title>
        {isAdmin && (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Новый пользователь
          </Button>
        )}
      </div>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={users}
        loading={loading}
        pagination={{ pageSize: 20, showTotal: (t) => `Всего: ${t}` }}
        size="small"
      />

      {/* Модал создания / редактирования */}
      <Modal
        title={editingUser ? 'Редактировать пользователя' : 'Новый пользователь'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        okText="Сохранить"
        cancelText="Отмена"
        confirmLoading={saving}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" onFinish={handleSave} style={{ marginTop: 16 }}>
          <Form.Item name="full_name" label="ФИО" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          {!editingUser && (
            <>
              <Form.Item name="username" label="Логин" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="password" label="Пароль" rules={[{ required: true, min: 4 }]}>
                <Input.Password />
              </Form.Item>
            </>
          )}
          <Form.Item name="role" label="Роль" rules={[{ required: true }]}>
            <Select options={ROLE_OPTIONS} />
          </Form.Item>
          <Form.Item name="department" label="Отдел">
            <Input />
          </Form.Item>
          {editingUser && (
            <Form.Item name="is_active" label="Активен" valuePropName="checked">
              <Switch />
            </Form.Item>
          )}
        </Form>
      </Modal>

      {/* Модал смены пароля */}
      <Modal
        title={`Сменить пароль — ${editingUser?.full_name}`}
        open={pwdModalOpen}
        onCancel={() => setPwdModal(false)}
        onOk={() => pwdForm.submit()}
        okText="Сменить"
        cancelText="Отмена"
        confirmLoading={saving}
        destroyOnHidden
      >
        <Form form={pwdForm} layout="vertical" onFinish={handleResetPwd} style={{ marginTop: 16 }}>
          <Form.Item
            name="new_password"
            label="Новый пароль"
            rules={[{ required: true, min: 4, message: 'Минимум 4 символа' }]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item
            name="confirm"
            label="Подтвердите пароль"
            dependencies={['new_password']}
            rules={[
              { required: true },
              ({ getFieldValue }) => ({
                validator(_, v) {
                  return v && getFieldValue('new_password') === v
                    ? Promise.resolve()
                    : Promise.reject('Пароли не совпадают')
                },
              }),
            ]}
          >
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
