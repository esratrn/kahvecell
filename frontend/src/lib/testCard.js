// Ödeme simülasyonunun her zaman başarılı dönen test kartı (case 12.1).
export const TEST_CARD = {
  card_number: '4242-4242-4242-4242',
  expiry_month: 12,
  expiry_year: new Date().getFullYear() + 4,
  cvv: '123',
}
