import { useI18n } from '../lib/i18n'

export function Loading({
  children,
}: {
  children?: string
}) {
  const { t } = useI18n()
  return (
    <div role="status" className="panel py-16 text-center text-slate-500">
      <span
        aria-hidden="true"
        className="mr-3 inline-block h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-emerald-700"
      />
      {children ?? t.feedback.loadingDocs}
    </div>
  )
}

export function ErrorNotice({
  message,
  onRetry,
}: {
  message: string
  onRetry?: () => void
}) {
  const { t } = useI18n()
  return (
    <div
      role="alert"
      className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-900"
    >
      <p>{message}</p>
      {onRetry && (
        <button className="button-secondary mt-4" onClick={onRetry}>
          {t.feedback.tryAgain}
        </button>
      )}
    </div>
  )
}
