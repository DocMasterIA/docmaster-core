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

export function isPncpResearchRoute(route) {
  const path = String(route?.path || '');
  return path.startsWith('/pesquisador-pncp');
}

export function getBulkAutostartController() {
  return bulkAutostartController;
}

export function beginBulkAutostartSession(sessionId, { reuseRunning = false } = {}) {
  if (
    reuseRunning
    && bulkAutostartRegistry.isRunning
    && Number(bulkAutostartRegistry.sessionId) === Number(sessionId)
    && bulkAutostartRegistry.bulkRunId != null
    && bulkAutostartController
  ) {
    return {
      bulkRunId: bulkAutostartRegistry.bulkRunId,
      signal: bulkAutostartController.signal,
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
  return { bulkRunId, signal: bulkAutostartController.signal };
}

export function isBulkRunActive(bulkRunId) {
  return Number(bulkRunId) === activeBulkRunId;
}

export function isRegistryAutostartBulk(bulkRunId) {
  return Boolean(bulkAutostartRegistry.isRunning)
    && Number(bulkAutostartRegistry.bulkRunId) === Number(bulkRunId)
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
    return !isRegistryAutostartBulk(myBulkRunId);
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
