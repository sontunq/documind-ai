import type { DocumentMetadata } from '../../lib/api/documents'
import { useI18n } from '../../lib/i18n'
import { formatDate, formatSize } from './format'

export function Status({ status }: { status: DocumentMetadata['status'] }) {
  const { t } = useI18n()
  const colors = status === 'FAILED'
    ? 'border-red-200 bg-red-50 text-red-800'
    : status === 'COMPLETED'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
      : status === 'NEEDS_REVIEW'
        ? 'border-amber-200 bg-amber-50 text-amber-800'
        : 'border-slate-200 bg-slate-50 text-slate-700'
  const label = t.status[status] ?? status
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold tracking-wide ${colors}`}>
      {label}
    </span>
  )
}

export function Metadata({
  document,
  technical = false,
}: {
  document: DocumentMetadata
  technical?: boolean
}) {
  const { t } = useI18n()
  const fields = [
    [t.metadata.originalFilename, document.original_filename],
    [t.metadata.mediaType, document.media_type],
    [
      t.metadata.fileSize,
      `${formatSize(document.size_bytes)} (${document.size_bytes.toLocaleString()} bytes)`,
    ],
    [t.metadata.pages, document.page_count ?? t.metadata.notAvailable],
    [t.metadata.created, formatDate(document.created_at)],
    [t.metadata.updated, formatDate(document.updated_at)],
  ]
  return (
    <>
      <dl className="grid gap-x-10 gap-y-6 sm:grid-cols-2">
        {fields.map(([label, value]) => (
          <div key={label}>
            <dt className="text-sm text-slate-500">{label}</dt>
            <dd className="mt-1 break-all text-sm font-medium text-slate-800">
              {value}
            </dd>
          </div>
        ))}
      </dl>
      {technical && (
        <details className="mt-8 border-t border-slate-200 pt-5">
          <summary className="cursor-pointer text-sm font-medium">
            {t.metadata.technical}
          </summary>
          <dl className="mt-4 space-y-4 text-sm">
            <div>
              <dt className="text-slate-500">{t.metadata.docId}</dt>
              <dd className="mt-1 break-all font-mono">{document.id}</dd>
            </div>
            <div>
              <dt className="text-slate-500">{t.metadata.checksum}</dt>
              <dd className="mt-1 break-all font-mono">{document.checksum}</dd>
            </div>
          </dl>
        </details>
      )}
    </>
  )
}
