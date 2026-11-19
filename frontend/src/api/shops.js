import { client, request } from './client'

// params: { lat, lng, radius, q, min_rating, open_now, sort }
export const listShops = (params = {}) => request(client.get('/shops', { params }))

export const getShop = (shopId, location) =>
  request(client.get(`/shops/${shopId}`, { params: location ?? {} }))
