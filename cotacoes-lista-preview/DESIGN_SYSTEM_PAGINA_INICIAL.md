# Design System — Pagina Inicial DocMaster

Baseado em `pagina_inicial_docmaster_final (2) (1).jsx` para manter consistencia visual nas proximas paginas.

## 1) Paleta oficial

- Primaria: `#254E78` (AZUL_DOCMASTER)
- Secundaria: `#79B6E3` (AZUL_CLARO)
- Destaque: `#E7C55B` (DOURADO)
- Hover primaria: `#1F4468`

Neutros usados (Tailwind):
- Claro: `slate-50/100/200/300/500/700/900`
- Escuro: `slate-700/800/900/950`

## 2) Estrutura de layout (nao quebrar)

- Root: `h-screen overflow-hidden`
- Shell: `flex h-full min-h-0 flex-col overflow-hidden`
- Header/navbar: `shrink-0`
- Corpo: `grid min-h-0 flex-1 xl:grid-cols-[284px_minmax(0,1fr)]`
- Sidebar: fixa na esquerda (`h-full overflow-hidden`)
- Conteudo principal: unico scroll da pagina (`h-full overflow-y-auto`)

## 3) Tokens de superficie

- Painel principal:
  - Light: `rounded-[24px] border border-slate-200/80 bg-white/96 ring-1 ring-white/90 shadow-[0_14px_36px_rgba(15,23,42,0.045)]`
  - Dark: `rounded-[24px] border border-slate-800 bg-slate-950/80 ring-1 ring-white/5 shadow-[0_16px_42px_rgba(2,6,23,0.34)]`

- Card secundario:
  - Light: `rounded-[24px] border border-slate-200 bg-white/96 ring-1 ring-white/80 shadow-[0_14px_36px_rgba(15,23,42,0.045)]`
  - Dark: `rounded-[24px] border border-slate-800 bg-slate-900/74 ring-1 ring-white/5 shadow-[0_16px_36px_rgba(2,6,23,0.30)]`

## 4) Padrao de botoes

### 4.1 CTA principal (acao primaria)

```txt
inline-flex items-center gap-2 rounded-full bg-[#254E78] px-5 py-3 text-sm font-semibold text-white
ring-1 ring-white/10 transition hover:-translate-y-0.5 hover:bg-[#1F4468]
shadow-[0_16px_34px_rgba(37,78,120,0.24)] hover:shadow-[0_20px_42px_rgba(37,78,120,0.30)]
```

### 4.2 Secundario no header (claro/escuro)

- Base:
`inline-flex items-center justify-center gap-2 rounded-full border px-4 py-2 text-xs font-bold transition hover:-translate-y-0.5`

- Light:
`border-white/15 bg-white/10 text-white hover:border-white/25 hover:bg-white/18`

- Dark:
`border-slate-700 bg-slate-800 text-slate-100 hover:border-slate-500 hover:bg-slate-700`

### 4.3 Botao de selecao em chips/listas

- Light ativo:
`border-slate-300 bg-slate-50 text-[#254E78] ring-1 ring-slate-200`
- Light inativo:
`border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50 hover:text-[#254E78]`
- Dark ativo:
`border-slate-600 bg-slate-800 text-slate-100`
- Dark inativo:
`border-slate-700 bg-slate-900 text-slate-200 hover:border-slate-500 hover:bg-slate-800`

## 5) Navegacao

- Top tabs (`HorizontalTab`):
  - Radius: `rounded-xl`
  - Altura icone: `h-7 w-7` com fundo proprio
  - Tamanho texto: `text-[13px] font-semibold`

- Sidebar (`SideSubTab`):
  - Bloco pai: `rounded-2xl`
  - Bloco filho: `rounded-xl`
  - Item final: `rounded-lg`
  - Indicador ativo lateral: barra de `w-1` com `bg-[#254E78]`

## 6) Inputs e formularios

- Campo padrao:
  - Radius `rounded-2xl`
  - Padding `px-3 py-2.5`
  - Label `text-xs font-medium`
  - Focus light: `focus:border-[#254E78] focus:ring-[#254E78]/10`
  - Focus dark: `focus:border-slate-500 focus:ring-slate-500/15`

## 7) Tipografia

- Titulos principais: `text-[18px]` a `text-lg`, `font-semibold`/`font-extrabold`
- Labels e meta: `text-xs` ou `text-[10px..13px]`
- Tracking alto para labels em caixa alta: `tracking-[0.12em]` a `tracking-[0.14em]`

## 8) Regras de consistencia para novas paginas

- Sempre usar os mesmos 3 niveis de acao: primaria, secundaria, ghost/chip.
- Manter `rounded` predominante alto (`20px`, `24px`, `full`) para identidade visual.
- Nao criar novas cores sem mapear para primaria/secundaria/destaque.
- Scroll somente no conteudo central quando a tela tiver navbar + sidebar.
- Preservar contraste e variantes light/dark em todos os componentes reutilizados.

## 9) Checklist rapido de replica

- [ ] Header com fundo azul DocMaster e logo oficial.
- [ ] Tabs horizontais no mesmo padrao do `HorizontalTab`.
- [ ] Sidebar fixa com `Navegacao da secao`.
- [ ] Conteudo em cards com `rounded-[24px]`.
- [ ] CTA principal com azul DocMaster.
- [ ] Inputs `rounded-2xl` com foco azul.
- [ ] Tema dark com classes equivalentes.

