import client from './client'

export const getLimitCards    = (params) => client.get('/limit-cards', { params })
export const getLimitCard     = (id)     => client.get(`/limit-cards/${id}`)
export const closeLimitCard   = (id)     => client.post(`/limit-cards/${id}/close`)
export const setAllocation    = (id, d)  => client.post(`/limit-cards/${id}/allocations`, d)
export const downloadLimitCardPdf = (id) => client.get(`/limit-cards/${id}/pdf`, { responseType: 'blob' })
