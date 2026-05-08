/** Apenas dígitos, no máximo 14 (base numérica do CNPJ). */
export function cnpjDigitsOnly(value) {
  return String(value ?? '').replace(/\D/g, '').slice(0, 14);
}

/** Máscara fixa brasileira: 00.000.000/0001-00 (só números na base). */
export function formatCnpjBr(value) {
  const n = cnpjDigitsOnly(value);
  if (!n.length) return '';
  if (n.length <= 2) return n;
  if (n.length <= 5) return `${n.slice(0, 2)}.${n.slice(2)}`;
  if (n.length <= 8) return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5)}`;
  if (n.length <= 12) return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5, 8)}/${n.slice(8)}`;
  return `${n.slice(0, 2)}.${n.slice(2, 5)}.${n.slice(5, 8)}/${n.slice(8, 12)}-${n.slice(12, 14)}`;
}

const CNPJ_NAV_KEYS = new Set([
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

/**
 * Bloqueia teclas que não sejam dígitos (Ctrl/Cmd/Alt + atalhos continuam liberados).
 * Colar texto com máscara é normalizado no @input com formatCnpjBr.
 */
export function onCnpjInputKeydown(event) {
  if (event.ctrlKey || event.metaKey || event.altKey) return;
  if (CNPJ_NAV_KEYS.has(event.key)) return;
  if (/^[0-9]$/.test(event.key)) return;
  event.preventDefault();
}
