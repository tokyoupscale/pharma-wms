import client from './client'

export const getProductCard     = (id, params) => client.get(`/reports/product-card/${id}`, { params })
export const getStockBySubgroup = ()           => client.get('/reports/stock-by-subgroup')
export const getLowStock        = ()           => client.get('/reports/low-stock')
export const getDashboardStats  = ()           => client.get('/reports/dashboard-stats')
