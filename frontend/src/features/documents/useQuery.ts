import { useEffect, useState } from 'react'
import { errorMessage } from '../../lib/api/client'

type QueryState<T> =
  | { loading: true; data?: never; error?: never }
  | { loading: false; data: T; error?: never }
  | { loading: false; data?: never; error: string }

// Callers memoize load and key the query component by its parameters/retry count
// so each new query starts in loading state. Cleanup ignores stale responses.
export function useQuery<T>(
  load: (signal: AbortSignal) => Promise<T>,
  pollWhile?: (data: T) => boolean,
) {
  const [state, setState] = useState<QueryState<T>>({ loading: true })
  useEffect(() => {
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout> | undefined
    function refresh() {
      load(controller.signal).then(
        (data) => {
          if (controller.signal.aborted) return
          setState({ loading: false, data })
          if (pollWhile?.(data)) timer = setTimeout(refresh, 2000)
        },
        (error) => {
          if (!controller.signal.aborted)
            setState({ loading: false, error: errorMessage(error) })
        },
      )
    }
    refresh()
    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [load, pollWhile])
  return state
}
