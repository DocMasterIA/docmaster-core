<template>
  <div class="dm-ia-loader-wrap" :class="{ 'dm-ia-loader-wrap--compact': compact }" role="status" aria-live="polite">
    <svg class="dm-ia-pl" width="240" height="240" viewBox="0 0 240 240" aria-hidden="true">
      <circle
        class="dm-ia-pl-ring dm-ia-pl-ring--a"
        cx="120"
        cy="120"
        r="105"
        fill="none"
        stroke-width="20"
        stroke-dasharray="0 660"
        stroke-dashoffset="-330"
        stroke-linecap="round"
      />
      <circle
        class="dm-ia-pl-ring dm-ia-pl-ring--b"
        cx="120"
        cy="120"
        r="35"
        fill="none"
        stroke-width="20"
        stroke-dasharray="0 220"
        stroke-dashoffset="-110"
        stroke-linecap="round"
      />
      <circle
        class="dm-ia-pl-ring dm-ia-pl-ring--c"
        cx="85"
        cy="120"
        r="70"
        fill="none"
        stroke-width="20"
        stroke-dasharray="0 440"
        stroke-linecap="round"
      />
      <circle
        class="dm-ia-pl-ring dm-ia-pl-ring--d"
        cx="155"
        cy="120"
        r="70"
        fill="none"
        stroke-width="20"
        stroke-dasharray="0 440"
        stroke-linecap="round"
      />
    </svg>
    <p class="dm-ia-loader-text">{{ message }}</p>
  </div>
</template>

<script setup>
defineProps({
  message: {
    type: String,
    default: 'Gerando documento com IA...',
  },
  /** Versão menor (ex.: geração de cláusulas no meio do formulário). */
  compact: {
    type: Boolean,
    default: false,
  },
});
</script>

<style scoped>
.dm-ia-loader-wrap {
  margin-top: 14px;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.dm-ia-loader-wrap--compact {
  margin-top: 10px;
  padding: 8px 10px;
}
.dm-ia-loader-text {
  margin: 0;
  font-size: 12px;
  color: #334155;
  font-weight: 600;
  text-align: center;
}
.dm-ia-pl {
  width: 5.4em;
  height: 5.4em;
}
.dm-ia-loader-wrap--compact .dm-ia-pl {
  width: 3.6em;
  height: 3.6em;
}
.dm-ia-pl-ring {
  animation: dmIaRingA 2s linear infinite;
}
.dm-ia-pl-ring--a {
  stroke: #0d6efd;
}
.dm-ia-pl-ring--b {
  animation-name: dmIaRingB;
  stroke: #2a8cff;
}
.dm-ia-pl-ring--c {
  animation-name: dmIaRingC;
  stroke: #1b74e4;
}
.dm-ia-pl-ring--d {
  animation-name: dmIaRingD;
  stroke: #59a8ff;
}
@keyframes dmIaRingA {
  from,
  4% {
    stroke-dasharray: 0 660;
    stroke-width: 20;
    stroke-dashoffset: -330;
  }
  12% {
    stroke-dasharray: 60 600;
    stroke-width: 30;
    stroke-dashoffset: -335;
  }
  32% {
    stroke-dasharray: 60 600;
    stroke-width: 30;
    stroke-dashoffset: -595;
  }
  40%,
  54% {
    stroke-dasharray: 0 660;
    stroke-width: 20;
    stroke-dashoffset: -660;
  }
  62% {
    stroke-dasharray: 60 600;
    stroke-width: 30;
    stroke-dashoffset: -665;
  }
  82% {
    stroke-dasharray: 60 600;
    stroke-width: 30;
    stroke-dashoffset: -925;
  }
  90%,
  to {
    stroke-dasharray: 0 660;
    stroke-width: 20;
    stroke-dashoffset: -990;
  }
}
@keyframes dmIaRingB {
  from,
  12% {
    stroke-dasharray: 0 220;
    stroke-width: 20;
    stroke-dashoffset: -110;
  }
  20% {
    stroke-dasharray: 20 200;
    stroke-width: 30;
    stroke-dashoffset: -115;
  }
  40% {
    stroke-dasharray: 20 200;
    stroke-width: 30;
    stroke-dashoffset: -195;
  }
  48%,
  62% {
    stroke-dasharray: 0 220;
    stroke-width: 20;
    stroke-dashoffset: -220;
  }
  70% {
    stroke-dasharray: 20 200;
    stroke-width: 30;
    stroke-dashoffset: -225;
  }
  90% {
    stroke-dasharray: 20 200;
    stroke-width: 30;
    stroke-dashoffset: -305;
  }
  98%,
  to {
    stroke-dasharray: 0 220;
    stroke-width: 20;
    stroke-dashoffset: -330;
  }
}
@keyframes dmIaRingC {
  from {
    stroke-dasharray: 0 440;
    stroke-width: 20;
    stroke-dashoffset: 0;
  }
  8% {
    stroke-dasharray: 40 400;
    stroke-width: 30;
    stroke-dashoffset: -5;
  }
  28% {
    stroke-dasharray: 40 400;
    stroke-width: 30;
    stroke-dashoffset: -175;
  }
  36%,
  58% {
    stroke-dasharray: 0 440;
    stroke-width: 20;
    stroke-dashoffset: -220;
  }
  66% {
    stroke-dasharray: 40 400;
    stroke-width: 30;
    stroke-dashoffset: -225;
  }
  86% {
    stroke-dasharray: 40 400;
    stroke-width: 30;
    stroke-dashoffset: -395;
  }
  94%,
  to {
    stroke-dasharray: 0 440;
    stroke-width: 20;
    stroke-dashoffset: -440;
  }
}
@keyframes dmIaRingD {
  from,
  8% {
    stroke-dasharray: 0 440;
    stroke-width: 20;
    stroke-dashoffset: 0;
  }
  16% {
    stroke-dasharray: 40 400;
    stroke-width: 30;
    stroke-dashoffset: -5;
  }
  36% {
    stroke-dasharray: 40 400;
    stroke-width: 30;
    stroke-dashoffset: -175;
  }
  44%,
  50% {
    stroke-dasharray: 0 440;
    stroke-width: 20;
    stroke-dashoffset: -220;
  }
  58% {
    stroke-dasharray: 40 400;
    stroke-width: 30;
    stroke-dashoffset: -225;
  }
  78% {
    stroke-dasharray: 40 400;
    stroke-width: 30;
    stroke-dashoffset: -395;
  }
  86%,
  to {
    stroke-dasharray: 0 440;
    stroke-width: 20;
    stroke-dashoffset: -440;
  }
}
</style>

<style>
/* Tema escuro (classe em ancestrais .dm-dark / .dm-dark-theme) */
.dm-dark .dm-ia-loader-wrap,
.dm-dark-theme .dm-ia-loader-wrap {
  background: #082f49;
  border-color: #0ea5e9;
}
.dm-dark .dm-ia-loader-text,
.dm-dark-theme .dm-ia-loader-text {
  color: #bae6fd;
}
.dm-dark .dm-ia-pl-ring--a,
.dm-dark-theme .dm-ia-pl-ring--a {
  stroke: #38bdf8;
}
.dm-dark .dm-ia-pl-ring--b,
.dm-dark-theme .dm-ia-pl-ring--b {
  stroke: #7dd3fc;
}
.dm-dark .dm-ia-pl-ring--c,
.dm-dark-theme .dm-ia-pl-ring--c {
  stroke: #0ea5e9;
}
.dm-dark .dm-ia-pl-ring--d,
.dm-dark-theme .dm-ia-pl-ring--d {
  stroke: #bae6fd;
}
</style>
