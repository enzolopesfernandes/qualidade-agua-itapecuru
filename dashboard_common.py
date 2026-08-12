"""
Funcoes e constantes compartilhadas entre as paginas do dashboard Streamlit.

Nao duplica logica de calculo: le sempre os CSVs ja gerados pelos scripts/
(01_univariate_outliers.py, 02_correlacao_regressao_pca.py,
03_dispersao_e_reclustering.py) em output/, e reusa config/nomes_unidades.py
para rotulos e config/estilo.py para cores.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from config.estilo import CORES, CORES_STATUS, ROTULOS_CATEGORIA  # noqa: E402
from config.nomes_unidades import NOMES_UNIDADES, rotulo  # noqa: E402,F401

OUTPUT_DIR = BASE_DIR / "output"

# titulo oficial do trabalho -- usado exatamente (aba do navegador + hero da Home).
# A parte apos ":" e destacada em italico onde for exibida por extenso.
TITULO_TRABALHO = (
    "Análise Exploratória e Visualização Interativa de Dados da Qualidade da Água: "
    "um estudo aplicado à Bacia do Rio Itapecuru"
)
_TITULO_PRINCIPAL, _, _TITULO_SUBTITULO = TITULO_TRABALHO.partition(": ")

# icone da aba do navegador -- neutro (sem emoji), conforme redesign editorial
ICONE_PAGINA = "•"

# os 5 parametros priorizados na analise univariada (script 01, PARAMS_PRIORITARIOS)
# -- repetidos aqui como constante simples pois sao usados em mais de uma pagina
PARAMS_ROBUSTOS_PRIORITARIOS = [
    "PH",
    "TURBIDEZ",
    "TEMPERATURA_AGUA",
    "COND_ELETRICA_ESPECIFICA",
    "OXIGENIO_DISSOLVIDO",
]

# ---------------------------------------------------------- estilo global ----

_CSS_EDITORIAL = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500;1,600&display=swap');

h1, h2, h3, h4, h5, h6, .fonte-serifada {
    font-family: 'Lora', Georgia, 'Times New Roman', serif !important;
}

/* menu "..." padrao do Streamlit da acesso a troca de tema (claro/escuro) --
   escondido para manter o dashboard sempre no modo claro definido em
   .streamlit/config.toml, sem alternancia visivel ao usuario */
[data-testid="stToolbar"] { display: none; }

/* barra decorativa padrao do Streamlit (gradiente vermelho/amarelo fixo,
   nao respeita o tema) -- removida por conflitar com "sem gradientes ou
   cores decorativas extras" do redesign editorial */
[data-testid="stDecoration"] { display: none; }

.kicker {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 0.72rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #1f6f78;
    font-weight: 600;
    margin: 0 0 0.3rem 0;
}

.masthead-titulo {
    font-family: 'Lora', Georgia, serif;
    font-size: 1.05rem;
    font-weight: 600;
    color: #2A2A28;
    margin: 0;
}

.secao-titulo { display: flex; align-items: baseline; gap: 0.65rem; margin-top: 0.3rem; }
.secao-numero {
    font-family: 'Lora', Georgia, serif;
    color: #1f6f78;
    font-weight: 600;
    font-size: 1.1rem;
}
.secao-titulo h2, .secao-titulo h3 { margin: 0; }

.big-stat-valor {
    font-family: 'Lora', Georgia, serif;
    font-weight: 700;
    font-size: 2.3rem;
    color: #2A2A28;
    line-height: 1.15;
}
.big-stat-label {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #595652;
    margin-top: 0.15rem;
}

.bloco-interpretativo {
    border-left: 3px solid #1f6f78;
    padding: 0.1rem 0 0.1rem 1rem;
    font-style: italic;
    color: #595652;
    margin: 0.7rem 0;
}
.bloco-interpretativo p { margin: 0.3rem 0; }

.badge-confiabilidade {
    display: inline-block;
    padding: 3px 14px;
    border-radius: 999px;
    color: #ffffff !important;
    font-size: 0.82rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}

.legenda-grafico {
    font-style: italic;
    color: #595652;
    font-size: 0.85rem;
    margin: 0.1rem 0 0.8rem 0;
}
</style>
"""


def render_header(pagina_atual: str) -> None:
    """Cabecalho do dashboard: injeta o CSS editorial (fontes, cores,
    componentes) e o masthead compacto. A navegacao volta a ser o menu
    lateral PADRAO do Streamlit (lista automatica de paginas na sidebar) --
    nao escondemos mais a sidebar nem desenhamos um menu horizontal proprio.
    Chamar logo apos st.set_page_config().
    """
    st.markdown(_CSS_EDITORIAL, unsafe_allow_html=True)
    st.markdown('<p class="masthead-titulo">Qualidade da Água — Bacia do Itapecuru</p>', unsafe_allow_html=True)
    st.divider()


