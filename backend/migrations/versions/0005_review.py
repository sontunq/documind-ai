"""Phase 6 visual review and correction schema: document revision and reviews audit trail."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005_review"
down_revision = "0004_extraction"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("revision", sa.Integer(), nullable=False, server_default="1"))
    op.create_check_constraint("ck_documents_revision", "documents", "revision > 0")

    op.create_table(
        "reviews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("reviewer_id", sa.String(128), nullable=False),
        sa.Column("document_type", sa.String(32), nullable=True),
        sa.Column("fields", JSONB(), nullable=False),
        sa.Column("rejection_reason", sa.String(255), nullable=True),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_id", "revision", name="uq_review_doc_revision"),
        sa.CheckConstraint("revision > 0", name="ck_review_revision"),
        sa.CheckConstraint("status IN ('APPROVED','CORRECTED','REJECTED')", name="ck_review_status"),
    )
    op.create_index("ix_reviews_document_id", "reviews", ["document_id"])
    op.create_index("ix_reviews_created_at", "reviews", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_reviews_created_at", table_name="reviews")
    op.drop_index("ix_reviews_document_id", table_name="reviews")
    op.drop_table("reviews")
    op.drop_constraint("ck_documents_revision", "documents", type_="check")
    op.drop_column("documents", "revision")
