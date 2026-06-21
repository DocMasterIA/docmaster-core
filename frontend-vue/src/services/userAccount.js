const API_BASE = import.meta.env.DEV ? '' : (import.meta.env.VITE_API_URL || 'https://api.docmasteria.com.br');

function flattenErrors(errors) {
  if (!errors || typeof errors !== 'object') return 'Erro ao alterar senha.';
  return Object.values(errors).flat().join(' ');
}

/**
 * Altera a senha do usuário autenticado (sessão cookie).
 * @param {{ currentPassword: string, newPassword: string, confirmPassword: string }} payload
 */
export async function changePassword({ currentPassword, newPassword, confirmPassword }) {
  const res = await fetch(`${API_BASE}/api/me/password/`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword,
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message = flattenErrors(data.errors) || data.error || 'Erro ao alterar senha.';
    throw new Error(message);
  }
  return data;
}
