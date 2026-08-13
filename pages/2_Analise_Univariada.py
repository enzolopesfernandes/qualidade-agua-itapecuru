"""
Pagina 2 -- Analise Univariada.

Histograma interativo (Plotly, com zoom/pan nativos) por parametro, com
filtros no corpo da pagina. Reusa dashboard_common.figura_histograma_interativo()
e dashboard_common.badge_confiabilidade() para o selo de confiabilidade --
nao recalcula nada, so filtra o CSV ja gerado.

Nota metodologica (repetida do script 01): os outliers marcados (coluna
OUTLIER_<PARAMETRO>) foram calculados com o IQR do parametro inteiro (todas
as amostras validas), NAO recalculados para o subconjunto filtrado aqui --
um recalculo por filtro seria instavel com os N pequenos que varios filtros
produzem. O que os filtros desta pagina mudam e quais pontos aparecem no
grafico e as estatisticas do "recorte atual"; a classificacao de outlier em
si e sempre a global.
"""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.estilo import CORES  # noqa: E402
from config.nomes_unidades import rotulo  # noqa: E402
from dashboard_common import (  # noqa: E402
    ICONE_PAGINA,
    TITULO_TRABALHO,
    badge_confiabilidade,
    bloco_interpretativo,
    carregar_dados,
    carregar_resumo_cobertura,
    categoria_parametro,
    figura_histograma_interativo,
    layout_editorial,
    legenda_grafico,
    render_header,
    secao,
)

PLACEHOLDER = "Selecione uma opção"

st.set_page_config(page_title=TITULO_TRABALHO, page_icon=ICONE_PAGINA, layout="wide")
render_header("Análise Univariada")

st.title("2. Análise Univariada")

df = carregar_dados()
resumo = carregar_resumo_cobertura()

PARAMETROS = resumo.sort_values("N_VALIDO_PARAMETRO", ascending=False)["PARAMETRO"].tolist()

# --------------------------------------------------------------- filtros ----


def _limpar_filtros() -> None:
    for chave in ["filtro_corpo", "filtro_rnqa", "filtro_ano", "filtro_periodo"]:
        st.session_state.pop(chave, None)


st.markdown("**Filtros**")
f1, f2, f3, f4, f5 = st.columns([2, 2, 1, 1, 2])

corpos = sorted(df["CORPODAGUA"].dropna().unique().tolist())
corpo_sel = f1.multiselect("Corpo d'água", corpos, key="filtro_corpo", placeholder=PLACEHOLDER)

rnqas_disponiveis = sorted(
    df[df["CORPODAGUA"].isin(corpo_sel)]["RNQA"].dropna().unique().tolist()
    if corpo_sel
    else df["RNQA"].dropna().unique().tolist()
)
rnqa_sel = f2.multiselect("Ponto RNQA", rnqas_disponiveis, key="filtro_rnqa", placeholder=PLACEHOLDER)

anos = sorted(df["ANO"].dropna().unique().astype(int).tolist())
ano_sel = f3.multiselect("Ano", anos, key="filtro_ano", placeholder=PLACEHOLDER)

periodos = sorted(df["PERIODO"].dropna().unique().astype(int).tolist())
_anos_por_periodo = df.groupby("PERIODO")["ANO"].agg(["min", "max"])


def _rotulo_periodo(p: int) -> str:
    ano_min, ano_max = int(_anos_por_periodo.loc[p, "min"]), int(_anos_por_periodo.loc[p, "max"])
    ano_txt = str(ano_min) if ano_min == ano_max else f"{ano_min}–{ano_max}"
    return f"Período {p} ({ano_txt})"


periodo_sel = f4.multiselect(
    "Rodada de monitoramento", periodos, key="filtro_periodo", placeholder=PLACEHOLDER, format_func=_rotulo_periodo,
    help="Cada rodada (coluna PERIODO) revisita os mesmos pontos RNQA ao longo do tempo — não é uma "
    "unidade de calendário regular (uma rodada pode abranger mais de um ano); ver página 1.",
)

parametro_sel = f5.selectbox(
    "Parâmetro",
    PARAMETROS,
    format_func=rotulo,
    key="filtro_parametro",
    index=PARAMETROS.index("TURBIDEZ") if "TURBIDEZ" in PARAMETROS else 0,
)

st.button("Limpar filtros", on_click=_limpar_filtros)
st.divider()

# ---------------------------------------------------------- aplicar filtro ----

df_filtrado = df[df["VALIDO_PARA_CALCULO"]].copy()
if corpo_sel:
    df_filtrado = df_filtrado[df_filtrado["CORPODAGUA"].isin(corpo_sel)]
if rnqa_sel:
    df_filtrado = df_filtrado[df_filtrado["RNQA"].isin(rnqa_sel)]
if ano_sel:
    df_filtrado = df_filtrado[df_filtrado["ANO"].isin(ano_sel)]
