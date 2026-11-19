export default function Placeholder({ title, description, children }) {
  return (
    <section className="card">
      <h1>{title}</h1>
      <p className="muted">{description}</p>
      {children && <div className="stack">{children}</div>}
    </section>
  )
}
