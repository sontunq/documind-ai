"""Phase 5 structured field extraction payload belongs to its source OCR run."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004_extraction"
down_revision = "0003_classification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("processing_runs", sa.Column("extraction", JSONB(), nullable=True))
    op.add_column("processing_runs", sa.Column("extraction_seconds", sa.Float(), nullable=True))
    op.create_check_constraint("ck_extraction_duration", "processing_runs",
                               "extraction_seconds IS NULL OR extraction_seconds >= 0")
    op.create_check_constraint("ck_extraction_result", "processing_runs",
                               "extraction IS NULL OR (result IS NOT NULL AND status = 'COMPLETED')")


def downgrade() -> None:
    op.drop_constraint("ck_extraction_result", "processing_runs", type_="check")
    op.drop_constraint("ck_extraction_duration", "processing_runs", type_="check")
    op.drop_column("processing_runs", "extraction_seconds")
    op.drop_column("processing_runs", "extraction")
