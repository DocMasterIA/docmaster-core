import { useEffect, useMemo, useState } from 'react';

export default function ExternalSourcePreview({ title, sourcePath }) {
  const [content, setContent] = useState('Carregando arquivo...');
  const [error, setError] = useState('');

  const devFsUrl = useMemo(() => {
    if (!sourcePath) return '';
    return `/@fs${encodeURI(sourcePath)}`;
  }, [sourcePath]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!devFsUrl) {
        setError('Caminho do arquivo não configurado.');
        return;
      }
      try {
        const res = await fetch(devFsUrl, { credentials: 'same-origin' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const text = await res.text();
        if (!cancelled) {
          setContent(text);
          setError('');
        }
      } catch (err) {
        if (!cancelled) {
          setError(`Não foi possível carregar o arquivo (${err?.message || 'erro desconhecido'}).`);
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [devFsUrl]);

  return (
    <main className="min-h-screen bg-slate-100 p-4 md:p-6">
      <div className="mx-auto max-w-6xl space-y-3">
        <h1 className="text-xl font-semibold text-slate-900">{title || 'Preview externo'}</h1>
        <div className="rounded-lg border border-slate-300 bg-white p-3 text-xs text-slate-700">
          {sourcePath || 'Sem caminho'}
        </div>
        <a
          href={devFsUrl}
          target="_blank"
          rel="noreferrer noopener"
          className="inline-flex rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white"
        >
          Abrir bruto
        </a>
        {error ? <p className="text-sm text-red-700">{error}</p> : null}
        <pre className="overflow-auto rounded-xl bg-slate-950 p-4 text-xs leading-relaxed text-slate-100">
          {content}
        </pre>
      </div>
    </main>
  );
}
