import client from './client'

export const getExpenses   = (params) => client.get('/expenses', { params })
export const getExpense    = (id)     => client.get(`/expenses/${id}`)
export const createExpense = (data)   => client.post('/expenses', data)
export const cancelExpense = (id, reason) => client.patch(`/expenses/${id}/cancel`, { cancel_reason: reason })
