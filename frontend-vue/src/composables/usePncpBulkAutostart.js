/**
 * Busca inteligente em lote (autostart): estado global + pausa ao sair do módulo PNCP
 * para não saturar api.docmasteria.com.br enquanto o utilizador usa Dispensa / outros fluxos.
 */
import { reactive } from 'vue';

export const bulkAutostartRegistry = reactive({
  sessionId: null,
  isRunning: false,
  promise: null,
  bulkRunId: null,
  progress: null,
  rows: null,
  lastFailure: '',
  /** true quando o utilizador navegou para fora do pesquisador PNCP. */
  pausedByNavigation: false,
});

let bulkAutostartController = null;
let activeBulkRunId = 0;
/** Evita dois autostarts em paralelo (Vue Strict Mode / double mount). */
let bulkAutostartSingleFlight = null;

export function isPncpResearchRoute(route) {
  const path = String(route?.path || '');
  return path.startsWith('/pesquisador-pncp');
}

export function getBulkAutostartController() {
  return bulkAutostartController;
}

export function beginBulkAutostartSession(sessionId, { forceNew = false } = {}) {
  const sid = Number(sessionId);
  if (
    !forceNew
    && bulkAutostartRegistry.isRunning
    && Number(bulkAutostartRegistry.sessionId) === sid
    && bulkAutostartRegistry.bulkRunId != null
    && bulkAutostartController
  ) {
    return {
      bulkRunId: bulkAutostartRegistry.bulkRunId,
      signal: bulkAutostartController.signal,
      reused: true,
    };
  }
  activeBulkRunId += 1;
  const bulkRunId = activeBulkRunId;
  try {
    bulkAutostartController?.abort();
  } catch (_) {
    /* ignore */
  }
  bulkAutostartController = new AbortController();
  bulkAutostartRegistry.bulkRunId = bulkRunId;
  bulkAutostartRegistry.pausedByNavigation = false;
  return { bulkRunId, signal: bulkAutostartController.signal, reused: false };
}

/**
 * Garante um único autostart por sessão (remount não cancela o lote em curso).
 */
export async function runBulkAutostartOnce(sessionId, runner) {
  const sid = Number(sessionId);
  if (bulkAutostartSingleFlight && Number(bulkAutostartSingleFlight.sessionId) === sid) {
    return bulkAutostartSingleFlight.promise;
  }
  const promise = Promise.resolve().then(runner);
  bulkAutostartSingleFlight = { sessionId: sid, promise };
  try {
    return await promise;
  } finally {
    if (bulkAutostartSingleFlight?.promise === promise) {
      bulkAutostartSingleFlight = null;
    }
  }
}

export function isBulkRunActive(bulkRunId) {
  return Number(bulkRunId) === activeBulkRunId;
}

export function isRegistryAutostartBulk(bulkRunId) {
  return Number(bulkAutostartRegistry.bulkRunId) === Number(bulkRunId)
    && !bulkAutostartRegistry.pausedByNavigation;
}

export function bulkRunShouldStop({
  mountRunId,
  mountRunSeq,
  myBulkRunId,
  generation,
  searchGeneration,
  autostartBulk = false,
} = {}) {
  if (autostartBulk) {
    if (bulkAutostartRegistry.pausedByNavigation) return true;
    // Autostart: só cancela por abort explícito (navegação / «Pesquisar UF»), nunca por bulkRunId stale.
    try {
      if (bulkAutostartController?.signal?.aborted) return true;
    } catch (_) {
      /* ignore */
    }
    return false;
  }
  if (mountRunId != null && mountRunId !== mountRunSeq) return true;
  if (myBulkRunId != null && !isBulkRunActive(myBulkRunId)) return true;
  if (generation != null && generation !== searchGeneration) return true;
  return false;
}

/** Interrompe o item em curso e marca o lote como pausado (utilizador foi para outro módulo). */
export function pauseBulkAutostartForNavigation() {
  if (!bulkAutostartRegistry.isRunning && !bulkAutostartRegistry.pausedByNavigation) return;
  bulkAutostartRegistry.pausedByNavigation = true;
  bulkAutostartRegistry.isRunning = false;
  try {
    bulkAutostartController?.abort();
  } catch (_) {
    /* ignore */
  }
}

export function clearBulkPausedFlag() {
  bulkAutostartRegistry.pausedByNavigation = false;
}