def render_titulo_trabalho(tag: str = "h1") -> None:
    """Titulo oficial do trabalho, por extenso e exato, com a parte apos ':'
    em italico para enfase -- usar na Home (hero principal)."""
    st.markdown(
        f'<{tag} style="margin-bottom:0.3rem;">{_TITULO_PRINCIPAL}: <em>{_TITULO_SUBTITULO}</em></{tag}>',
        unsafe_allow_html=True,
    )


def secao(numero: str, titulo: str, nivel: str = "h3") -> None:
    """Cabecalho de secao no estilo editorial: numero pequeno ('01', '02', ...)
    em verde-petroleo antes do titulo. Seguir com o conteudo da secao e depois
    st.divider() para a linha fina entre secoes."""
    st.markdown(
        f'<div class="secao-titulo"><span class="secao-numero">{numero}</span>'
        f'<{nivel}>{titulo}</{nivel}></div>',
        unsafe_allow_html=True,
    )


def big_stat(valor: str, rotulo_stat: str) -> None:
    """Bloco de estatistica grande: numero serifado grande + rotulo pequeno
    sans-serif em caixa alta embaixo (ex. '340' / 'AMOSTRAS')."""
    st.markdown(
        f'<div class="big-stat-valor">{valor}</div><div class="big-stat-label">{rotulo_stat}</div>',
        unsafe_allow_html=True,
    )


def big_stats_row(itens: list[tuple[str, str]]) -> None:
    """Linha de big_stat()s em colunas iguais. itens = [(valor, rotulo), ...]."""
    colunas = st.columns(len(itens))
    for coluna, (valor, rotulo_stat) in zip(colunas, itens):
        with coluna:
            big_stat(valor, rotulo_stat)


def bloco_interpretativo(texto_md: str) -> None:
    """Bloco de texto interpretativo/nota de limitacao: borda fina a esquerda,
    italico -- estilo blockquote editorial. Aceita **negrito** markdown."""
    st.markdown(f'<div class="bloco-interpretativo">\n\n{texto_md}\n\n</div>', unsafe_allow_html=True)


def legenda_grafico(texto: str) -> None:
    """Legenda curta em italico abaixo de um grafico (n, media, mediana, etc.)."""
    st.markdown(f'<p class="legenda-grafico">{texto}</p>', unsafe_allow_html=True)


def layout_editorial(fig, **kwargs):
    """Aplica o layout minimalista do dashboard (fundo creme, eixos e
    gridlines finas) a uma figura plotly, in-place -- reusar em todo grafico
    plotly do dashboard para manter a mesma linguagem visual. kwargs extras
    sao passados direto para fig.update_layout()."""
    fig.update_layout(
        plot_bgcolor=CORES["fundo"],
        paper_bgcolor=CORES["fundo"],
        font_color=CORES["texto_primario"],
        **kwargs,
    )
    fig.update_xaxes(gridcolor=CORES["grade"], zeroline=False, linecolor=CORES["grade"])
    fig.update_yaxes(gridcolor=CORES["grade"], zeroline=False, linecolor=CORES["grade"])
    return fig


# ---------------------------------------------------------------- dados ----

@st.cache_data
def carregar_dados() -> pd.DataFrame:
    df = pd.read_csv(OUTPUT_DIR / "dados_analise_com_outliers.csv")
    if "DATA_COLETA" in df.columns:
        df["DATA_COLETA"] = pd.to_datetime(df["DATA_COLETA"], errors="coerce")
    return df


@st.cache_data
def carregar_resumo_cobertura() -> pd.DataFrame:
    return pd.read_csv(OUTPUT_DIR / "resumo_cobertura_parametros.csv")


@st.cache_data
def carregar_estatisticas_grupo() -> pd.DataFrame:
    return pd.read_csv(OUTPUT_DIR / "estatisticas_por_grupo.csv")


@st.cache_data
def carregar_correlacao() -> tuple[pd.DataFrame, pd.DataFrame]:
    corr = pd.read_csv(OUTPUT_DIR / "correlacao_pearson.csv", index_col=0)
    n = pd.read_csv(OUTPUT_DIR / "correlacao_pearson_n_amostras.csv", index_col=0)
    return corr, n


@st.cache_data
def carregar_regressao() -> tuple[pd.DataFrame, pd.DataFrame]:
    coef = pd.read_csv(OUTPUT_DIR / "regressao_coeficientes.csv")
    met = pd.read_csv(OUTPUT_DIR / "regressao_metricas.csv")
    return coef, met


@st.cache_data
def carregar_pca(sufixo: str = "") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    scores = pd.read_csv(OUTPUT_DIR / f"pca_scores{sufixo}.csv")
    var = pd.read_csv(OUTPUT_DIR / f"pca_variancia_explicada{sufixo}.csv")
    loadings = pd.read_csv(OUTPUT_DIR / f"pca_loadings{sufixo}.csv", index_col=0)
    perfil = pd.read_csv(OUTPUT_DIR / f"clustering_perfil_clusters{sufixo}.csv")
    return scores, var, loadings, perfil


@st.cache_data
def carregar_silhouette(sufixo: str = "") -> pd.DataFrame:
    return pd.read_csv(OUTPUT_DIR / f"clustering_silhouette{sufixo}.csv")


