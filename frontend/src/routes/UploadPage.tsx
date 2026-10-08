import { useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { uploadDocument, type DocumentMetadata } from '../lib/api/documents'
import { errorMessage } from '../lib/api/client'
import { Metadata, Status } from '../features/documents/Metadata'
import { formatSize } from '../features/documents/format'
import { ErrorNotice } from '../components/Feedback'
import { useI18n } from '../lib/i18n'

const configuredLimit = Number(import.meta.env.VITE_MAX_UPLOAD_BYTES)
const sizeLimit =
  Number.isSafeInteger(configuredLimit) && configuredLimit > 0
    ? configuredLimit
    : undefined

export function UploadPage() {
  const { t, formatTemplate } = useI18n()
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [created, setCreated] = useState<DocumentMetadata | null>(null)
  const [dragging, setDragging] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  const inFlight = useRef(false)

  function selectFiles(files: FileList | null) {
    setError(null)
    setCreated(null)
    setFile(null)
    if (!files?.length) return
    if (files.length !== 1) {
      setError(t.uploadPage.errSingle)
      return
    }
    const selected = files[0]
    if (!/\.(pdf|png|jpe?g)$/i.test(selected.name)) {
      setError(t.uploadPage.errFormat)
      return
    }
    if (selected.size === 0) {
      setError(t.uploadPage.errEmpty)
      return
    }
    if (sizeLimit && selected.size > sizeLimit) {
      setError(formatTemplate(t.uploadPage.errSize, { size: formatSize(sizeLimit) }))
      return
    }
    setFile(selected)
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (inFlight.current) return
    if (!file) {
      setError(t.uploadPage.errRequired)
      return
    }
    inFlight.current = true
    setUploading(true)
    setError(null)
    try {
      setCreated(await uploadDocument(file))
      setFile(null)
      if (input.current) input.current.value = ''
    } catch (error) {
      setError(errorMessage(error))
    } finally {
      setUploading(false)
      inFlight.current = false
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <p className="eyebrow">{t.uploadPage.eyebrow}</p>
      <h1 className="page-title">{t.uploadPage.title}</h1>
      <p className="mb-8 mt-3 text-sm text-slate-500">
        {t.uploadPage.desc}
      </p>
      {created ? (
        <section className="panel">
          <div role="status" className="mb-6">
            <h2 className="text-lg font-semibold text-emerald-800">
              {t.uploadPage.successTitle}
            </h2>
            <p className="mt-2 text-sm text-slate-500">
              {t.uploadPage.successDesc}
            </p>
          </div>
          <div className="mb-6">
            <Status status={created.status} />
          </div>
          <Metadata document={created} />
          <div className="mt-8 flex flex-wrap gap-3">
            <Link className="button-primary" to={`/documents/${created.id}`}>
              {t.uploadPage.viewDoc}
            </Link>
            <Link className="button-secondary" to="/documents">
              {t.uploadPage.allDocs}
            </Link>
            <button
              className="button-secondary"
              onClick={() => setCreated(null)}
            >
              {t.uploadPage.uploadAnother}
            </button>
          </div>
        </section>
      ) : (
        <form onSubmit={submit} className="panel" aria-busy={uploading}>
          <fieldset disabled={uploading}>
            <legend className="mb-4 text-sm font-semibold">
              {t.uploadPage.dragInactive}
            </legend>
            <div
              className={`rounded-xl border-2 border-dashed p-6 text-center sm:p-10 ${dragging ? 'border-emerald-600 bg-emerald-50' : 'border-slate-300 bg-slate-50'}`}
              onDragOver={(event) => {
                event.preventDefault()
                if (!uploading) setDragging(true)
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => {
                event.preventDefault()
                setDragging(false)
                if (!uploading) {
                  selectFiles(event.dataTransfer.files)
                  if (input.current) input.current.value = ''
                }
              }}
            >
              <span
                aria-hidden="true"
                className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl border border-slate-200 bg-white text-2xl text-emerald-800"
              >
                ↑
              </span>
              <p className="font-medium">
                {dragging ? t.uploadPage.dragActive : t.uploadPage.dragInactive}
              </p>
              <p className="mb-5 mt-2 text-sm text-slate-500">
                {t.uploadPage.orChoose}
              </p>
              <label htmlFor="document-file" className="sr-only">
                {t.uploadPage.title}
              </label>
              <input
                ref={input}
                id="document-file"
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
                aria-describedby="file-help"
                className="block w-full text-sm text-slate-600 file:mr-3 file:cursor-pointer file:rounded-lg file:border file:border-slate-300 file:bg-white file:px-4 file:py-2 file:font-medium file:text-slate-800"
                onChange={(event) => selectFiles(event.target.files)}
              />
              <p id="file-help" className="mt-5 text-xs text-slate-500">
                {t.uploadPage.rules}
                {sizeLimit
                  ? ` · ${formatTemplate(t.uploadPage.maxSize, { size: formatSize(sizeLimit) })}`
                  : ''}
              </p>
            </div>
            {file && (
              <div
                role="status"
                className="mt-5 flex items-center justify-between gap-4 rounded-lg border border-slate-200 p-4"
              >
                <div className="min-w-0">
                  <p className="break-all text-sm font-medium">{file.name}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {formatSize(file.size)}
                  </p>
                </div>
                <button
                  type="button"
                  className="text-link text-sm"
                  onClick={() => {
                    setFile(null)
                    setError(null)
                    if (input.current) input.current.value = ''
                  }}
                >
                  ✕
                </button>
              </div>
            )}
          </fieldset>
          {error && (
            <div className="mt-5">
              <ErrorNotice message={error} />
            </div>
          )}
          {uploading && (
            <p role="status" className="mt-5 text-sm text-slate-600">
              {t.uploadPage.uploading}
            </p>
          )}
          <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-slate-100 pt-6">
            <p className="max-w-sm text-xs leading-relaxed text-slate-500">
              {t.uploadPage.rules}
            </p>
            <button
              className="button-primary"
              type="submit"
              disabled={uploading}
            >
              {uploading ? t.uploadPage.uploading : t.uploadPage.submit}
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
