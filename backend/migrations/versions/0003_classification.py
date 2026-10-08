"""Phase 4 immutable classification payload belongs to its source OCR run."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003_classification"
down_revision = "0002_ocr_processing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("processing_runs", sa.Column("classification", JSONB(), nullable=True))
    op.add_column("processing_runs", sa.Column("classification_seconds", sa.Float(), nullable=True))
    op.create_check_constraint("ck_classification_duration", "processing_runs",
                               "classification_seconds IS NULL OR classification_seconds >= 0")
    op.create_check_constraint("ck_classification_result", "processing_runs",
                               "classification IS NULL OR (result IS NOT NULL AND status = 'COMPLETED')")


def downgrade() -> None:
    op.drop_constraint("ck_classification_result", "processing_runs", type_="check")
    op.drop_constraint("ck_classification_duration", "processing_runs", type_="check")
    op.drop_column("processing_runs", "classification_seconds")
    op.drop_column("processing_runs", "classification")
    op.execute("UPDATE documents SET status = 'COMPLETED' WHERE status = 'NEEDS_REVIEW'")
