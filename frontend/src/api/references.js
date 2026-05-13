import client from './client'

export const getCategories   = ()       => client.get('/references/categories')
export const createCategory  = (data)   => client.post('/references/categories', data)
export const deleteCategory  = (id)     => client.delete(`/references/categories/${id}`)

export const getSubgroups    = (params) => client.get('/references/subgroups', { params })
export const createSubgroup  = (data)   => client.post('/references/subgroups', data)

export const getSuppliers    = ()       => client.get('/references/suppliers')
export const createSupplier  = (data)   => client.post('/references/suppliers', data)
export const deleteSupplier  = (id)     => client.delete(`/references/suppliers/${id}`)

export const getProducts     = (params) => client.get('/references/products', { params })
export const createProduct   = (data)   => client.post('/references/products', data)
export const updateProduct   = (id, d)  => client.patch(`/references/products/${id}`, d)
export const deleteProduct   = (id)     => client.delete(`/references/products/${id}`)
