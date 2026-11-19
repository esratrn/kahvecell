import { client, request } from './client'

export const listPlans = () => request(client.get('/subscriptions/plans'))

export const getMySubscription = () => request(client.get('/subscriptions/me'))

export const subscribe = (planCode, card) =>
  request(client.post('/subscriptions', { plan_code: planCode, card }))

export const changePlan = (planCode, card = null) =>
  request(client.patch('/subscriptions/me', { plan_code: planCode, card }))

export const cancelSubscription = () => request(client.delete('/subscriptions/me'))

export const listMyPayments = () => request(client.get('/payments/me'))
