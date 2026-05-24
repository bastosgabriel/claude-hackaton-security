export type RegionLevel = "critico" | "alto" | "medio" | "baixo"

export type RegionCriterion = {
  label: string
  icon: string
  val: string
  pct: number
  color: string
}

export type RegionActionIcon = "amb" | "pol" | "int"

export type RegionAction = {
  ico: RegionActionIcon
  icon: string
  title: string
  desc: string
  cost: string
}

export type Region = {
  id: string
  name: string
  aisp: string
  score: number
  level: RegionLevel
  roubos: number
  denuncias: number
  ambiente: number
  intel: "Alta" | "Média" | "Baixa"
  criteria: RegionCriterion[]
  narrative: string
  actions: RegionAction[]
}

export const REGIONS: Region[] = [
  {
    id: "lapa",
    name: "Lapa – Centro",
    aisp: "AISP 5",
    score: 92,
    level: "critico",
    roubos: 42,
    denuncias: 18,
    ambiente: 78,
    intel: "Alta",
    criteria: [
      { label: "Roubos a transeunte (7d)", icon: "🚨", val: "42", pct: 88, color: "#dc2626" },
      { label: "Disque Denúncia (qualitativo)", icon: "📞", val: "18", pct: 74, color: "#ea580c" },
      { label: "Fatores ambientais negativos", icon: "💡", val: "7/20", pct: 65, color: "#ca8a04" },
      { label: "RELINTs ativos", icon: "📄", val: "3", pct: 80, color: "#dc2626" },
      { label: "Histórico 4 semanas", icon: "📈", val: "+22%", pct: 71, color: "#ea580c" },
    ],
    narrative:
      "<strong>Convergência crítica:</strong> aumento de 22% em roubos a transeunte coincide com 3 RELINTs apontando facção atuando em pontos com iluminação deficiente nos arcos. Fluxo de pedestres em fim de semana amplifica risco.",
    actions: [
      { ico: "pol", icon: "👮", title: "Patrulhamento a pé reforçado", desc: "+24 agentes · turnos noturnos sex/sáb", cost: "24 agentes" },
      { ico: "amb", icon: "💡", title: "Reparo emergencial de iluminação", desc: "R. do Lavradio + Arcos · prazo 48h", cost: "COMLURB" },
      { ico: "amb", icon: "🌳", title: "Poda de vegetação obstrutiva", desc: "4 pontos identificados · visibilidade", cost: "CLLG" },
      { ico: "int", icon: "🎯", title: "Operação integrada PM + GM", desc: "foco em receptação · base R. Riachuelo", cost: "2 viaturas" },
    ],
  },
  {
    id: "copa",
    name: "Copacabana – Posto 4",
    aisp: "AISP 19",
    score: 87,
    level: "critico",
    roubos: 38,
    denuncias: 14,
    ambiente: 62,
    intel: "Alta",
    criteria: [
      { label: "Roubos a transeunte (7d)", icon: "🚨", val: "38", pct: 82, color: "#dc2626" },
      { label: "Disque Denúncia (qualitativo)", icon: "📞", val: "14", pct: 64, color: "#ea580c" },
      { label: "Fatores ambientais negativos", icon: "💡", val: "5/20", pct: 48, color: "#ca8a04" },
      { label: "RELINTs ativos", icon: "📄", val: "2", pct: 65, color: "#ea580c" },
      { label: "Histórico 4 semanas", icon: "📈", val: "+15%", pct: 62, color: "#ea580c" },
    ],
    narrative:
      "<strong>Padrão de oportunidade:</strong> roubos concentrados na orla entre 18h–22h. Disque denúncia indica grupo recorrente operando em bicicleta. Sem RELINT formalizado, mas confirmado por 3 fontes.",
    actions: [
      { ico: "pol", icon: "🚴", title: "Patrulhamento ciclístico", desc: "18 agentes · trecho R. Constante Ramos a R. Bolívar", cost: "18 agentes" },
      { ico: "int", icon: "📹", title: "Câmera móvel + leitura de placas", desc: "2 pontos da orla · integração CICC", cost: "CICC" },
      { ico: "amb", icon: "💡", title: "Manutenção luminárias quiosques", desc: "7 quiosques sem iluminação adequada", cost: "COMLURB" },
    ],
  },
  {
    id: "madureira",
    name: "Madureira – Centro",
    aisp: "AISP 9",
    score: 81,
    level: "alto",
    roubos: 31,
    denuncias: 22,
    ambiente: 71,
    intel: "Média",
    criteria: [
      { label: "Roubos a transeunte (7d)", icon: "🚨", val: "31", pct: 68, color: "#ea580c" },
      { label: "Disque Denúncia (qualitativo)", icon: "📞", val: "22", pct: 88, color: "#dc2626" },
      { label: "Fatores ambientais negativos", icon: "💡", val: "8/20", pct: 72, color: "#ea580c" },
      { label: "RELINTs ativos", icon: "📄", val: "1", pct: 50, color: "#ca8a04" },
      { label: "Histórico 4 semanas", icon: "📈", val: "+8%", pct: 48, color: "#ca8a04" },
    ],
    narrative:
      "<strong>Sinal forte de moradores:</strong> 22 denúncias no Disque concentradas em 4 quadras próximas ao mercado. Aglomeração comercial cria pontos de fuga e receptação informal.",
    actions: [
      { ico: "pol", icon: "👮", title: "Patrulhamento misto a pé + moto", desc: "20 agentes · horário comercial", cost: "20 agentes" },
      { ico: "amb", icon: "🧹", title: "Remoção de obstrução visual", desc: "containers e carrinhos abandonados", cost: "COMLURB" },
      { ico: "int", icon: "🎯", title: "Foco em receptação", desc: "fiscalização integrada SEFAZ", cost: "1 equipe" },
    ],
  },
  {
    id: "tijuca",
    name: "Tijuca – Saens Peña",
    aisp: "AISP 6",
    score: 74,
    level: "alto",
    roubos: 24,
    denuncias: 11,
    ambiente: 58,
    intel: "Média",
    criteria: [
      { label: "Roubos a transeunte (7d)", icon: "🚨", val: "24", pct: 58, color: "#ea580c" },
      { label: "Disque Denúncia (qualitativo)", icon: "📞", val: "11", pct: 52, color: "#ca8a04" },
      { label: "Fatores ambientais negativos", icon: "💡", val: "6/20", pct: 55, color: "#ca8a04" },
      { label: "RELINTs ativos", icon: "📄", val: "1", pct: 50, color: "#ca8a04" },
      { label: "Histórico 4 semanas", icon: "📈", val: "+11%", pct: 55, color: "#ca8a04" },
    ],
    narrative:
      "<strong>Risco emergente:</strong> deslocamento de padrão da Praça Saens Peña em direção à R. Conde de Bonfim. Necessário reposicionar efetivo antes de consolidar.",
    actions: [
      { ico: "pol", icon: "🏍️", title: "Patrulhamento motorizado", desc: "12 agentes · eixo Conde de Bonfim", cost: "12 agentes" },
      { ico: "amb", icon: "💡", title: "Iluminação na Praça Saens Peña", desc: "4 luminárias com falha", cost: "COMLURB" },
    ],
  },
  {
    id: "botafogo",
    name: "Botafogo – Praia",
    aisp: "AISP 2",
    score: 68,
    level: "medio",
    roubos: 18,
    denuncias: 9,
    ambiente: 42,
    intel: "Baixa",
    criteria: [
      { label: "Roubos a transeunte (7d)", icon: "🚨", val: "18", pct: 42, color: "#ca8a04" },
      { label: "Disque Denúncia (qualitativo)", icon: "📞", val: "9", pct: 38, color: "#ca8a04" },
      { label: "Fatores ambientais negativos", icon: "💡", val: "3/20", pct: 28, color: "#16a34a" },
      { label: "RELINTs ativos", icon: "📄", val: "0", pct: 10, color: "#16a34a" },
      { label: "Histórico 4 semanas", icon: "📈", val: "+4%", pct: 30, color: "#16a34a" },
    ],
    narrative:
      "<strong>Padrão estável:</strong> risco moderado em horário de fluxo intenso (saída do trabalho). Sem RELINT ativo. Manutenção preventiva suficiente.",
    actions: [{ ico: "pol", icon: "👮", title: "Patrulhamento preventivo", desc: "10 agentes · 17h–20h", cost: "10 agentes" }],
  },
  {
    id: "meier",
    name: "Méier – Engenho Novo",
    aisp: "AISP 3",
    score: 62,
    level: "medio",
    roubos: 16,
    denuncias: 13,
    ambiente: 54,
    intel: "Baixa",
    criteria: [
      { label: "Roubos a transeunte (7d)", icon: "🚨", val: "16", pct: 38, color: "#ca8a04" },
      { label: "Disque Denúncia (qualitativo)", icon: "📞", val: "13", pct: 58, color: "#ea580c" },
      { label: "Fatores ambientais negativos", icon: "💡", val: "5/20", pct: 48, color: "#ca8a04" },
      { label: "RELINTs ativos", icon: "📄", val: "0", pct: 10, color: "#16a34a" },
      { label: "Histórico 4 semanas", icon: "📈", val: "+6%", pct: 35, color: "#ca8a04" },
    ],
    narrative:
      "<strong>Atenção qualitativa:</strong> mais denúncias do que ocorrências formais sugere subnotificação. Reforço de inteligência local recomendado antes de operação ostensiva.",
    actions: [
      { ico: "int", icon: "🎯", title: "Coleta de inteligência local", desc: "P2 + Disque Denúncia · 1 semana", cost: "1 equipe" },
      { ico: "amb", icon: "🌳", title: "Poda de vegetação", desc: "R. 24 de Maio · 6 pontos", cost: "CLLG" },
    ],
  },
  {
    id: "barra",
    name: "Barra – Av. das Américas",
    aisp: "AISP 31",
    score: 58,
    level: "medio",
    roubos: 14,
    denuncias: 6,
    ambiente: 38,
    intel: "Baixa",
    criteria: [
      { label: "Roubos a transeunte (7d)", icon: "🚨", val: "14", pct: 34, color: "#ca8a04" },
      { label: "Disque Denúncia (qualitativo)", icon: "📞", val: "6", pct: 28, color: "#16a34a" },
      { label: "Fatores ambientais negativos", icon: "💡", val: "3/20", pct: 28, color: "#16a34a" },
      { label: "RELINTs ativos", icon: "📄", val: "0", pct: 10, color: "#16a34a" },
      { label: "Histórico 4 semanas", icon: "📈", val: "+2%", pct: 22, color: "#16a34a" },
    ],
    narrative:
      "<strong>Vigilância recomendada:</strong> pontos isolados em paradas de BRT mostram crescimento lento mas consistente. Foco em prevenção situacional.",
    actions: [{ ico: "pol", icon: "👮", title: "Postos fixos em estações BRT", desc: "8 agentes · 6 estações", cost: "8 agentes" }],
  },
  {
    id: "bangu",
    name: "Bangu – Centro",
    aisp: "AISP 14",
    score: 54,
    level: "medio",
    roubos: 12,
    denuncias: 8,
    ambiente: 41,
    intel: "Baixa",
    criteria: [
      { label: "Roubos a transeunte (7d)", icon: "🚨", val: "12", pct: 30, color: "#16a34a" },
      { label: "Disque Denúncia (qualitativo)", icon: "📞", val: "8", pct: 36, color: "#ca8a04" },
      { label: "Fatores ambientais negativos", icon: "💡", val: "4/20", pct: 38, color: "#ca8a04" },
      { label: "RELINTs ativos", icon: "📄", val: "0", pct: 10, color: "#16a34a" },
      { label: "Histórico 4 semanas", icon: "📈", val: "−3%", pct: 18, color: "#16a34a" },
    ],
    narrative:
      "<strong>Tendência de queda:</strong> redução leve em ocorrências, mas denúncias mantêm patamar. Acompanhar próximas duas semanas.",
    actions: [{ ico: "pol", icon: "👮", title: "Patrulhamento padrão", desc: "8 agentes · rotina", cost: "8 agentes" }],
  },
]

export const LEVEL_COLOR: Record<RegionLevel, string> = {
  critico: "#dc2626",
  alto: "#ea580c",
  medio: "#ca8a04",
  baixo: "#16a34a",
}

export const LEVEL_LABEL: Record<RegionLevel, string> = {
  critico: "Crítico",
  alto: "Alto",
  medio: "Médio",
  baixo: "Baixo",
}

export function agentsFor(region: Region): number {
  return region.actions.reduce((sum, a) => {
    const match = a.cost.match(/(\d+)\s+agentes/)
    return sum + (match ? parseInt(match[1], 10) : 0)
  }, 0)
}
