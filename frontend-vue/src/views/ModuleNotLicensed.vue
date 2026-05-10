<template>
  <div class="dm-module-not-licensed" role="status">
    <p class="dm-module-not-licensed__title">Módulo Não Liberado.</p>
    <p class="dm-module-not-licensed__hint">Entrar em contato com o suporte.</p>
  </div>
</template>

<style scoped>
.dm-module-not-licensed {
  max-width: 36rem;
  margin: 2rem auto;
  padding: 1.75rem 1.5rem;
  text-align: center;
  border-radius: 1rem;
  border: 1px solid #e2e8f0;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.06);
}

.dm-module-not-licensed__title {
  margin: 0 0 0.5rem;
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
}

.dm-module-not-licensed__hint {
  margin: 0;
  font-size: 0.9375rem;
  color: #475569;
  line-height: 1.5;
}

:global(.dm-layout-bg.dm-dark) .dm-module-not-licensed {
  border-color: rgba(148, 163, 184, 0.35);
  background: rgba(15, 23, 42, 0.72);
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.25);
}

:global(.dm-layout-bg.dm-dark) .dm-module-not-licensed__title {
  color: #f1f5f9;
}

:global(.dm-layout-bg.dm-dark) .dm-module-not-licensed__hint {
  color: #94a3b8;
}
</style>
