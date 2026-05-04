import React from "react";
import logoSistema from "./frontend-vue/src/assets/logo_branca.png";

type MainTabKey =
  | "dispensa"
  | "dispensa_eletronica"
  | "pregao"
  | "pregao_eletronico"
  | "inexigibilidade"
  | "etp"
  | "analisador"
  | "pesquisa"
  | "contratos"
  | "controle_interno"
  | "impugnacao"
  | "recurso"
  | "usuario";

type SubTabKey = "dispensa" | "inexigibilidade" | "etp" | "pesquisa";

type IconName =
  | "bot"
  | "chevronRight"
  | "fileText"
  | "search"
  | "shoppingCart"
  | "shieldCheck"
  | "sparkles"
  | "user"
  | "logOut"
  | "sun"
  | "moon";

type SubTabNode = {
  label: string;
  children?: SubTabNode[];
};

type MainTabConfig = {
  key: MainTabKey;
  label: string;
  icon: IconName;
};

type ItemLinha = {
  item: string;
  quantidade: string;
  descricao: string;
  valorUnitario: string;
  valorTotal: string;
};

type Fornecedor = {
  razao: string;
  cnpj: string;
};

const AZUL_DOCMASTER = "#254E78";
const AZUL_CLARO = "#79B6E3";
const DOURADO = "#E7C55B";

const SUB_TABS: Record<SubTabKey, SubTabNode[]> = {
  dispensa: [
    {
      label: "Dispensa Rápida",
      children: [
        {
          label: "Dispensa - Art. 75, I",
          children: [{ label: "Obras e Serviços de Engenharia" }, { label: "Manutenção de Veículos" }],
        },
        {
          label: "Dispensa - Art. 75, II",
          children: [{ label: "Compras" }, { label: "Serviços" }, { label: "Compras com Serviços Inclusos" }],
        },
      ],
    },
    {
      label: "Dispensa Normal",
      children: [
        {
          label: "Dispensa - Art. 75, I",
          children: [{ label: "Obras e Serviços de Engenharia" }, { label: "Manutenção de Veículos" }],
        },
        {
          label: "Dispensa - Art. 75, II",
          children: [{ label: "Compras" }, { label: "Serviços" }, { label: "Compras com Serviços Inclusos" }],
        },
      ],
    },
  ],
  inexigibilidade: [
    {
      label: "Inexigibilidade Art. 74, I",
      children: [
        { label: "Fornecedor exclusivo geral" },
        { label: "Fornecedor exclusivo para manutenção de veículos" },
      ],
    },
  ],
  etp: [{ label: "ETP" }],
  pesquisa: [{ label: "Central de Preços" }, { label: "Pesquisa Rápida" }],
};

const MAIN_TABS: MainTabConfig[] = [
  { key: "dispensa", label: "Dispensa", icon: "fileText" },
  { key: "dispensa_eletronica", label: "Dispensa Eletrônica", icon: "fileText" },
  { key: "pregao", label: "Pregão", icon: "fileText" },
  { key: "pregao_eletronico", label: "Pregão Eletrônico", icon: "fileText" },
  { key: "inexigibilidade", label: "Inexigibilidade", icon: "fileText" },
  { key: "etp", label: "ETP", icon: "fileText" },
  { key: "analisador", label: "Analisador de Documentos", icon: "search" },
  { key: "pesquisa", label: "Pesquisa de Preços Inteligente", icon: "shoppingCart" },
  { key: "contratos", label: "Contratos", icon: "fileText" },
  { key: "controle_interno", label: "Controle Interno", icon: "fileText" },
  { key: "impugnacao", label: "Impugnação", icon: "fileText" },
  { key: "recurso", label: "Recurso Processo Licitatório", icon: "fileText" },
  { key: "usuario", label: "Área do Usuário", icon: "user" },
];

const DEFAULT_ORGAOS = [
  "Prefeitura Municipal de Itajá",
  "Secretaria Municipal de Administração",
  "Secretaria Municipal de Saúde",
  "Secretaria Municipal de Educação",
  "Câmara Municipal de Itajá",
  "Fundo Municipal de Saúde",
];

const DEFAULT_FORNECEDORES: Fornecedor[] = [
  { razao: "M.A DE OLIVEIRA MINIMERCADO", cnpj: "11.200.658/0001-63" },
  { razao: "EMPRESA MODELO LTDA", cnpj: "00.000.000/0001-00" },
];

const EMPTY_ITEM: ItemLinha = {
  item: "",
  quantidade: "",
  descricao: "",
  valorUnitario: "",
  valorTotal: "",
};

function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

function hasSubTabs(tab: MainTabKey): tab is SubTabKey {
  return tab === "dispensa" || tab === "inexigibilidade" || tab === "etp" || tab === "pesquisa";
}

