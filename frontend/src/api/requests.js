import client from './client'

export const getRequests     = (params) => client.get('/requests', { params })
export const createRequest   = (data)   => client.post('/requests', data)
export const approveRequest  = (id)     => client.post(`/requests/${id}/approve`)
export const rejectRequest   = (id, reason) => client.post(`/requests/${id}/reject`, { reject_reason: reason })
export const downloadRequestPdf = (id) => client.get(`/requests/${id}/pdf`, { responseType: 'blob' })
