import { Form, Input, Button, Card, Typography, Alert, Modal, Select, Divider, notification, theme as antTheme } from 'antd'
import { UserOutlined, LockOutlined, QuestionCircleOutlined, UserAddOutlined } from '@ant-design/icons'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login, register, getMe } from '../../api/auth'
import { useAuthStore } from '../../store/authStore'

const { Title, Text } = Typography

const DEPARTMENTS = [
  'ОМТС',
  'Цех АФС',
  'Цех ГЛС',
  'Отдел контроля качества',
  'Отдел технического контроля',
  'Планово-экономический отдел',
]

export default function LoginPage() {
  const { token } = antTheme.useToken()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [registerOpen, setRegisterOpen] = useState(false)
  const [forgotOpen, setForgotOpen] = useState(false)
  const [registerLoading, setRegisterLoading] = useState(false)
  const [registerForm] = Form.useForm()
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)

  const onLogin = async ({ username, password }) => {
    setLoading(true)
    setError(null)
    try {
      const res = await login(username, password)
      setAuth(res.data.access_token, { username })
      const me = await getMe()
      setAuth(res.data.access_token, me.data)
      navigate('/dashboard')
    } catch {
      setError('Неверный логин или пароль')
    } finally {
      setLoading(false)
    }
  }

  const onRegister = async (values) => {
    setRegisterLoading(true)
    try {
      await register({
        username: values.username,
        full_name: values.full_name,
        department: values.department,
        password: values.password,
      })
      notification.success({
        message: 'Регистрация прошла успешно',
        description: 'Теперь вы можете войти в систему.',
      })
      setRegisterOpen(false)
      registerForm.resetFields()
    } catch (e) {
      const msg = e.response?.data?.detail || 'Ошибка регистрации'
      notification.error({ message: msg })
    } finally {
      setRegisterLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: token.colorBgLayout }}>
      <Card style={{ width: 380, boxShadow: '0 4px 24px rgba(0,0,0,0.08)' }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <Title level={3} style={{ margin: 0 }}>ВИЛАР</Title>
          <Text type="secondary">Складская система</Text>
        </div>

        {error && <Alert message={error} type="error" showIcon style={{ marginBottom: 16 }} />}

        <Form onFinish={onLogin} layout="vertical" size="large">
          <Form.Item name="username" rules={[{ required: true, message: 'Введите логин' }]}>
            <Input prefix={<UserOutlined />} placeholder="Логин" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: 'Введите пароль' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="Пароль" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            Войти
          </Button>
        </Form>

        <Divider style={{ margin: '16px 0' }} />

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Button
            type="link"
            icon={<QuestionCircleOutlined />}
            style={{ padding: 0, fontSize: 13 }}
            onClick={() => setForgotOpen(true)}
          >
            Забыл пароль
          </Button>
          <Button
            type="link"
            icon={<UserAddOutlined />}
            style={{ padding: 0, fontSize: 13 }}
            onClick={() => setRegisterOpen(true)}
          >
            Регистрация
          </Button>
        </div>
      </Card>

      {/* Модальное окно: забыл пароль */}
      <Modal
        title={<><QuestionCircleOutlined style={{ marginRight: 8 }} />Забыли пароль?</>}
        open={forgotOpen}
        onCancel={() => setForgotOpen(false)}
        footer={<Button type="primary" onClick={() => setForgotOpen(false)}>Понятно</Button>}
      >
        <Text>
          Сбросить пароль может только администратор системы. Обратитесь к нему лично или по внутреннему каналу связи.
        </Text>
        <br /><br />
        <Text type="secondary" style={{ fontSize: 12 }}>
          Администратор использует раздел «Управление пользователями» для сброса пароля.
        </Text>
      </Modal>

      {/* Модальное окно: регистрация */}
      <Modal
        title={<><UserAddOutlined style={{ marginRight: 8 }} />Регистрация</>}
        open={registerOpen}
        onCancel={() => { setRegisterOpen(false); registerForm.resetFields() }}
        footer={null}
        width={440}
      >
        <Form
          form={registerForm}
          onFinish={onRegister}
          layout="vertical"
          size="middle"
          style={{ marginTop: 16 }}
        >
          <Form.Item
            name="full_name"
            label="ФИО"
            rules={[{ required: true, message: 'Введите ФИО' }]}
          >
            <Input placeholder="Иванов Иван Иванович" />
          </Form.Item>

          <Form.Item
            name="department"
            label="Отдел"
            rules={[{ required: true, message: 'Выберите отдел' }]}
          >
            <Select placeholder="Выберите отдел">
              {DEPARTMENTS.map((d) => (
                <Select.Option key={d} value={d}>{d}</Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="username"
            label="Логин"
            rules={[
              { required: true, message: 'Введите логин' },
              { min: 3, message: 'Минимум 3 символа' },
              { pattern: /^[a-zA-Z0-9_]+$/, message: 'Только латиница, цифры и _' },
            ]}
          >
            <Input placeholder="ivanov_ii" />
          </Form.Item>

          <Form.Item
            name="password"
            label="Пароль"
            rules={[{ required: true, message: 'Введите пароль' }, { min: 6, message: 'Минимум 6 символов' }]}
          >
            <Input.Password placeholder="Не менее 6 символов" />
          </Form.Item>

          <Form.Item
            name="confirm"
            label="Повторите пароль"
            dependencies={['password']}
            rules={[
              { required: true, message: 'Повторите пароль' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) return Promise.resolve()
                  return Promise.reject(new Error('Пароли не совпадают'))
                },
              }),
            ]}
          >
            <Input.Password placeholder="Повторите пароль" />
          </Form.Item>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <Button onClick={() => { setRegisterOpen(false); registerForm.resetFields() }}>
              Отмена
            </Button>
            <Button type="primary" htmlType="submit" loading={registerLoading}>
              Зарегистрироваться
            </Button>
          </div>
        </Form>
      </Modal>
    </div>
  )
}