function formatFornecedor(fornecedor: Fornecedor): string {
  return `${fornecedor.razao} — ${fornecedor.cnpj}`;
}

function runSelfTests() {
  console.assert(new Set(MAIN_TABS.map((tab) => tab.key)).size === MAIN_TABS.length, "As abas principais devem ter chaves únicas.");
  console.assert(SUB_TABS.pesquisa.some((tab) => tab.label === "Pesquisa Rápida"), "A aba Pesquisa deve conter Pesquisa Rápida.");
  console.assert(SUB_TABS.dispensa.some((tab) => tab.label === "Dispensa Rápida"), "A aba Dispensa deve conter Dispensa Rápida.");
  console.assert(SUB_TABS.dispensa.some((tab) => tab.label === "Dispensa Normal"), "A aba Dispensa deve conter Dispensa Normal.");
  console.assert(
    SUB_TABS.dispensa.some((tab) =>
      tab.label === "Dispensa Rápida" && tab.children?.some((child) => child.label === "Dispensa - Art. 75, II" && child.children?.some((item) => item.label === "Compras"))
    ),
    "A aba Dispensa Rápida deve conter as subopções de dispensa."
  );
  console.assert(
    SUB_TABS.dispensa.some((tab) =>
      tab.label === "Dispensa Normal" && tab.children?.some((child) => child.label === "Dispensa - Art. 75, II" && child.children?.some((item) => item.label === "Compras com Serviços Inclusos"))
    ),
    "A aba Dispensa Normal deve conter as subopções de dispensa."
  );
  console.assert(hasSubTabs("dispensa") === true, "Dispensa deve possuir subabas.");
  console.assert(
    SUB_TABS.inexigibilidade.some((tab) =>
      tab.label === "Inexigibilidade Art. 74, I" && tab.children?.some((item) => item.label === "Fornecedor exclusivo geral")
    ),
    "A aba Inexigibilidade deve conter Fornecedor exclusivo geral."
  );
  console.assert(
    SUB_TABS.inexigibilidade.some((tab) =>
      tab.label === "Inexigibilidade Art. 74, I" && tab.children?.some((item) => item.label === "Fornecedor exclusivo para manutenção de veículos")
    ),
    "A aba Inexigibilidade deve conter Fornecedor exclusivo para manutenção de veículos."
  );
  console.assert(hasSubTabs("usuario") === false, "Área do Usuário não deve possuir subabas.");
  console.assert(formatFornecedor(DEFAULT_FORNECEDORES[0]).includes(DEFAULT_FORNECEDORES[0].cnpj), "O formatador de fornecedor deve incluir o CNPJ.");
  console.assert(DEFAULT_ORGAOS.length >= 3, "Deve haver órgãos padrão suficientes para seleção inicial.");
  console.assert(EMPTY_ITEM.item === "" && EMPTY_ITEM.valorTotal === "", "O item vazio deve iniciar com campos em branco.");
  console.assert(AZUL_DOCMASTER === "#254E78", "A cor principal deve ser o azul da imagem de referência.");
  console.assert(AZUL_CLARO === "#79B6E3", "A cor clara de apoio deve estar definida.");
  console.assert(DOURADO === "#E7C55B", "O destaque dourado deve estar definido.");
}

function Icon({ name, className = "h-4 w-4" }: { name: IconName; className?: string }) {
  const common = {
    className,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };

  switch (name) {
    case "chevronRight":
      return (
        <svg {...common}>
          <path d="m9 18 6-6-6-6" />
        </svg>
      );
    case "search":
      return (
        <svg {...common}>
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" />
        </svg>
      );
    case "shoppingCart":
      return (
        <svg {...common}>
          <circle cx="9" cy="21" r="1" />
          <circle cx="20" cy="21" r="1" />
          <path d="M1 1h4l2.5 13.5a2 2 0 0 0 2 1.5h8.8a2 2 0 0 0 1.9-1.4L23 6H6" />
        </svg>
      );
    case "shieldCheck":
      return (
        <svg {...common}>
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <path d="m9 12 2 2 4-4" />
        </svg>
      );
    case "user":
      return (
        <svg {...common}>
          <circle cx="12" cy="8" r="4" />
          <path d="M4 22c0-4 3.5-7 8-7s8 3 8 7" />
        </svg>
      );
    case "logOut":
      return (
        <svg {...common}>
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
          <path d="M16 17l5-5-5-5" />
          <path d="M21 12H9" />
        </svg>
      );
    case "sun":
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2" />
          <path d="M12 20v2" />
          <path d="M2 12h2" />
          <path d="M20 12h2" />
          <path d="m4.93 4.93 1.41 1.41" />
          <path d="m17.66 17.66 1.41 1.41" />
          <path d="m19.07 4.93-1.41 1.41" />
          <path d="m6.34 17.66-1.41 1.41" />
        </svg>
      );
    case "moon":
      return (
        <svg {...common}>
          <path d="M12 3a7.5 7.5 0 1 0 9 9A9 9 0 1 1 12 3Z" />
        </svg>
      );
    case "sparkles":
      return (
        <svg {...common}>
          <path d="M12 3 9.8 8.8 4 11l5.8 2.2L12 19l2.2-5.8L20 11l-5.8-2.2z" />
        </svg>
      );
    case "bot":
      return (
        <svg {...common}>
          <path d="M12 8V4" />
          <rect x="5" y="8" width="14" height="11" rx="3" />
          <path d="M9 13h.01" />
          <path d="M15 13h.01" />
          <path d="M9 17h6" />
        </svg>
      );
    case "fileText":
    default:
      return (
        <svg {...common}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <path d="M14 2v6h6" />
          <path d="M8 13h8" />
          <path d="M8 17h6" />
        </svg>
      );
  }
}