@st.cache_data
def carregar_grupos_robusto_moderado_baixo() -> tuple[list[str], list[str], list[str]]:
    resumo = carregar_resumo_cobertura()
    robusto = resumo.loc[resumo["COBERTURA"] == "ROBUSTO", "PARAMETRO"].tolist()
    moderado = resumo.loc[resumo["COBERTURA"] == "MODERADO", "PARAMETRO"].tolist()
    baixo = resumo.loc[resumo["COBERTURA"].str.startswith("BAIXO"), "PARAMETRO"].tolist()
    return robusto, moderado, baixo


# --------------------------------------------------------- eixo de periodo ----

def tabela_periodos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Uma linha por PERIODO (registros sem periodo -- 22 amostras de 2017
    anteriores a numeracao existir -- ficam de fora: nenhum grafico temporal
    do dashboard mostra um grupo "sem periodo"), com o ano predominante (ou
    faixa de anos, quando o periodo cai em mais de um ano-calendario) e
    ordenada cronologicamente.

    PERIODO nao e uma unidade de calendario (um mesmo periodo pode cair em
    dois anos-calendario, ex. periodo 6 = 2020-2021), mas e um eixo
    cronologico legitimo: os mesmos pontos RNQA sao revisitados ao longo das
    rodadas (media de ~6 periodos distintos por ponto, so 5 dos 27 pontos
    aparecem em um unico periodo). Por isso todo grafico temporal do
    dashboard usa PERIODO (nao ANO) como eixo categorico ordenado, e usa esta
    tabela para o rotulo do eixo e para a ordem cronologica correta. CAMPANHA
    nao entra em nada aqui -- cada periodo e tratado como uma rodada unica,
    agregando as duas campanhas quando existirem.

    Retorna colunas: PERIODO (int), ROTULO_CURTO ("Período 8 (2022–23)"),
    ordenada cronologicamente.
    """
    base = df[df["PERIODO"].notna()]
    g = base.groupby("PERIODO").agg(ANO_MIN=("ANO", "min"), ANO_MAX=("ANO", "max")).reset_index()
    g["ANO_TXT"] = g.apply(
        lambda r: str(int(r["ANO_MIN"])) if r["ANO_MIN"] == r["ANO_MAX"] else f"{int(r['ANO_MIN'])}–{str(int(r['ANO_MAX']))[-2:]}",
        axis=1,
    )
    g["ROTULO_CURTO"] = "Período " + g["PERIODO"].astype(int).astype(str) + " (" + g["ANO_TXT"] + ")"
    return g.sort_values("PERIODO").reset_index(drop=True)


def agrupar_por_periodo(df: pd.DataFrame, tabela: pd.DataFrame, colunas: list[str], agg: str = "mean") -> pd.DataFrame:
    """Agrega `colunas` de `df` por PERIODO (amostras sem periodo ficam de
    fora, ver tabela_periodos()) e reindexa pela ordem cronologica de
    `tabela`, trocando o indice pelo ROTULO_CURTO pronto. Periodos sem
    nenhuma amostra no recorte atual ficam com NaN (vira lacuna no grafico,
    nao zero)."""
    agregado = df.groupby("PERIODO")[colunas].agg(agg)
    agregado = agregado.reindex(tabela["PERIODO"])
    agregado.index = tabela["ROTULO_CURTO"]
    return agregado


# ----------------------------------------------------- badge de confianca ----

def categoria_parametro(param: str, resumo: pd.DataFrame | None = None) -> str:
    """Categoria completa (ex. 'BAIXO (cautela na interpretacao)') de um parametro."""
    if resumo is None:
        resumo = carregar_resumo_cobertura()
    linha = resumo.loc[resumo["PARAMETRO"] == param]
    if linha.empty:
        return "DESCONHECIDO"
    return linha["COBERTURA"].iloc[0]


def badge_categoria(categoria: str) -> None:
    """Badge solido (fundo colorido + texto branco) para uma categoria
    conhecida (ROBUSTO/MODERADO/BAIXO). O rotulo exibido usa a nomenclatura
    simplificada -- Robusto / Moderado / Pouco -- sem o criterio numerico de N
    dentro do badge (isso fica em legenda/nota de rodape, quando necessario)."""
    chave = "BAIXO" if categoria.startswith("BAIXO") else categoria
    cor = CORES_STATUS.get(chave, CORES["texto_mudo"])
    rotulo_exibido = ROTULOS_CATEGORIA.get(chave, chave)
    st.markdown(
        f'<span class="badge-confiabilidade" style="background:{cor};">{rotulo_exibido}</span>',
        unsafe_allow_html=True,
    )


def badge_confiabilidade(param: str, resumo: pd.DataFrame | None = None) -> None:
    """
    Badge visual de confiabilidade para um parametro (ROBUSTO/MODERADO/BAIXO),
    sempre com a mesma cor por categoria (config/estilo.py). Reutilizar esta
    funcao em qualquer pagina que exiba um parametro especifico, para manter
    o significado da cor consistente em todo o dashboard.
    """
    badge_categoria(categoria_parametro(param, resumo))
