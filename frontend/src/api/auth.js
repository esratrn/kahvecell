import { client, request } from './client'

export const requestOtp = (phoneNumber) =>
  request(client.post('/auth/register', { phone_number: phoneNumber }))

export const verifyOtp = (phoneNumber, otpCode) =>
  request(client.post('/auth/verify-otp', { phone_number: phoneNumber, otp_code: otpCode }))

export const logout = (refreshToken) => request(client.post('/auth/logout', { refresh_token: refreshToken }))

export const getMe = () => request(client.get('/users/me'))

export const updateProfile = (profile) => request(client.patch('/users/me', profile))
