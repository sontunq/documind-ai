import type { DocumentResults } from '../../lib/api/documents'
import { useI18n } from '../../lib/i18n'

const percent = (value: number) => `${(value * 100).toFixed(1)}%`

export function Classification({ results }: { results: DocumentResults }) {
  const { t, formatTemplate } = useI18n()
  const prediction = results.current_run?.classification
  const previous = results.current_run && results.latest_run?.id !== results.current_run.id

  const typeNameMap: Record<string, string> = {
    invoice: t.classification.typeInvoice,
    contract: t.classification.typeContract,
    form: t.classification.typeForm,
  }

  return (
    <section className="mt-8 border-t border-slate-100 pt-6" aria-labelledby="classification-heading">
      <h2 id="classification-heading" className="text-lg font-semibold">{t.classification.heading}</h2>
      {results.latest_run?.error_message && (
        <p className="mt-3 text-sm text-red-700" role="status">{results.latest_run.error_message}</p>
      )}
      {prediction ? (
        <>
          <p className="mt-3 text-sm text-slate-500">
            {t.classification.prediction}{previous ? t.classification.fromPrevious : ''}
          </p>
          <p className="mt-1 text-xl font-semibold">
            {typeNameMap[prediction.predicted_type] ?? prediction.predicted_type}
          </p>
          <p className="mt-2 text-sm">{t.classification.probability}: {percent(prediction.confidence)}</p>
          <p className="mt-2 text-sm text-slate-600">
            {prediction.needs_review
              ? formatTemplate(t.classification.lowConfidence, { threshold: percent(prediction.threshold) })
              : t.classification.notGuarantee}
          </p>
          <details className="mt-4 text-sm">
            <summary className="cursor-pointer text-slate-600">{t.classification.detailsSummary}</summary>
            <dl className="mt-3 space-y-2 break-all">
              {Object.entries(prediction.scores).map(([label, score]) => (
                <div key={label}>
                  <dt className="inline font-medium">{typeNameMap[label] ?? label}: </dt>
                  <dd className="inline">{percent(score)}</dd>
                </div>
              ))}
              <div><dt className="font-medium inline">{t.classification.model}: </dt><dd className="inline">{prediction.model_identifier}</dd></div>
              <div><dt className="font-medium inline">{t.classification.modelVersion}: </dt><dd className="inline">{prediction.model_version}</dd></div>
              <div><dt className="font-medium inline">{t.classification.dataset}: </dt><dd className="inline">{prediction.dataset_version}</dd></div>
            </dl>
          </details>
        </>
      ) : (
        <p className="mt-3 text-sm text-slate-500">
          {results.status === 'QUEUED' || results.status === 'PROCESSING'
            ? t.classification.willAppear
            : t.classification.noResult}
        </p>
      )}
    </section>
  )
}
