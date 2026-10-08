from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DocumentRow(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("status IN ('UPLOADED','QUEUED','PROCESSING','NEEDS_REVIEW','COMPLETED','FAILED')", name="ck_documents_status"),
        CheckConstraint("size_bytes > 0", name="ck_documents_size"),
        CheckConstraint("page_count IS NULL OR page_count > 0", name="ck_documents_pages"),
        CheckConstraint("updated_at >= created_at", name="ck_documents_timestamps"),
        CheckConstraint("revision > 0", name="ck_documents_revision"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(32), unique=True)
    media_type: Mapped[str] = mapped_column(String(32))
    size_bytes: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    page_count: Mapped[int | None] = mapped_column(Integer)
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProcessingRunRow(Base):
    __tablename__ = "processing_runs"
    __table_args__ = (
        UniqueConstraint("document_id", "pipeline_version", "attempt", name="uq_run_attempt"),
        CheckConstraint("status IN ('QUEUED','PROCESSING','COMPLETED','FAILED')", name="ck_run_status"),
        CheckConstraint("attempt > 0", name="ck_run_attempt"),
        CheckConstraint("total_seconds IS NULL OR total_seconds >= 0", name="ck_run_duration"),
        CheckConstraint("classification_seconds IS NULL OR classification_seconds >= 0", name="ck_classification_duration"),
        CheckConstraint("classification IS NULL OR (result IS NOT NULL AND status = 'COMPLETED')", name="ck_classification_result"),
        CheckConstraint("extraction_seconds IS NULL OR extraction_seconds >= 0", name="ck_extraction_duration"),
        CheckConstraint("extraction IS NULL OR (result IS NOT NULL AND status = 'COMPLETED')", name="ck_extraction_result"),
        CheckConstraint("NOT is_current OR (status = 'COMPLETED' AND result IS NOT NULL)", name="ck_run_current"),
        Index("uq_run_current", "document_id", unique=True, postgresql_where=text("is_current")),
        Index("uq_run_active", "document_id", unique=True, postgresql_where=text("status IN ('QUEUED','PROCESSING')")),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), index=True)
    pipeline_version: Mapped[str] = mapped_column(String(64))
    config_version: Mapped[str] = mapped_column(String(64))
    config: Mapped[dict] = mapped_column(JSONB)
    attempt: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_seconds: Mapped[float | None] = mapped_column(Float)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(String(255))
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    classification: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    classification_seconds: Mapped[float | None] = mapped_column(Float)
    extraction: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    extraction_seconds: Mapped[float | None] = mapped_column(Float)


class ReviewRow(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("document_id", "revision", name="uq_review_doc_revision"),
        CheckConstraint("revision > 0", name="ck_review_revision"),
        CheckConstraint("status IN ('APPROVED','CORRECTED','REJECTED')", name="ck_review_status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    reviewer_id: Mapped[str] = mapped_column(String(128))
    document_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fields: Mapped[list] = mapped_column(JSONB, default=list)
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
