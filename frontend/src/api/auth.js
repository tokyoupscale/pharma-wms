import client from './client'

export const login = (username, password) => {
  const form = new URLSearchParams()
  form.append('username', username)
  form.append('password', password)
  return client.post('/auth/login', form)
}

export const getMe         = ()           => client.get('/auth/me')
export const logoutApi     = ()           => client.post('/auth/logout')
export const register      = (data)       => client.post('/auth/register', data)
export const getUsers      = ()           => client.get('/auth/users')
export const createUser    = (data)       => client.post('/auth/users', data)
export const updateUser    = (id, data)   => client.patch(`/auth/users/${id}`, data)
export const resetPassword = (id, data)  => client.patch(`/auth/users/${id}/reset-password`, data)
