/** Apenas dígitos, no máximo 11 (DDD + celular). */
export function telefoneDigitsOnly(value) {
  return String(value ?? '').replace(/\D/g, '').slice(0, 11);
}

function isCelularBr(n) {
  return n.length === 11 || (n.length >= 3 && n[2] === '9');
}

/** Máscara brasileira: (00) 00000-0000 (celular) ou (00) 0000-0000 (fixo). */
export function formatTelefoneBr(value) {
  const n = telefoneDigitsOnly(value);
  if (!n.length) return '';
  if (n.length <= 2) return `(${n}`;
  if (n.length <= 6) return `(${n.slice(0, 2)}) ${n.slice(2)}`;
  if (isCelularBr(n)) {
    if (n.length <= 7) return `(${n.slice(0, 2)}) ${n.slice(2)}`;
    return `(${n.slice(0, 2)}) ${n.slice(2, 7)}-${n.slice(7)}`;
  }
  return `(${n.slice(0, 2)}) ${n.slice(2, 6)}-${n.slice(6)}`;
}

const TELEFONE_NAV_KEYS = new Set([
  'Backspace',
  'Delete',
  'Tab',
  'Escape',
  'Enter',
  'ArrowLeft',
  'ArrowRight',
  'ArrowUp',
  'ArrowDown',
  'Home',
  'End',
]);

/** Bloqueia teclas que não sejam dígitos (Ctrl/Cmd/Alt + atalhos continuam liberados). */
export function onTelefoneInputKeydown(event) {
  if (event.ctrlKey || event.metaKey || event.altKey) return;
  if (TELEFONE_NAV_KEYS.has(event.key)) return;
  if (/^[0-9]$/.test(event.key)) return;
  event.preventDefault();
}
