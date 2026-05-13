import client from './client'

export const getSupplies    = (params) => client.get('/supplies', { params })
export const getSupply      = (id)     => client.get(`/supplies/${id}`)
export const createSupply   = (data)   => client.post('/supplies', data)
export const confirmSupply  = (id)     => client.post(`/supplies/${id}/confirm`)
export const deleteSupply   = (id)     => client.delete(`/supplies/${id}`)
export const downloadSupplyPdf = (id)       => client.get(`/supplies/${id}/pdf`, { responseType: 'blob' })
export const updateSupply      = (id, data) => client.patch(`/supplies/${id}`, data)
