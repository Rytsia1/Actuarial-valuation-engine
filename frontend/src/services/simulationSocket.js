/**
 * WebSocket Simulation Client
 * Establishes real-time bidirectional streaming for Monte Carlo progress events and results.
 */

/**
 * Determine WebSocket base URL from environment or current window location.
 */
function getWebSocketUrl(jobId) {
  const envBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');
  
  if (envBase) {
    const wsProto = envBase.startsWith('https') ? 'wss:' : 'ws:';
    const host = envBase.replace(/^https?:\/\//, '');
    return `${wsProto}//${host}/ws/simulations/${jobId}`;
  }

  // Fallback to local default port 8000 when running in Vite dev mode
  const loc = window.location;
  const isHttps = loc.protocol === 'https:';
  const wsProto = isHttps ? 'wss:' : 'ws:';
  
  // If Vite dev server on 5173, backend is on 8000
  const host = loc.hostname || 'localhost';
  const port = loc.port === '5173' ? '8000' : (loc.port ? loc.port : (isHttps ? '443' : '80'));
  
  return `${wsProto}//${host}:${port}/ws/simulations/${jobId}`;
}

/**
 * Connect to WebSocket stream for simulation progress.
 *
 * @param {string} jobId - Unique simulation job identifier
 * @param {Object} callbacks - { onProgress, onComplete, onError }
 * @returns {Object} { close: Function }
 */
export function connectSimulationSocket(jobId, { onProgress, onComplete, onError }) {
  const url = getWebSocketUrl(jobId);
  let socket = null;
  let isClosed = false;

  try {
    socket = new WebSocket(url);

    socket.onopen = () => {
      // Connection established
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);

        if (payload.type === 'PROGRESS') {
          if (onProgress) {
            onProgress({
              percent: payload.percent,
              completed_paths: payload.completed_paths,
              total_paths: payload.total_paths,
              partial_metrics: payload.partial_metrics,
            });
          }
        } else if (payload.type === 'COMPLETE') {
          if (onComplete) {
            onComplete(payload.data);
          }
          if (socket) socket.close();
        } else if (payload.type === 'ERROR') {
          if (onError) {
            onError(new Error(payload.error || 'Simulation failed'));
          }
          if (socket) socket.close();
        }
      } catch (err) {
        if (onError) onError(err);
      }
    };

    socket.onerror = (err) => {
      if (!isClosed && onError) {
        onError(new Error('WebSocket connection error. Falling back to HTTP polling.'));
      }
    };

    socket.onclose = () => {
      isClosed = true;
    };
  } catch (err) {
    if (onError) onError(err);
  }

  return {
    close: () => {
      isClosed = true;
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    },
  };
}
