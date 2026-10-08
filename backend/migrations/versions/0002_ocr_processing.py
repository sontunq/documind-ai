"""Phase 3 lifecycle and versioned OCR processing runs only."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002_ocr_processing"
down_revision = "0001_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_documents_status", "documents", type_="check")
    op.create_check_constraint("ck_documents_status", "documents",
                               "status IN ('UPLOADED','QUEUED','PROCESSING','NEEDS_REVIEW','COMPLETED','FAILED')")
    op.create_table(
        "processing_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("pipeline_version", sa.String(64), nullable=False),
        sa.Column("config_version", sa.String(64), nullable=False),
        sa.Column("config", JSONB(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("total_seconds", sa.Float()),
        sa.Column("error_code", sa.String(64)),
        sa.Column("error_message", sa.String(255)),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("result", JSONB()),
        sa.UniqueConstraint("document_id", "pipeline_version", "attempt", name="uq_run_attempt"),
        sa.CheckConstraint("status IN ('QUEUED','PROCESSING','COMPLETED','FAILED')", name="ck_run_status"),
        sa.CheckConstraint("attempt > 0", name="ck_run_attempt"),
        sa.CheckConstraint("total_seconds IS NULL OR total_seconds >= 0", name="ck_run_duration"),
        sa.CheckConstraint("NOT is_current OR (status = 'COMPLETED' AND result IS NOT NULL)", name="ck_run_current"),
    )
    op.create_index("ix_processing_runs_document_id", "processing_runs", ["document_id"])
    op.create_index("uq_run_current", "processing_runs", ["document_id"], unique=True,
                    postgresql_where=sa.text("is_current"))
    op.create_index("uq_run_active", "processing_runs", ["document_id"], unique=True,
                    postgresql_where=sa.text("status IN ('QUEUED','PROCESSING')"))


def downgrade() -> None:
    # Downgrade explicitly discards Phase 3 results and restores Phase 1 semantics.
    op.drop_table("processing_runs")
    op.execute("UPDATE documents SET status = 'UPLOADED'")
    op.drop_constraint("ck_documents_status", "documents", type_="check")
    op.create_check_constraint("ck_documents_status", "documents", "status = 'UPLOADED'")
