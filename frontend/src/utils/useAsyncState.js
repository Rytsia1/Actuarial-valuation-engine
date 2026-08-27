import { ref, shallowRef } from 'vue'

/**
 * Standardized Request State Machine with Race Condition Guards and AbortController Support
 * 
 * Features:
 * 1. Monotonic Request ID sequencing: Prevents out-of-order responses from overwriting newer requests.
 * 2. AbortController integration: Automatically aborts prior in-flight HTTP requests when a new request starts.
 * 3. Strict stale data invalidation on request dispatch and failure.
 */
export function createRequestState(initialData = null) {
  const data = shallowRef(initialData)
  const loading = ref(false)
  const error = ref(null)
  let currentRequestId = 0
  let currentAbortController = null

  /**
   * Dispatches a new request cycle.
   * - Aborts any prior in-flight HTTP request.
   * - Increments the request ID token.
   * - Invalidates previous stale data and sets loading = true.
   * 
   * @returns {{ requestId: number, signal: AbortSignal }}
   */
  function start() {
    if (currentAbortController) {
      try {
        currentAbortController.abort('New request initiated')
      } catch (_) {}
    }
    currentAbortController = new AbortController()
    const requestId = ++currentRequestId

    loading.value = true
    error.value = null
    data.value = null

    return {
      requestId,
      signal: currentAbortController.signal,
    }
  }

  /**
   * Commits the result of a request if and only if it matches the latest requestId.
   * 
   * @param {*} result - Successful response data
   * @param {number} requestId - Token returned by start()
   * @returns {boolean} true if committed, false if discarded as stale
   */
  function success(result, requestId = null) {
    if (requestId !== null && requestId !== currentRequestId) {
      // Stale response discarded (prevent race condition overwrite)
      return false
    }

    data.value = result
    error.value = null
    loading.value = false
    return true
  }

  /**
   * Commits an error if and only if it matches the latest requestId (ignoring abort errors).
   * 
   * @param {Error|string} err - Error object or message
   * @param {number} requestId - Token returned by start()
   * @returns {boolean} true if committed, false if discarded as stale
   */
  function failure(err, requestId = null) {
    if (requestId !== null && requestId !== currentRequestId) {
      // Stale error discarded
      return false
    }

    // If request was deliberately aborted or canceled, ignore silently
    if (
      err?.name === 'CanceledError' ||
      err?.name === 'AbortError' ||
      err?.code === 'ERR_CANCELED' ||
      err?.message?.includes('canceled') ||
      err?.message?.includes('aborted')
    ) {
      return false
    }

    data.value = null
    error.value = typeof err === 'string' ? err : err?.message || 'An unexpected error occurred.'
    loading.value = false
    return true
  }

  function reset() {
    if (currentAbortController) {
      try { currentAbortController.abort() } catch (_) {}
      currentAbortController = null
    }
    currentRequestId++
    data.value = initialData
    loading.value = false
    error.value = null
  }

  function isLatest(requestId) {
    return requestId === currentRequestId
  }

  return {
    data,
    loading,
    error,
    start,
    success,
    failure,
    reset,
    isLatest,
  }
}
