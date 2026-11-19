const MONTHS = Array.from({ length: 12 }, (_, index) => index + 1)
const CURRENT_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: 11 }, (_, index) => CURRENT_YEAR + index)

function formatCardNumber(value) {
  return value
    .replace(/\D/g, '')
    .slice(0, 16)
    .replace(/(\d{4})(?=\d)/g, '$1-')
}

export default function CardFields({ value, onChange, disabled = false }) {
  const update = (field) => (event) => onChange({ ...value, [field]: event.target.value })

  return (
    <fieldset className="stack card-fields" disabled={disabled}>
      <label className="field">
        Kart numarası
        <input
          inputMode="numeric"
          autoComplete="off"
          value={value.card_number}
          onChange={(event) => onChange({ ...value, card_number: formatCardNumber(event.target.value) })}
          required
        />
        <span className="muted small">Test kartı, değiştirmeyin.</span>
      </label>
      <label className="field">
        Kart üzerindeki isim
        <input value={value.holder_name} onChange={update('holder_name')} minLength={2} required />
      </label>
      <div className="row">
        <label className="field grow">
          Ay
          <select
            value={value.expiry_month}
            onChange={(event) => onChange({ ...value, expiry_month: Number(event.target.value) })}
          >
            {MONTHS.map((month) => (
              <option key={month} value={month}>
                {String(month).padStart(2, '0')}
              </option>
            ))}
          </select>
        </label>
        <label className="field grow">
          Yıl
          <select
            value={value.expiry_year}
            onChange={(event) => onChange({ ...value, expiry_year: Number(event.target.value) })}
          >
            {YEARS.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </label>
        <label className="field grow">
          CVV
          <input
            inputMode="numeric"
            autoComplete="off"
            maxLength={3}
            value={value.cvv}
            onChange={(event) => onChange({ ...value, cvv: event.target.value.replace(/\D/g, '') })}
            required
          />
        </label>
      </div>
    </fieldset>
  )
}
