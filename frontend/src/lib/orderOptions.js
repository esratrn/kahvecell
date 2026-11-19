export const SIZE_OPTIONS = [
  { value: 'S', label: 'Küçük (S)' },
  { value: 'M', label: 'Orta (M)' },
  { value: 'L', label: 'Büyük (L)' },
]

export const SUGAR_OPTIONS = [
  { value: 0, label: 'Şekersiz' },
  { value: 1, label: 'Az' },
  { value: 2, label: 'Orta' },
  { value: 3, label: 'Çok' },
]

export const MILK_OPTIONS = [
  { value: 'NONE', label: 'Sütsüz' },
  { value: 'WHOLE', label: 'Tam yağlı süt' },
  { value: 'LACTOSE_FREE', label: 'Laktozsuz süt' },
  { value: 'OAT', label: 'Yulaf sütü' },
  { value: 'ALMOND', label: 'Badem sütü' },
  { value: 'SOY', label: 'Soya sütü' },
]

export const EXTRA_SHOT_OPTIONS = [
  { value: 0, label: 'Yok' },
  { value: 1, label: '+1' },
  { value: 2, label: '+2' },
  { value: 3, label: '+3' },
]

const labelOf = (options, value) => options.find((option) => option.value === value)?.label

export function describeCustomization({ size, milk, sugar_level, extra_shots }) {
  const parts = [`${size} boy`, labelOf(MILK_OPTIONS, milk)]
  parts.push(sugar_level === 0 ? 'Şekersiz' : `${labelOf(SUGAR_OPTIONS, sugar_level)} şekerli`)
  if (extra_shots) {
    parts.push(`${extra_shots} ekstra shot`)
  }
  return parts.join(' · ')
}
