import type {
  DocumentResults,
  ExtractedField,
  ExtractionResult,
} from '../../lib/api/documents'
import { useI18n } from '../../lib/i18n'

const percent = (value: number) => `${(value * 100).toFixed(1)}%`

function FieldRow({ label, field }: { label: string; field?: ExtractedField | null }) {
  const { t, formatTemplate } = useI18n()
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between py-2 border-b border-slate-100 last:border-0 text-sm">
      <span className="font-medium text-slate-700">{label}</span>
      <div className="flex items-center gap-3 mt-1 sm:mt-0">
        {field && field.value !== null && field.value !== undefined ? (
          <>
            <span className="font-mono text-slate-900 font-semibold">{String(field.value)}</span>
            <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
              {t.extraction.conf}: {percent(field.confidence)}
            </span>
            {field.page && (
              <span className="text-xs text-slate-400">
                {formatTemplate(t.extraction.page, { page: field.page })}
              </span>
            )}
          </>
        ) : (
          <span className="text-xs italic text-slate-400">{t.extraction.notDetected}</span>
        )}
      </div>
    </div>
  )
}

function RenderInvoice({ extraction }: { extraction: ExtractionResult }) {
  const { t } = useI18n()
  const inv = extraction.invoice
  if (!inv) return <p className="text-sm text-slate-500">{t.extraction.noInvoiceFields}</p>
  return (
    <div className="space-y-1">
      <FieldRow label={t.extraction.fields.invoice_number} field={inv.invoice_number} />
      <FieldRow label={t.extraction.fields.supplier} field={inv.supplier} />
      <FieldRow label={t.extraction.fields.customer} field={inv.customer} />
      <FieldRow label={t.extraction.fields.issue_date} field={inv.issue_date} />
      <FieldRow label={t.extraction.fields.due_date} field={inv.due_date} />
      <FieldRow label={t.extraction.fields.subtotal} field={inv.subtotal} />
      <FieldRow label={t.extraction.fields.tax} field={inv.tax} />
      <FieldRow label={t.extraction.fields.total} field={inv.total} />
      <FieldRow label={t.extraction.fields.currency} field={inv.currency} />
    </div>
  )
}

function RenderContract({ extraction }: { extraction: ExtractionResult }) {
  const { t } = useI18n()
  const contract = extraction.contract
  if (!contract) return <p className="text-sm text-slate-500">{t.extraction.noContractFields}</p>
  return (
    <div className="space-y-1">
      <FieldRow label={t.extraction.fields.contract_number} field={contract.contract_number} />
      <FieldRow label={t.extraction.fields.title} field={contract.title} />
      <FieldRow label={t.extraction.fields.party_a} field={contract.party_a} />
      <FieldRow label={t.extraction.fields.party_b} field={contract.party_b} />
      <FieldRow label={t.extraction.fields.effective_date} field={contract.effective_date} />
      <FieldRow label={t.extraction.fields.expiry_date} field={contract.expiry_date} />
      <FieldRow label={t.extraction.fields.contract_value} field={contract.contract_value} />
      <FieldRow label={t.extraction.fields.governing_law} field={contract.governing_law} />
    </div>
  )
}

function RenderForm({ extraction }: { extraction: ExtractionResult }) {
  const { t } = useI18n()
  const form = extraction.form
  if (!form) return <p className="text-sm text-slate-500">{t.extraction.noFormFields}</p>
  return (
    <div className="space-y-1">
      <FieldRow label={t.extraction.fields.form_title} field={form.form_title} />
      {form.fields.length > 0 ? (
        form.fields.map((field, idx) => (
          <FieldRow key={`${field.name}-${idx}`} label={field.name} field={field} />
        ))
      ) : (
        <p className="text-sm text-slate-400 italic">{t.extraction.noFormFields}</p>
      )}
    </div>
  )
}

export function Extraction({ results }: { results: DocumentResults }) {
  const { t, formatTemplate } = useI18n()
  const extraction = results.current_run?.extraction
  const previous = results.current_run && results.latest_run?.id !== results.current_run.id

  const typeNameMap: Record<string, string> = {
    invoice: t.classification.typeInvoice,
    contract: t.classification.typeContract,
    form: t.classification.typeForm,
  }

  return (
    <section className="mt-8 border-t border-slate-100 pt-6" aria-labelledby="extraction-heading">
      <h2 id="extraction-heading" className="text-lg font-semibold">{t.extraction.heading}</h2>
      {extraction ? (
        <>
          <p className="mt-1 text-sm text-slate-500">
            {t.extraction.subtitle}{previous ? t.extraction.fromPrevious : ''} ({typeNameMap[extraction.document_type] ?? extraction.document_type})
          </p>
          <div className="mt-4 bg-slate-50 border border-slate-200/60 rounded-lg p-4">
            {extraction.document_type === 'invoice' && <RenderInvoice extraction={extraction} />}
            {extraction.document_type === 'contract' && <RenderContract extraction={extraction} />}
            {extraction.document_type === 'form' && <RenderForm extraction={extraction} />}
          </div>
          <p className="mt-2 text-xs text-slate-400">
            {formatTemplate(t.extraction.extractor, {
              name: extraction.extractor_name,
              version: extraction.extractor_version,
            })}
          </p>
        </>
      ) : (
        <p className="mt-3 text-sm text-slate-500">
          {results.status === 'QUEUED' || results.status === 'PROCESSING'
            ? t.extraction.willAppear
            : t.extraction.noFields}
        </p>
      )}
    </section>
  )
}
