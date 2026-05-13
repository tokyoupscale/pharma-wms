import client from './client'

export const getOperationsLog = (params) => client.get('/operations-log', { params })