if periodo_sel:
    df_filtrado = df_filtrado[df_filtrado["PERIODO"].isin(periodo_sel)]

n_bacia_inteira = int(df["VALIDO_PARA_CALCULO"].sum())
if len(corpo_sel) == 1:
    st.metric(
        f"N — {corpo_sel[0]}", len(df_filtrado),
        help=f"Amostras válidas neste corpo d'água (considerando também os demais filtros acima), de um "
        f"total de {n_bacia_inteira} na bacia inteira. Corpos d'água com N baixo tornam estatísticas e "
        "gráficos mais instáveis — interprete com cautela.",
    )
elif corpo_sel:
    st.caption(
        f"Corpos d'água selecionados: {', '.join(corpo_sel)} — **N = {len(df_filtrado)}** amostras válidas "
        f"(bacia inteira: N = {n_bacia_inteira})."
    )

rotulo_param = rotulo(parametro_sel)
categoria_sel = categoria_parametro(parametro_sel, resumo)
eh_robusto_moderado = categoria_sel in ("ROBUSTO", "MODERADO")

secao("01", rotulo_param)
col_badge, col_info = st.columns([1, 5])
with col_badge:
    badge_confiabilidade(parametro_sel, resumo)
with col_info:
    n_global = int(resumo.loc[resumo["PARAMETRO"] == parametro_sel, "N_VALIDO_PARAMETRO"].iloc[0])
    st.caption(
        f"Classificação de confiabilidade calculada sobre **todas** as {n_global} amostras válidas do "
        f"parâmetro (independente dos filtros acima) — ver página 1 para os critérios de N."
    )

serie = df_filtrado[parametro_sel].dropna()
n_filtro = len(serie)

if n_filtro == 0:
    bloco_interpretativo("Nenhuma amostra válida para essa combinação de filtros e parâmetro.")
else:
    if n_filtro < 5:
        bloco_interpretativo(
            f"Apenas N={n_filtro} amostra(s) no recorte atual — histograma pouco informativo com uma "
            "amostra tão pequena, mas exibido mesmo assim para referência."
        )

    outlier_mask = df_filtrado.loc[serie.index, f"OUTLIER_{parametro_sel}"] == True  # noqa: E712

    fig = figura_histograma_interativo(serie, rotulo_eixo=rotulo_param, cor=CORES["petroleo"])
    layout_editorial(fig, height=420, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)

    n_outliers_filtro = int(outlier_mask.sum())
    texto_outliers = f" · {n_outliers_filtro} de {n_filtro} amostras identificadas como outlier pelo método IQR"
    if n_filtro > 1:
        texto_legenda = (
            f"n = {n_filtro} · média = {serie.mean():.2f} · mediana = {serie.median():.2f} · "
            f"desvio padrão = {serie.std():.2f} · mín = {serie.min():.2f} · máx = {serie.max():.2f}{texto_outliers}"
        )
    else:
        texto_legenda = f"n = {n_filtro} · média = {serie.mean():.2f} · mín = {serie.min():.2f} · máx = {serie.max():.2f}{texto_outliers}"
    legenda_grafico(texto_legenda)
    st.caption(
        "Outliers calculados pelo método IQR (Q1 − 1,5×IQR / Q3 + 1,5×IQR) sobre **todas** as amostras "
        "válidas do parâmetro — não recalculado para o recorte filtrado (ver nota no topo do arquivo "
        "desta página)."
    )

st.divider()

# ------------------------------------------------- comparacao entre corpos d'agua ----

secao("02", "Comparação entre corpos d'água")

if not eh_robusto_moderado:
    bloco_interpretativo(
        f"Comparação entre corpos d'água disponível apenas para parâmetros de cobertura Robusta ou "
        f"Moderada. {rotulo_param} tem cobertura Pouca — amostra insuficiente para essa comparação."
    )
else:
    dados_comp = df_filtrado[["CORPODAGUA", parametro_sel]].dropna()
    contagem_corpo = dados_comp["CORPODAGUA"].value_counts()
    ordem_corpo = contagem_corpo.index.tolist()
    dados_comp["CORPO_COM_N"] = dados_comp["CORPODAGUA"].map(lambda c: f"{c} (N={contagem_corpo[c]})")
    ordem_com_n = [f"{c} (N={contagem_corpo[c]})" for c in ordem_corpo]

    fig_comp = px.box(
        dados_comp,
        x="CORPO_COM_N",
        y=parametro_sel,
        category_orders={"CORPO_COM_N": ordem_com_n},
        labels={"CORPO_COM_N": "Corpo d'água", parametro_sel: rotulo_param},
        color_discrete_sequence=[CORES["petroleo"]],
    )
    layout_editorial(fig_comp, height=440, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig_comp, use_container_width=True)
    legenda_grafico(
        "Cada caixa é um corpo d'água, com o N do recorte atual indicado no eixo X. RIO ITAPECURU "
        "concentra a maior parte da amostra; caixas com poucas observações são menos confiáveis."
    )
