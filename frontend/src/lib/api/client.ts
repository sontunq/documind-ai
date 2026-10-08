export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, {
      ...options,
      signal: options.signal
        ? AbortSignal.any([options.signal, AbortSignal.timeout(60_000)])
        : AbortSignal.timeout(60_000),
    })
  } catch (error) {
    if (options.signal?.aborted) throw error
    throw new Error(
      'Could not reach the backend or the request timed out. Check your connection and try again. If uploading, check Documents before retrying.',
    )
  }
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(
      data?.error?.message ||
        `Request failed (${response.status}). Please try again.`,
      response.status,
    )
  }
  if (data === null)
    throw new Error('The backend returned an unexpected response.')
  return data as T
}

export function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : 'Something went wrong. Please try again.'
}
