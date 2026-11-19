import { Link } from 'react-router-dom'

import Placeholder from '../components/Placeholder'

export default function RegisterPage() {
  return (
    <Placeholder
      title="Kayıt: profilini tamamla"
      description="İlk girişte ad soyad, e-posta, kahve tercihleri ve alerjen bilgileri alınacak."
    >
      <Link to="/">Kaydı bitirince ana sayfaya →</Link>
    </Placeholder>
  )
}
