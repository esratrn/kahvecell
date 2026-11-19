"""menu categories: espresso based / filter / cold drinks / other

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-19 23:30:00

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Kategori sütunu VARCHAR olduğu için şema değişmez; yalnızca mevcut değerler taşınır.
    op.execute("UPDATE products SET category = 'ESPRESSO_BASED' WHERE category = 'HOT_COFFEE'")
    op.execute("UPDATE products SET category = 'FILTER_COFFEE' WHERE name = 'Filtre Kahve'")
    op.execute("UPDATE products SET category = 'OTHER' WHERE name = 'Türk Kahvesi'")
    op.execute("UPDATE products SET category = 'COLD_DRINK' WHERE category = 'COLD_COFFEE'")
    op.execute("UPDATE products SET category = 'OTHER' WHERE category = 'TEA'")


def downgrade() -> None:
    # Eski yapıda ayrı çay kategorisi vardı; ad üzerinden geri ayrılır.
    op.execute("UPDATE products SET category = 'TEA' WHERE category = 'OTHER' AND name LIKE '%Çay%'")
    op.execute(
        "UPDATE products SET category = 'HOT_COFFEE' "
        "WHERE category IN ('ESPRESSO_BASED', 'FILTER_COFFEE') OR name = 'Türk Kahvesi'"
    )
    op.execute("UPDATE products SET category = 'COLD_COFFEE' WHERE category = 'COLD_DRINK'")