function AiRobotIcon({ size = "large", darkMode }: { size?: "large" | "small"; darkMode: boolean }) {
  const boxClass = size === "large" ? "h-20 w-20 rounded-[24px]" : "h-12 w-12 rounded-2xl";
  const svgClass = size === "large" ? "h-14 w-14" : "h-8 w-8";

  return (
    <div
      className={cx(
        "relative flex items-center justify-center overflow-hidden border shadow-[0_18px_42px_rgba(37,78,120,0.18)] ring-1",
        boxClass,
        darkMode
          ? "border-slate-700 bg-[linear-gradient(135deg,#020617_0%,#0f172a_45%,#254E78_100%)] ring-white/10"
          : "border-white/80 bg-[linear-gradient(135deg,#f8fbff_0%,#dbeafe_38%,#254E78_100%)] ring-white/90"
      )}
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_28%_18%,rgba(255,255,255,0.55),transparent_36%)]" />
      {size === "large" ? <div className="absolute inset-x-4 bottom-3 h-4 rounded-full bg-slate-950/20 blur-md" /> : null}
      <svg className={cx("relative", svgClass)} viewBox="0 0 96 96" fill="none" aria-hidden="true">
        <rect x="22" y="34" width="52" height="38" rx="18" fill="#F8FAFC" />
        <path d="M30 35c4-7 11-10 18-10s14 3 18 10" stroke="#2C5A89" strokeWidth="5" strokeLinecap="round" />
        <rect x="29" y="42" width="38" height="21" rx="10" fill="#071426" />
        <circle cx="40" cy="52" r="4" fill="#7DD3FC" />
        <circle cx="56" cy="52" r="4" fill="#7DD3FC" />
        <path d="M43 61c3 2.5 7 2.5 10 0" stroke="#7DD3FC" strokeWidth="3" strokeLinecap="round" />
        <path d="M48 26V16" stroke="#254E78" strokeWidth="5" strokeLinecap="round" />
        <circle cx="48" cy="12" r="7" fill="#D4AF37" />
        {size === "large" ? (
          <>
            <rect x="14" y="45" width="9" height="18" rx="4.5" fill="#E2E8F0" />
            <rect x="73" y="45" width="9" height="18" rx="4.5" fill="#E2E8F0" />
            <path d="M23 72c6 7 16 10 25 10s19-3 25-10" stroke="#254E78" strokeWidth="5" strokeLinecap="round" />
            <rect x="41" y="72" width="14" height="4" rx="2" fill="#D4AF37" />
          </>
        ) : null}
      </svg>
      {size === "large" ? <span className="absolute right-3 top-3 h-2.5 w-2.5 rounded-full bg-[#D4AF37] shadow-[0_0_0_5px_rgba(212,175,55,0.18)]" /> : null}
    </div>
  );
}

function HorizontalTab({
  label,
  active,
  icon,
  onClick,
  darkMode,
}: {
  label: string;
  active: boolean;
  icon: IconName;
  onClick: () => void;
  darkMode: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cx(
        "group inline-flex items-center gap-2 rounded-xl border px-3 py-1.5 text-[13px] font-semibold transition-all duration-200",
        darkMode
          ? active
            ? "border-slate-500 bg-slate-800 text-white shadow-[0_10px_22px_rgba(2,6,23,0.26)] ring-1 ring-white/5"
            : "border-slate-700/80 bg-slate-900/70 text-slate-200 hover:-translate-y-0.5 hover:border-slate-500 hover:bg-slate-800"
          : active
            ? "border-white/45 bg-white text-[#254E78] shadow-[0_10px_22px_rgba(15,23,42,0.14)] ring-1 ring-white/60"
            : "border-white/14 bg-white/8 text-white/90 hover:-translate-y-0.5 hover:border-white/28 hover:bg-white/15 hover:text-white"
      )}
    >
      <span
        className={cx(
          "flex h-7 w-7 items-center justify-center rounded-lg transition",
          darkMode
            ? active
              ? "bg-slate-700 text-white"
              : "bg-slate-800 text-slate-300 group-hover:bg-slate-700"
            : active
              ? "bg-[#E8EEF5] text-[#254E78]"
              : "bg-white/10 text-white group-hover:bg-white/18"
        )}
      >
        <Icon name={icon} className="h-3.5 w-3.5" />
      </span>
      <span className="whitespace-nowrap">{label}</span>
    </button>
  );
}

