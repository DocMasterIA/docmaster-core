/**
 * Login helpers — credenciais via env (PLAYWRIGHT_USER / PLAYWRIGHT_PASSWORD).
 */
export function requireCreds() {
  const user = String(process.env.PLAYWRIGHT_USER || '').trim();
  const password = String(process.env.PLAYWRIGHT_PASSWORD || '').trim();
  if (!user || !password) {
    throw new Error(
      'Defina PLAYWRIGHT_USER e PLAYWRIGHT_PASSWORD (ex.: copie .env.e2e.example → .env.e2e).',
    );
  }
  return { user, password };
}

export function cotacaoIdFromEnv(fallback = '138') {
  return String(process.env.PLAYWRIGHT_COTACAO_ID || fallback).trim();
}

/**
 * Garante sessão autenticada. Usa ?redirect= para voltar à rota alvo após login.
 */
export async function loginIfNeeded(page, { redirectTo } = {}) {
  const { user, password } = requireCreds();
  const redirect = redirectTo && String(redirectTo).startsWith('/')
    ? redirectTo
    : '/';
  const loginUrl = `/login?redirect=${encodeURIComponent(redirect)}`;

  await page.goto(loginUrl, { waitUntil: 'networkidle' });

  // Já autenticado: app redireciona para fora de /login
  if (!page.url().includes('/login')) {
    return;
  }

  const email = page.locator('#email_or_username');
  await expectVisible(email, 20_000);

  await email.fill(user);
  await page.locator('#password').fill(password);
  await page.getByRole('button', { name: /Entrar na plataforma/i }).click();

  // Sucesso: sai de /login (redirect ou home)
  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 45_000 });

  // Se ainda há banner de erro de login, falha explícita
  const loginErr = page.locator('.login-page__error');
  if (await loginErr.isVisible().catch(() => false)) {
    throw new Error(`Login falhou: ${await loginErr.innerText()}`);
  }
}

async function expectVisible(locator, timeout) {
  await locator.waitFor({ state: 'visible', timeout });
}
