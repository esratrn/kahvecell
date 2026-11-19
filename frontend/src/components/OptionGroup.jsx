export default function OptionGroup({ name, label, options, value, onChange }) {
  return (
    <fieldset className="option-group">
      <legend>{label}</legend>
      <div className="options">
        {options.map((option) => (
          <label key={option.value} className={option.value === value ? 'option selected' : 'option'}>
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={option.value === value}
              onChange={() => onChange(option.value)}
            />
            {option.label}
          </label>
        ))}
      </div>
    </fieldset>
  )
}
