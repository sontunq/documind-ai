import { useCallback, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getDocument, getDocumentResults, isProcessing } from '../lib/api/documents'
import { Classification } from '../features/documents/Classification'
import { Extraction } from '../features/documents/Extraction'
import { Metadata, Status } from '../features/documents/Metadata'
import { useQuery } from '../features/documents/useQuery'
import { ErrorNotice, Loading } from '../components/Feedback'
import { useI18n } from '../lib/i18n'

function DocumentDetail({ id, retry }: { id: string; retry: () => void }) {
  const { t } = useI18n()
  const load = useCallback(
    async (signal: AbortSignal) => {
      const [document, results] = await Promise.all([getDocument(id, signal), getDocumentResults(id, signal)])
      return { ...document, status: results.status, results }
    },
    [id],
  )
  const state = useQuery(load, isProcessing)
  if (state.loading) return <Loading>{t.documentPage.loading}</Loading>
  if (state.error !== undefined)
    return <ErrorNotice message={state.error} onRetry={retry} />
  return (
    <div className="panel">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 pb-6">
        <div className="min-w-0">
          <p className="eyebrow">{t.documentPage.eyebrow}</p>
          <h1 className="mt-2 break-all text-2xl font-semibold tracking-tight">
            {state.data.original_filename}
          </h1>
        </div>
        <Status status={state.data.status} />
      </div>
      <Metadata document={state.data} technical />
      <Classification results={state.data.results} />
      <Extraction results={state.data.results} />
      <button className="button-secondary mt-6" onClick={retry}>
        {t.documentPage.refresh}
      </button>
      <p className="mt-6 text-xs text-slate-500">
        {t.documentPage.tzNotice}
      </p>
    </div>
  )
}

export function DocumentPage() {
  const { t } = useI18n()
  const { id = '' } = useParams()
  const [revision, setRevision] = useState(0)
  return (
    <>
      <Link className="text-link mb-6 inline-block text-sm" to="/documents">
        {t.documentPage.back}
      </Link>
      <DocumentDetail
        key={`${id}-${revision}`}
        id={id}
        retry={() => setRevision(revision + 1)}
      />
    </>
  )
}
