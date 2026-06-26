import {
  addCotacoesToItemInResearchSession,
  addItemsToResearchSession,
} from '../services/pncpResearch';

export function createCotacaoSaveStats() {
  return { inseridas: 0, duplicadas: 0, semFornecedor: 0, itensNovos: 0 };
}

export function accumulateCotacaoSaveResponse(stats, res) {
  if (!stats || !res) return stats;
  if (res.cotacoes_inseridas != null) {
    stats.inseridas += Number(res.cotacoes_inseridas) || 0;
  }
  if (res.itens_inseridos != null) {
    stats.itensNovos += Number(res.itens_inseridos) || 0;
  }
  stats.duplicadas += Number(res.cotacoes_ignoradas_duplicadas) || 0;
  stats.semFornecedor += Number(res.cotacoes_ignoradas_sem_fornecedor) || 0;
  return stats;
}

/** Garante vínculo com o item da rota quando a linha veio sem item_ref_id. */
export function attachRouteItemId(rows, routeItemId) {
  const rid = Number(routeItemId);
  if (!Number.isFinite(rid) || rid <= 0) return rows;
  return rows.map((row) => {
    const iid = Number(row.item_ref_id ?? row.itemId);
    if (Number.isFinite(iid) && iid > 0) return row;
    return { ...row, item_ref_id: rid };
  });
}

export function partitionCotacoesByItem(rows) {
  const byItem = new Map();
  const orphans = [];
  for (const row of rows) {
    const iid = Number(row.item_ref_id ?? row.itemId);
    if (Number.isFinite(iid) && iid > 0) {
      if (!byItem.has(iid)) byItem.set(iid, []);
      byItem.get(iid).push(row);
    } else {
      orphans.push(row);
    }
  }
  return { byItem, orphans };
}

export function formatCotacaoSaveFeedback(stats, { routeItemId = null, semFornecedorUi = 0 } = {}) {
  const parts = [];
  const rid = Number(routeItemId);
  const singleItem = Number.isFinite(rid) && rid > 0;

  if (stats.itensNovos > 0) {
    parts.push(`${stats.itensNovos} item(ns) adicionados à cotação.`);
  } else if (stats.inseridas > 0) {
    parts.push(
      singleItem
        ? `${stats.inseridas} cotação(ões) adicionadas ao item #${rid}.`
        : `${stats.inseridas} cotação(ões) adicionadas aos itens da cotação.`,
    );
  } else {
    parts.push('Nenhuma cotação nova inserida.');
  }

  if (stats.duplicadas > 0) {
    parts.push(`${stats.duplicadas} duplicada(s) ignorada(s).`);
  }
  if (stats.semFornecedor > 0) {
    parts.push(`${stats.semFornecedor} rejeitada(s) pelo servidor (sem fornecedor válido).`);
  }
  if (semFornecedorUi > 0) {
    parts.push(`${semFornecedorUi} ignorada(s) na seleção (sem CNPJ).`);
  }
  return parts.join(' ');
}

/** Remove seleção só quando houve insert ou todas as linhas foram tratadas (ex.: duplicatas). */
export function shouldClearSavedSelection(stats, attempted) {
  const n = Number(attempted) || 0;
  if (n <= 0) return false;
  if (stats.inseridas > 0 || stats.itensNovos > 0) return true;
  const handled = (stats.inseridas + stats.duplicadas + stats.semFornecedor) >= n;
  return handled && stats.duplicadas > 0;
}

async function saveItemCotacoesBatched(sessionId, itemId, rows, batchSize, stats, onProgress, progressCtx) {
  const iid = Number(itemId);
  for (let i = 0; i < rows.length; i += batchSize) {
    const lote = rows.slice(i, i + batchSize);
    const res = await addCotacoesToItemInResearchSession(sessionId, iid, lote);
    accumulateCotacaoSaveResponse(stats, res);
    if (progressCtx) {
      progressCtx.cotacoesEnviadas += lote.length;
    }
    if (typeof onProgress === 'function') {
      onProgress({
        itemId: iid,
        lote: Math.floor(i / batchSize) + 1,
        cotacoesEnviadas: progressCtx?.cotacoesEnviadas ?? lote.length,
        totalCotacoes: progressCtx?.totalCotacoes ?? rows.length,
        done: progressCtx?.itemsDone ?? 0,
        total: progressCtx?.itemsTotal ?? 1,
      });
    }
  }
}

/**
 * Persiste cotações nos itens corretos (agrupado por item_ref_id).
 * Linhas sem item vão para addItems (novos itens na sessão) — fallback legado.
 */
export async function persistCotacoesToResearchSession(
  sessionId,
  rows,
  {
    routeItemId = null,
    concurrency = 4,
    batchSize = 250,
    onProgress = null,
  } = {},
) {
  const stats = createCotacaoSaveStats();
  const enriched = attachRouteItemId(rows, routeItemId);
  const { byItem, orphans } = partitionCotacoesByItem(enriched);
  const entries = [...byItem.entries()];
  const totalCotacoes = enriched.length;
  const progressCtx = {
    totalCotacoes,
    cotacoesEnviadas: 0,
    itemsTotal: entries.length,
    itemsDone: 0,
  };

  if (entries.length > 0) {
    let nextIdx = 0;
    const workers = Math.min(concurrency, entries.length);

    async function worker() {
      while (nextIdx < entries.length) {
        const idx = nextIdx;
        nextIdx += 1;
        const [iid, arr] = entries[idx];
        await saveItemCotacoesBatched(
          sessionId,
          iid,
          arr,
          batchSize,
          stats,
          onProgress,
          progressCtx,
        );
        progressCtx.itemsDone += 1;
        if (typeof onProgress === 'function') {
          onProgress({
            done: progressCtx.itemsDone,
            total: progressCtx.itemsTotal,
            cotacoesEnviadas: progressCtx.cotacoesEnviadas,
            totalCotacoes: progressCtx.totalCotacoes,
            itemId: iid,
            phase: 'item',
          });
        }
      }
    }

    await Promise.all(Array.from({ length: workers }, () => worker()));
  }

  if (orphans.length > 0) {
    for (let i = 0; i < orphans.length; i += batchSize) {
      const lote = orphans.slice(i, i + batchSize);
      const res = await addItemsToResearchSession(sessionId, lote);
      accumulateCotacaoSaveResponse(stats, res);
    }
  }

  return stats;
}
