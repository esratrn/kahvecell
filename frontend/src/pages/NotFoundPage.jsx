import { Link } from 'react-router-dom'

import Placeholder from '../components/Placeholder'

export default function NotFoundPage() {
  return (
    <Placeholder title="Sayfa bulunamadı" description="Aradığın sayfa yok ya da taşınmış olabilir.">
      <Link to="/">Ana sayfaya dön</Link>
    </Placeholder>
  )
}
