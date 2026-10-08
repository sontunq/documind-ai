import { useCallback, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { listDocuments, hasProcessingDocuments } from '../lib/api/documents'
import { useQuery } from '../features/documents/useQuery'
import { Status } from '../features/documents/Metadata'
import { formatDate, formatSize } from '../features/documents/format'
import { ErrorNotice, Loading } from '../components/Feedback'
import { useI18n } from '../lib/i18n'

const PAGE_SIZE = 10

function DocumentList({ page }: { page: number }) {
  const { t, formatTemplate } = useI18n()
  const load = useCallback(
    (signal: AbortSignal) =>
      listDocuments(PAGE_SIZE + 1, (page - 1) * PAGE_SIZE, signal),
    [page],
  )
  const state = useQuery(load, hasProcessingDocuments)
  if (state.loading) return <Loading>{t.feedback.loadingDocs}</Loading>
  if (state.error !== undefined) return <ErrorNotice message={state.error} />
  const documents = state.data.slice(0, PAGE_SIZE)
  return (
    <>
      {documents.length === 0 ? (
        <div className="panel py-16 text-center">
          <div
            className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100 text-2xl"
            aria-hidden="true"
          >
            ▤
          </div>
          <h2 className="text-lg font-semibold">
            {page === 1
              ? t.documentsPage.emptyTitleFirst
              : t.documentsPage.emptyTitlePage}
          </h2>
          <p className="mt-2 text-sm text-slate-500">
            {page === 1
              ? t.documentsPage.emptyDescFirst
              : t.documentsPage.emptyDescPage}
          </p>
          {page === 1 && (
            <Link className="button-primary mt-6" to="/upload">
              {t.documentsPage.uploadFirst}
            </Link>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">
              {t.documentsPage.subtitle}
            </caption>
            <thead className="border-b border-slate-200 bg-slate-50 text-xs text-slate-500">
              <tr>
                {[
                  t.documentsPage.thDocument,
                  t.documentsPage.thStatus,
                  t.documentsPage.thMediaType,
                  t.documentsPage.thSize,
                  t.documentsPage.thUploaded,
                ].map((label) => (
                  <th
                    scope="col"
                    key={label}
                    className="whitespace-nowrap px-5 py-4 font-medium"
                  >
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {documents.map((document) => (
                <tr key={document.id} className="hover:bg-slate-50">
                  <td className="min-w-56 max-w-80 px-5 py-5">
                    <Link
                      className="text-link break-all"
                      to={`/documents/${document.id}`}
                    >
                      {document.original_filename}
                    </Link>
                  </td>
                  <td className="px-5 py-5">
                    <Status status={document.status} />
                  </td>
                  <td className="whitespace-nowrap px-5 py-5 text-slate-500">
                    {document.media_type}
                  </td>
                  <td className="whitespace-nowrap px-5 py-5 text-slate-500">
                    {formatSize(document.size_bytes)}
                  </td>
                  <td className="whitespace-nowrap px-5 py-5 text-slate-500">
                    {formatDate(document.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <nav
        aria-label={t.documentsPage.ariaNav}
        className="mt-5 flex items-center justify-between gap-3 text-sm"
      >
        <span className="text-slate-500">
          {formatTemplate(t.documentsPage.pageLabel, { page })} · {documents.length}{' '}
          {t.documentsPage.title.toLowerCase()}
        </span>
        <div className="flex gap-2">
          {page > 1 ? (
            <Link className="button-secondary" to={`?page=${page - 1}`}>
              {t.documentsPage.prev}
            </Link>
          ) : (
            <button className="button-secondary" disabled>
              {t.documentsPage.prev}
            </button>
          )}
          {state.data.length > PAGE_SIZE ? (
            <Link className="button-secondary" to={`?page=${page + 1}`}>
              {t.documentsPage.next}
            </Link>
          ) : (
            <button className="button-secondary" disabled>
              {t.documentsPage.next}
            </button>
          )}
        </div>
      </nav>
    </>
  )
}

export function DocumentsPage() {
  const { t } = useI18n()
  const [params] = useSearchParams()
  const rawPage = Number(params.get('page') || 1)
  const page =
    Number.isSafeInteger(rawPage) && rawPage > 0 && rawPage <= 100_000
      ? rawPage
      : 1
  const [revision, setRevision] = useState(0)
  return (
    <>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-5">
        <div>
          <p className="eyebrow">{t.documentsPage.eyebrow}</p>
          <h1 className="page-title">{t.documentsPage.title}</h1>
          <p className="mt-3 text-sm text-slate-500">
            {t.documentsPage.subtitle}
          </p>
        </div>
        <div className="flex gap-3">
          <button
            className="button-secondary"
            onClick={() => setRevision(revision + 1)}
          >
            {t.documentPage.refresh}
          </button>
          <Link className="button-primary" to="/upload">
            + {t.nav.upload}
          </Link>
        </div>
      </div>
      <DocumentList key={`${page}-${revision}`} page={page} />
    </>
  )
}
