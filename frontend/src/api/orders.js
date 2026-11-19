import { client, request } from './client'

// order: { shop_id, product_id, size, sugar_level, milk, extra_shots, note }
export const placeOrder = (order) => request(client.post('/orders', order))

export const getOrder = (orderId) => request(client.get(`/orders/${orderId}`))

export const listOrderHistory = ({ offset = 0, limit = 20 } = {}) =>
  request(client.get('/orders/history', { params: { offset, limit } }))

export const cancelOrder = (orderId) => request(client.post(`/orders/${orderId}/cancel`))

export const reorder = (orderId) => request(client.post(`/orders/${orderId}/reorder`))