function Input({
  label,
  placeholder,
  value,
  onChange,
  darkMode,
}: {
  label: string;
  placeholder: string;
  value?: string;
  onChange?: (value: string) => void;
  darkMode: boolean;
}) {
  return (
    <div>
      <label className={cx("text-xs font-medium", darkMode ? "text-slate-300" : "text-slate-500")}>{label}</label>
      <input
        className={cx(
          "mt-1 w-full rounded-2xl border px-3 py-2.5 text-sm outline-none transition",
          darkMode
            ? "border-slate-700 bg-slate-900 text-slate-100 shadow-[0_8px_18px_rgba(2,6,23,0.35)] focus:border-slate-500 focus:ring-4 focus:ring-slate-500/15"
            : "border-slate-200 bg-white/95 text-slate-700 shadow-[0_8px_18px_rgba(15,23,42,0.05)] focus:border-[#254E78] focus:ring-4 focus:ring-[#254E78]/10"
        )}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
      />
    </div>
  );
}

function SideSubTab({
  node,
  active,
  expandedChildTab,
  activeChild,
  onToggle,
  onChildToggle,
  onFinalSelect,
  darkMode,
}: {
  node: SubTabNode;
  active: boolean;
  expandedChildTab: string;
  activeChild: string;
  onToggle: () => void;
  onChildToggle: (childKey: string) => void;
  onFinalSelect: (childKey: string, finalKey: string) => void;
  darkMode: boolean;
}) {
  const hasChildren = Boolean(node.children?.length);

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={onToggle}
        className={cx(
          "relative flex w-full items-center justify-between overflow-hidden rounded-2xl border px-4 py-3 text-left text-sm transition-all duration-200",
          darkMode
            ? active
              ? "border-slate-600 bg-slate-800 text-slate-100 shadow-[0_12px_26px_rgba(2,6,23,0.24)]"
              : "border-slate-700 bg-slate-900/80 text-slate-200 hover:-translate-y-0.5 hover:border-slate-500 hover:bg-slate-800"
            : active
              ? "border-slate-300 bg-slate-50 text-[#254E78] shadow-[0_12px_26px_rgba(15,23,42,0.08)]"
              : "border-slate-200 bg-white text-slate-700 hover:-translate-y-0.5 hover:border-slate-300 hover:bg-slate-50"
        )}
      >
        <span className={cx("absolute inset-y-2 left-2 w-1 rounded-full", active ? "bg-[#254E78]" : "bg-transparent")} />
        <span className="pl-2 font-semibold">{node.label}</span>
        <Icon
          name="chevronRight"
          className={cx(
            "h-4 w-4 transition",
            active && hasChildren ? "rotate-90" : "rotate-0",
            darkMode ? "text-slate-400" : "text-slate-400"
          )}
        />
      </button>

      {active && hasChildren ? (
        <div className={cx("ml-4 space-y-2 border-l pl-4", darkMode ? "border-slate-700" : "border-slate-200")}>
          {node.children?.map((child) => {
            const childKey = `${node.label}__${child.label}`;
            const childExpanded = expandedChildTab === childKey;
            const childHasChildren = Boolean(child.children?.length);

            return (
              <div key={childKey} className="space-y-2">
                <button
                  type="button"
                  onClick={() => {
                    if (childHasChildren) {
                      onChildToggle(childKey);
                    } else {
                      onFinalSelect(childKey, childKey);
                    }
                  }}
                  className={cx(
                    "flex w-full items-center justify-between rounded-xl border px-3 py-2.5 text-left text-sm transition",
                    darkMode
                      ? childExpanded
                        ? "border-slate-600 bg-slate-800 text-white shadow-[0_10px_22px_rgba(2,6,23,0.22)]"
                        : "border-slate-700 bg-slate-900 text-slate-200 hover:border-slate-500 hover:bg-slate-800"
                      : childExpanded
                        ? "border-[#254E78] bg-[#254E78] text-white shadow-[0_10px_22px_rgba(37,78,120,0.22)]"
                        : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50 hover:text-[#254E78]"
                  )}
                >
                  <span>{child.label}</span>
                  <Icon
                    name="chevronRight"
                    className={cx("h-4 w-4 transition", childExpanded && childHasChildren ? "rotate-90" : "rotate-0")}
                  />
                </button>

                {childExpanded && childHasChildren ? (
                  <div className={cx("ml-3 space-y-1.5 border-l pl-3", darkMode ? "border-slate-700" : "border-slate-200")}>
                    {child.children?.map((grandChild) => {
                      const finalKey = `${childKey}__${grandChild.label}`;
                      const isActive = activeChild === finalKey;

                      return (
                        <button
                          key={finalKey}
                          type="button"
                          onClick={() => onFinalSelect(childKey, finalKey)}
                          className={cx(
                            "w-full rounded-lg border px-3 py-2 text-left text-sm transition",
                            darkMode
                              ? isActive
                                ? "border-slate-500 bg-slate-700 text-white"
                                : "border-slate-700 bg-slate-900/80 text-slate-200 hover:bg-slate-800"
                              : isActive
                                ? "border-[#254E78] bg-[#254E78] text-white"
                                : "border-slate-200 bg-white/90 text-slate-700 hover:bg-slate-50 hover:text-[#254E78]"
                          )}
                        >
                          {grandChild.label}
                        </button>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

runSelfTests();

export default function GeradorDocumentos() {
  const [mainTab, setMainTab] = React.useState<MainTabKey>("dispensa");
  const [expandedSubTab, setExpandedSubTab] = React.useState("");
  const [expandedChildTab, setExpandedChildTab] = React.useState("");
  const [activeChild, setActiveChild] = React.useState("");
  const [hasActiveSelection, setHasActiveSelection] = React.useState(false);
  const [usarProcesso, setUsarProcesso] = React.useState(false);
  const [orgaoSelecionado, setOrgaoSelecionado] = React.useState("");
  const [fornecedorSelecionado, setFornecedorSelecionado] = React.useState<Fornecedor | null>(null);
  const [itens, setItens] = React.useState<ItemLinha[]>([{ ...EMPTY_ITEM }]);
  const [darkMode, setDarkMode] = React.useState(false);

  const subTabs = hasSubTabs(mainTab) ? SUB_TABS[mainTab] : [];
  const activeMainTab = MAIN_TABS.find((tab) => tab.key === mainTab);
  const ocultarFormularioCompleto = mainTab === "dispensa" || mainTab === "inexigibilidade" || mainTab === "pesquisa";

  const trocarAba = (next: MainTabKey) => {
    setMainTab(next);
    setExpandedSubTab("");
    setExpandedChildTab("");
    setActiveChild("");
    setHasActiveSelection(false);
  };

  const selecionarSubAba = (label: string, hasChildren: boolean) => {
    if (expandedSubTab === label) {
      setExpandedSubTab("");
      setActiveChild("");
      setHasActiveSelection(false);
      return;
    }

    setExpandedSubTab(label);
    setExpandedChildTab("");
    if (!hasChildren) {
      setHasActiveSelection(true);
      setActiveChild(label);
      return;
    }

    setHasActiveSelection(false);
    setActiveChild("");
  };

  const alternarGrupoFilho = (childKey: string) => {
    setExpandedChildTab((current) => (current === childKey ? "" : childKey));
    setActiveChild("");
    setHasActiveSelection(false);
  };

  const selecionarOpcaoFinal = (childKey: string, finalKey: string) => {
    setExpandedChildTab(childKey);
    setActiveChild(finalKey);
    setHasActiveSelection(true);
  };

  const updateItem = (index: number, field: keyof ItemLinha, value: string) => {
    setItens((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, [field]: value } : item)));
  };

  const addItem = () => {
    setItens((current) => [...current, { ...EMPTY_ITEM }]);
  };

  const removeItem = (index: number) => {
    setItens((current) => {
      const next = current.filter((_, itemIndex) => itemIndex !== index);
      return next.length > 0 ? next : [{ ...EMPTY_ITEM }];
    });
  };

  const pageBg = darkMode
    ? "min-h-screen bg-[linear-gradient(180deg,#020617_0%,#0f172a_52%,#111827_100%)]"
    : "min-h-screen bg-[linear-gradient(180deg,#f8fafc_0%,#f1f5f9_50%,#eef2f6_100%)]";

  const panelClass = darkMode
    ? "rounded-[24px] border border-slate-800 bg-slate-950/80 shadow-[0_16px_42px_rgba(2,6,23,0.34)] backdrop-blur-xl ring-1 ring-white/5"
    : "rounded-[24px] border border-slate-200/80 bg-white/96 shadow-[0_14px_36px_rgba(15,23,42,0.045)] backdrop-blur-xl ring-1 ring-white/90";

  const cardClass = darkMode
    ? "rounded-[24px] border border-slate-800 bg-slate-900/74 shadow-[0_16px_36px_rgba(2,6,23,0.30)] ring-1 ring-white/5"
    : "rounded-[24px] border border-slate-200 bg-white/96 shadow-[0_14px_36px_rgba(15,23,42,0.045)] ring-1 ring-white/80";

  const smallCardClass = darkMode
    ? "rounded-[20px] border border-slate-800 bg-slate-900/72 shadow-[0_12px_26px_rgba(2,6,23,0.24)] ring-1 ring-white/5"
    : "rounded-[20px] border border-slate-200 bg-white/94 shadow-[0_12px_26px_rgba(15,23,42,0.04)] ring-1 ring-white/80";

  const renderPlaceholder = () => (
    <section className={panelClass}>
      <div className="px-6 py-16 text-center">
        <h2 className={cx("mt-5 text-lg font-semibold", darkMode ? "text-slate-50" : "text-slate-900")}>
          {hasActiveSelection && ocultarFormularioCompleto ? "Formulário oculto nesta aba" : "Selecione uma subaba para continuar"}
        </h2>
        <p className={cx("mx-auto mt-2 max-w-xl text-sm leading-6", darkMode ? "text-slate-300" : "text-slate-500")}>
          {hasActiveSelection && ocultarFormularioCompleto
            ? "As abas Dispensa, Inexigibilidade e Pesquisa de Preços exibem uma experiência simplificada nesta etapa."
            : "O assistente de criação será exibido após a seleção de uma opção na navegação lateral."}
        </p>
      </div>
    </section>
  );

  const renderFormulario = () => (
    <section className={panelClass}>
      <div className={cx("border-b px-6 py-5", darkMode ? "border-slate-700 bg-slate-900/70" : "border-slate-200 bg-[#F7F9FB]")}> 
        <div className="flex items-start gap-3">
          <AiRobotIcon size="small" darkMode={darkMode} />
          <div>
            <h2 className={cx("text-[18px] font-semibold", darkMode ? "text-slate-50" : "text-slate-900")}>Assistente de Criação</h2>
            <p className={cx("mt-1 text-sm", darkMode ? "text-slate-300" : "text-slate-500")}>Preencha os campos para gerar o documento com padrão profissional.</p>
          </div>
        </div>
      </div>

      <div className="space-y-6 p-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className={cx("md:col-span-2 flex items-center gap-2 rounded-[20px] border px-4 py-3.5", darkMode ? "border-slate-800 bg-slate-900/70" : "border-slate-200 bg-slate-50/90")}> 
            <input type="checkbox" id="usarProcesso" checked={usarProcesso} onChange={(e) => setUsarProcesso(e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-[#254E78]" />
            <label htmlFor="usarProcesso" className={cx("text-sm font-medium", darkMode ? "text-slate-100" : "text-slate-700")}>Informar número do processo</label>
          </div>

          {usarProcesso ? <Input label="Processo" placeholder="Ex: 123/2026" darkMode={darkMode} /> : null}

          <div className={cx("md:col-span-2 p-4", cardClass)}>
            <label className={cx("text-xs font-medium", darkMode ? "text-slate-300" : "text-slate-500")}>Órgão/Unidade responsável</label>
            <div className="mt-3 flex flex-wrap gap-2">
              {DEFAULT_ORGAOS.map((orgao) => {
                const ativo = orgaoSelecionado === orgao;
                return (
                  <button
                    key={orgao}
                    type="button"
                    onClick={() => setOrgaoSelecionado(orgao)}
                    className={cx(
                      "rounded-full border px-3.5 py-2 text-sm font-medium transition",
                      darkMode
                        ? ativo
                          ? "border-slate-600 bg-slate-800 text-slate-100 shadow-sm"
                          : "border-slate-700 bg-slate-900 text-slate-200 hover:border-slate-500 hover:bg-slate-800"
                        : ativo
                          ? "border-slate-300 bg-slate-50 text-[#254E78] shadow-sm ring-1 ring-slate-200"
                          : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50 hover:text-[#254E78]"
                    )}
                  >
                    {orgao}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <div className={cx("space-y-3 p-4", cardClass)}>
          <h3 className={cx("text-sm font-semibold", darkMode ? "text-slate-100" : "text-slate-700")}>Fornecedor</h3>
          <div className="flex flex-wrap gap-2">
            {DEFAULT_FORNECEDORES.map((fornecedor) => {
              const ativo = fornecedorSelecionado?.cnpj === fornecedor.cnpj;
              return (
                <button
                  key={fornecedor.cnpj}
                  type="button"
                  onClick={() => setFornecedorSelecionado(fornecedor)}
                  className={cx(
                    "rounded-2xl border px-3.5 py-2.5 text-sm transition",
                    darkMode
                      ? ativo
                        ? "border-slate-600 bg-slate-800 text-slate-100 shadow-sm"
                        : "border-slate-700 bg-slate-900 text-slate-200 hover:border-slate-500 hover:bg-slate-800"
                      : ativo
                        ? "border-slate-300 bg-slate-50 text-[#254E78] shadow-sm ring-1 ring-slate-200"
                        : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50 hover:text-[#254E78]"
                  )}
                >
                  {formatFornecedor(fornecedor)}
                </button>
              );
            })}
          </div>
        </div>

        <div className={cx("space-y-4 p-4", cardClass)}>
          <div className="flex items-center justify-between gap-3">
            <h3 className={cx("text-sm font-semibold", darkMode ? "text-slate-100" : "text-slate-700")}>Itens e Valores</h3>
            <button type="button" onClick={addItem} className={cx("inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition", darkMode ? "border-slate-700 bg-slate-900 text-slate-100 hover:-translate-y-0.5 hover:border-slate-500 hover:bg-slate-800" : "border-slate-200 bg-white text-[#254E78] hover:-translate-y-0.5 hover:bg-slate-50 hover:shadow-[0_10px_20px_rgba(15,23,42,0.06)]")}>Adicionar</button>
          </div>

          {itens.map((item, index) => (
            <div key={index} className={cx("rounded-3xl border p-3.5", darkMode ? "border-slate-700 bg-slate-900/80" : "border-slate-200 bg-white")}> 
              <div className="mb-3 flex items-center justify-between">
                <span className={cx("text-xs font-semibold uppercase tracking-[0.12em]", darkMode ? "text-slate-400" : "text-slate-500")}>Item {index + 1}</span>
                {itens.length > 1 ? (
                  <button type="button" onClick={() => removeItem(index)} className="rounded-lg px-2 py-1 text-xs font-medium text-red-500 transition hover:bg-red-500/10">Remover</button>
                ) : null}
              </div>

              <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
                <Input label="Item" placeholder="Ex: 1" value={item.item} onChange={(value) => updateItem(index, "item", value)} darkMode={darkMode} />
                <Input label="Quantidade" placeholder="Ex: 1" value={item.quantidade} onChange={(value) => updateItem(index, "quantidade", value)} darkMode={darkMode} />
                <Input label="Descrição" placeholder="Descreva o item" value={item.descricao} onChange={(value) => updateItem(index, "descricao", value)} darkMode={darkMode} />
                <Input label="Valor Unitário" placeholder="R$" value={item.valorUnitario} onChange={(value) => updateItem(index, "valorUnitario", value)} darkMode={darkMode} />
                <Input label="Valor Total" placeholder="R$" value={item.valorTotal} onChange={(value) => updateItem(index, "valorTotal", value)} darkMode={darkMode} />
              </div>
            </div>
          ))}
        </div>

        <button className="inline-flex items-center gap-2 rounded-full bg-[#254E78] px-5 py-3 text-sm font-semibold text-white shadow-[0_16px_34px_rgba(37,78,120,0.24)] ring-1 ring-white/10 transition hover:-translate-y-0.5 hover:bg-[#1F4468] hover:shadow-[0_20px_42px_rgba(37,78,120,0.30)]">
          <Icon name="sparkles" className="h-4 w-4" />
          Gerar Documento com IA
        </button>
      </div>
    </section>
  );

  return (
    <div className={cx(pageBg, "h-screen overflow-hidden")}>
      <div className="mx-auto h-full w-full max-w-[1600px] px-4 py-3 md:px-6">
        <div className={cx("flex h-full min-h-0 flex-col overflow-hidden rounded-none border shadow-[0_30px_90px_rgba(15,23,42,0.10)] ring-1", darkMode ? "border-slate-800 bg-slate-950/70 ring-white/5" : "border-slate-200/80 bg-white/70 ring-white/80")}> 
        <header className={cx("shrink-0 overflow-hidden border-b backdrop-blur-xl", darkMode ? "border-slate-800 bg-slate-950 shadow-none" : "border-[#254E78]/70 bg-[#254E78] shadow-none")}>  
          <div className={cx("relative overflow-hidden border-b px-6 py-3.5", darkMode ? "border-slate-800 bg-slate-950 text-slate-100" : "border-[#254E78] bg-[#254E78] text-white")}> 
            <div className={cx("pointer-events-none absolute -right-16 -top-20 h-40 w-40 rounded-full blur-3xl", darkMode ? "bg-slate-700/20" : "bg-white/10")} />
            <div className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-white/25 to-transparent" />

            <div className="relative flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex min-w-0 items-center gap-3.5">
                <div
                  className={cx(
                    "flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border shadow-[0_18px_36px_rgba(15,23,42,0.18)] ring-1 p-1",
                    darkMode ? "border-slate-700 bg-slate-800 ring-slate-700" : "border-white/15 bg-white/12 ring-white/10"
                  )}
                >
                  <img src={logoSistema} alt="DocMasterIA" className="h-full w-full object-contain" />
                </div>

                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <h1 className="text-[18px] font-extrabold tracking-[0.04em] text-white">DocMaster IA</h1>
                    <span className={cx("inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em]", darkMode ? "border-slate-700 bg-slate-800 text-slate-200" : "border-white/15 bg-white/12 text-white/90")}>Gestão Documental</span>
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">

                <button type="button" onClick={() => setDarkMode((value) => !value)} className={cx("inline-flex items-center justify-center gap-2 rounded-full border px-4 py-2 text-xs font-bold shadow-[0_12px_24px_rgba(15,23,42,0.10)] backdrop-blur-sm transition hover:-translate-y-0.5", darkMode ? "border-slate-700 bg-slate-800 text-slate-100 hover:border-slate-500 hover:bg-slate-700" : "border-white/15 bg-white/10 text-white hover:border-white/25 hover:bg-white/18")}>
                  <Icon name={darkMode ? "sun" : "moon"} className="h-3.5 w-3.5" />
                  {darkMode ? "Claro" : "Escuro"}
                </button>

                <button className={cx("inline-flex items-center justify-center gap-2 rounded-full border px-4 py-2 text-xs font-bold shadow-[0_12px_24px_rgba(15,23,42,0.10)] backdrop-blur-sm transition hover:-translate-y-0.5", darkMode ? "border-slate-700 bg-slate-800 text-slate-100 hover:border-slate-500 hover:bg-slate-700" : "border-white/15 bg-white/10 text-white hover:border-white/25 hover:bg-white/18")}>
                  <Icon name="logOut" className="h-3.5 w-3.5" />
                  Sair
                </button>
              </div>
            </div>
          </div>

          <div className={cx("px-5 py-3 backdrop-blur-sm", darkMode ? "bg-slate-950" : "bg-[#254E78]")}> 
            <div className="flex flex-wrap items-center gap-2">
              {MAIN_TABS.map((tab) => (
                <HorizontalTab key={tab.key} icon={tab.icon} label={tab.label} active={mainTab === tab.key} onClick={() => trocarAba(tab.key)} darkMode={darkMode} />
              ))}
            </div>
          </div>
        </header>

        <div className={cx("grid min-h-0 flex-1 grid-cols-1 gap-0 border-t xl:grid-cols-[284px_minmax(0,1fr)]", darkMode ? "border-slate-800" : "border-slate-200/70")}>  
          <aside className={cx("h-full overflow-hidden border-r", darkMode ? "border-slate-800 bg-slate-950/72" : "border-[#BCCBDA] bg-[#DCE5EE]")}>    
            <div className={cx("border-b px-5 py-4", darkMode ? "border-slate-800 bg-slate-950/40" : "border-[#BCCBDA] bg-[#D2DEE9]")}>   
              <div className={cx("text-[11px] font-semibold uppercase tracking-[0.14em]", darkMode ? "text-slate-400" : "text-[#2C5A89]")}>Navegação da seção</div>
              <div className={cx("mt-1 text-[15px] font-semibold", darkMode ? "text-slate-50" : "text-[#254E78]")}>{activeMainTab?.label ?? "Módulo"}</div>
              <p className={cx("mt-1 text-xs leading-5", darkMode ? "text-slate-300" : "text-slate-600")}>Selecione uma opção para avançar no fluxo de geração.</p>
            </div>

            <div className="p-4">
              {subTabs.length > 0 ? (
                <div className="space-y-2.5">
                  {subTabs.map((item) => (
                    <SideSubTab
                        key={item.label}
                        node={item}
                        active={expandedSubTab === item.label}
                        expandedChildTab={expandedChildTab}
                        activeChild={activeChild}
                        onToggle={() => selecionarSubAba(item.label, Boolean(item.children?.length))}
                        onChildToggle={alternarGrupoFilho}
                        onFinalSelect={selecionarOpcaoFinal}
                        darkMode={darkMode}
                      />
                  ))}
                </div>
              ) : (
                <div className={cx("rounded-2xl border border-dashed px-3 py-4 text-sm", darkMode ? "border-slate-700 bg-slate-900 text-slate-300" : "border-slate-200 bg-[#F5F8FB] text-slate-500")}>Nenhuma subopção disponível para esta aba.</div>
              )}
            </div>
          </aside>

          <div key={`${mainTab}-${expandedSubTab}-${activeChild}`} className={cx("h-full overflow-y-auto p-4 transition-all duration-300 ease-out", darkMode ? "bg-slate-950/35" : "bg-slate-50/45")}> 
            {hasActiveSelection ? (ocultarFormularioCompleto ? renderPlaceholder() : renderFormulario()) : renderPlaceholder()}
          </div>
        </div>
        </div>
      </div>
    </div>
  );
}
