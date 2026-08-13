"""
Logica compartilhada pelas paginas da Galeria de Graficos
(pages/5a_Galeria_Bacia_Toda.py, 5b_Galeria_Rio_Itapecuru.py,
5c_Galeria_Demais_Corpos_Dagua.py).

Cada corpo d'agua tem sua PROPRIA pagina Streamlit (nao abas/expanders numa
unica pagina) de proposito: trocar de pagina no Streamlit descarta o
conteudo das demais, entao abrir "Rio Itapecuru" nao recalcula nada de
"Bacia toda" nem dos demais corpos -- ao contrario de abas/expanders, que
ficam todos no mesmo script e sao recalculados juntos a cada interacao.

"Bacia toda" reusa as figuras PNG estaticas ja geradas pelos scripts de
analise (scripts/01, 02 e 03) em output/figuras/ -- reproduzi-las ao vivo
exigiria recalcular PCA/regressao a cada carregamento da pagina. Os demais
corpos d'agua nao tem PNG pre-gerado, entao os graficos (histogramas,
correlacao, dispersao par-a-par, regressao, PCA) sao calculados ao vivo,
sempre atras de @st.cache_data (a cache e valida entre paginas, ja que todas
rodam no mesmo processo Streamlit -- ver render_secao_corpo_dagua()).

PCA/clustering por corpo d'agua so e exibido quando o N permite com
seguranca (mesmos limiares da pagina 3 -- ver _regressao_disponivel()/
_pca_disponivel()); quando insuficiente, a secao mostra isso explicitamente
("Multivariada limitada — N insuficiente") em vez de omitir silenciosamente.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "scripts"))

from config.estilo import CORES, CORES_CLUSTER, DIVERGENTE_CORRELACAO  # noqa: E402
from config.nomes_unidades import rotulo  # noqa: E402
from dashboard_common import (  # noqa: E402
    OUTPUT_DIR,
    carregar_dados,
    carregar_grupos_robusto_moderado_baixo,
    figura_histograma_interativo,
    layout_editorial,
    legenda_grafico,
    limites_iqr_expandido,
)
from _lib_analise import ajustar_ols, calcular_pca_clustering_live  # noqa: E402

FIG_DIR = OUTPUT_DIR / "figuras"

LIMIAR_LINEAR = 0.7
LIMIAR_MONOTONICA = 0.5
GANHO_MONOTONICA = 0.15
DESVIO_MINIMO = 1e-9
REGRESSAO_MIN_RATIO = 5  # mesma referencia da pagina 3 (N >= 5x preditores/variaveis)

TITULOS_ESPECIAIS = {
    "correlacao_heatmap.png": ("Matriz de correlação (todos os parâmetros)", "Correlação (matriz)"),
    "pca_biplot.png": ("PCA biplot — PC1 × PC2 (com outlier)", "PCA / Clustering"),
    "pca_biplot_sem_outlier.png": ("PCA biplot — PC1 × PC2 (sem outlier ITA-0220)", "PCA / Clustering"),
    "pca_variancia_explicada.png": ("PCA — variância explicada por componente (com outlier)", "PCA / Clustering"),
    "pca_variancia_explicada_sem_outlier.png": ("PCA — variância explicada por componente (sem outlier)", "PCA / Clustering"),
    "clustering_silhouette.png": ("Clustering — silhouette por k (com outlier)", "PCA / Clustering"),
    "clustering_silhouette_sem_outlier.png": ("Clustering — silhouette por k (sem outlier)", "PCA / Clustering"),
    "regressao_TURBIDEZ_completo.png": ("Regressão — Turbidez (modelo completo)", "Regressão"),
    "regressao_TURBIDEZ_nucleo_robusto.png": ("Regressão — Turbidez (núcleo robusto)", "Regressão"),
    "regressao_VAZAO_nucleo_robusto.png": ("Regressão — Vazão (núcleo robusto)", "Regressão"),
}

RELACOES_ESPERADAS = [
    (
        "COND_ELETRICA_ESPECIFICA", "SOLIDOS_DISSOLVIDOS", "positivo",
        "Relação aproximadamente linear bem documentada — a condutividade elétrica reflete diretamente "
        "a concentração de íons dissolvidos na água.",
    ),
    (
        "COND_ELETRICA_ESPECIFICA", "SALINIDADE", "positivo",
        "Relação quase definicional — nestes dados, a salinidade é derivada matematicamente da "
        "condutividade (ver dicionário de dados do projeto, página 1).",
    ),
    (
        "OXIGENIO_DISSOLVIDO", "TEMPERATURA_AGUA", "negativo",
        "Relação inversa esperada pela físico-química clássica: gases se dissolvem menos em água mais "
        "quente.",
    ),
    (
        "TURBIDEZ", "SOLIDOS_SUSPENSOS", "positivo",
        "Relação positiva esperada — turbidez e sólidos suspensos medem, por vias diferentes, material "
        "particulado na água.",
    ),
]


@st.cache_data
def montar_itens_estaticos() -> list[dict]:
    """Histogramas (todos os ~23 parametros), PCA/clustering, regressao e a
    matriz de correlacao -- imagens ja geradas por scripts/01 e scripts/02
    (sempre "Bacia toda", os unicos PNGs pre-gerados)."""
    itens = []

    for caminho in sorted(FIG_DIR.glob("*.png")):
        nome = caminho.name
        if nome in TITULOS_ESPECIAIS:
            titulo, categoria = TITULOS_ESPECIAIS[nome]
        else:
            # ex. "00_TURBIDEZ.png" / "01_ALCALINIDADE.png" -> histograma+boxplot do parametro
            param = nome.split("_", 1)[1].rsplit(".", 1)[0]
            titulo = f"{rotulo(param)} (histograma + boxplot)"
            categoria = "Univariada"
        itens.append({"tipo": "estatico", "caminho": str(caminho), "titulo": titulo, "categoria": categoria})

    for caminho in sorted((FIG_DIR / "dispersao").glob("tendencia_*.png")):
        stem = caminho.stem
        param = stem.removeprefix("tendencia_").removesuffix("_por_ano")
        titulo, categoria = f"{rotulo(param)} ao longo do tempo", "Temporal"
        itens.append({"tipo": "estatico", "caminho": str(caminho), "titulo": titulo, "categoria": categoria})

    return itens


def _classificar(x, y) -> tuple[str, str, float, float]:
    """Retorna (tipo, categoria_filtro, r_pearson, r_spearman). r's vem NaN
    quando uma das variaveis e praticamente constante (tipo 'Constante...')."""
    if x.std() < DESVIO_MINIMO or y.std() < DESVIO_MINIMO:
        return "Constante/quase sem variância", "Sem Relação", float("nan"), float("nan")
    r_p = float(x.corr(y, method="pearson"))
    r_s = float(x.corr(y, method="spearman"))
    if abs(r_p) > LIMIAR_LINEAR:
        return "Linear forte", "Correlação Linear", r_p, r_s
    if abs(r_s) > LIMIAR_MONOTONICA and (abs(r_s) - abs(r_p)) > GANHO_MONOTONICA:
        return "Monotônica não-linear", "Correlação Não-linear", r_p, r_s
    return "Fraca/sem relação clara", "Sem Relação", r_p, r_s


def _subset_por_corpo(df_valido: pd.DataFrame, corpo: str | None) -> pd.DataFrame:
    """corpo=None (ou "Bacia toda") -> sem filtro; senao, so as amostras
    daquele corpo d'agua."""
    if not corpo or corpo == "Bacia toda":
        return df_valido
    return df_valido[df_valido["CORPODAGUA"] == corpo]


def _legenda_par(item: dict) -> str:
    if item["tipo"] == "Constante/quase sem variância":
        return f"{item['tipo']} (N={item['n']}) — não classificado como relação."
    return f"{item['tipo']} — Pearson r={item['r_pearson']:.2f}, Spearman ρ={item['r_spearman']:.2f} (N={item['n']})"


def _pca_disponivel_galeria(df_secao: pd.DataFrame, robusto: list[str]) -> bool:
    return df_secao[robusto].dropna().shape[0] > len(robusto)


def _regressao_disponivel_galeria(df_secao: pd.DataFrame, robusto: list[str]) -> tuple[bool, str | None]:
    for alvo in ["TURBIDEZ", "VAZAO"]:
        if alvo not in df_secao.columns:
            continue
        preditores = [p for p in robusto if p not in ("SALINIDADE", alvo)]
        n_disp = df_secao[[alvo] + preditores].dropna().shape[0]
        if preditores and n_disp >= REGRESSAO_MIN_RATIO * len(preditores):
            return True, alvo
    return False, None


# --------------------------------------------------- funcoes que geram figura (cacheadas) ----

@st.cache_data
def montar_pares_correlacao(corpo: str | None = None) -> list[dict]:
    """Todas as combinacoes de pares entre parametros ROBUSTO/MODERADO
    (cobertura Pouca fica de fora -- amostra insuficiente para classificar
    relacao com confianca), com Pearson, Spearman e classificacao do tipo de
    relacao aparente. `corpo`: None/"Bacia toda" = todas as amostras da bacia;
    senao, restrito aquele corpo d'agua."""
    df = carregar_dados()
    df_valido = _subset_por_corpo(df[df["VALIDO_PARA_CALCULO"]], corpo)
    robusto, moderado, _ = carregar_grupos_robusto_moderado_baixo()
    principal = sorted(robusto + moderado)

    pares = []
    for a, b in itertools.combinations(principal, 2):
        sub = df_valido[[a, b]].dropna()
        n = len(sub)
        if n < 3:
            continue
        tipo, categoria, r_p, r_s = _classificar(sub[a], sub[b])
        pares.append({"a": a, "b": b, "n": n, "r_pearson": r_p, "r_spearman": r_s, "tipo": tipo, "categoria": categoria})
    return pares


@st.cache_data
def figura_par_plotly(a: str, b: str, mostrar_tudo: bool = False, corpo: str | None = None) -> tuple[go.Figure, int]:
    """Scatter a-vs-b (Plotly) no estilo editorial, com zoom/pan nativos.
    Retorna (fig, n_pontos_fora_da_vista) -- quando mostrar_tudo=False, o
    eixo inicial e recortado ao intervalo interquartil expandido (mesmo
    criterio de outlier do projeto) e n_pontos_fora_da_vista conta quantos
    pontos ficam fora desse recorte inicial. `corpo`: None/"Bacia toda" =
    todas as amostras; senao, restrito aquele corpo d'agua."""
    df = carregar_dados()
    df_valido = _subset_por_corpo(df[df["VALIDO_PARA_CALCULO"]], corpo)
    sub = df_valido[[a, b]].dropna()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=sub[a], y=sub[b], mode="markers",
            marker=dict(color=CORES["petroleo"], size=6, opacity=0.55),
            showlegend=False,
        )
    )

    if sub[a].std() > DESVIO_MINIMO and sub[b].std() > DESVIO_MINIMO and len(sub) >= 2:
        coef = np.polyfit(sub[a], sub[b], 1)
        xs = np.linspace(sub[a].min(), sub[a].max(), 50)
        fig.add_trace(
            go.Scatter(
                x=xs, y=np.polyval(coef, xs), mode="lines",
                line=dict(color=CORES["linha_tendencia"], width=1.6),
                showlegend=False,
            )
        )

    n_fora = 0
    if not mostrar_tudo and len(sub) >= 4:
        x_ini, x_fim = limites_iqr_expandido(sub[a])
        y_ini, y_fim = limites_iqr_expandido(sub[b])
        fora = sub[(sub[a] < x_ini) | (sub[a] > x_fim) | (sub[b] < y_ini) | (sub[b] > y_fim)]
        n_fora = len(fora)
        if n_fora:
            fig.update_xaxes(range=[x_ini, x_fim])
            fig.update_yaxes(range=[y_ini, y_fim])

    fig.update_layout(xaxis_title=rotulo(a), yaxis_title=rotulo(b))
    return fig, n_fora


@st.cache_data
def figura_histograma_corpo(corpo: str, param: str) -> tuple[go.Figure, int] | None:
    """Histograma ao vivo (Plotly) de um parametro, restrito a um corpo
    d'agua especifico -- usado pelas paginas que nao tem PNG pre-gerado
    ("Bacia toda" usa os PNGs estaticos, ver montar_itens_estaticos())."""
    df = carregar_dados()
    df_valido = _subset_por_corpo(df[df["VALIDO_PARA_CALCULO"]], corpo)
    serie = df_valido[param].dropna()
    if serie.empty:
        return None
    fig = figura_histograma_interativo(serie, rotulo_eixo=rotulo(param), cor=CORES["petroleo"])
    layout_editorial(fig, title=f"{rotulo(param)} (histograma)", height=280, margin=dict(l=10, r=10, t=40, b=10), title_font_size=12, showlegend=False)
    return fig, len(serie)


@st.cache_data
def figura_correlacao_heatmap(corpo: str) -> tuple[go.Figure, int]:
    """Heatmap de correlacao de Pearson (Plotly) para um corpo d'agua (ou
    "Bacia toda"). Retorna (fig, N amostras usadas na secao)."""
    df = carregar_dados()
    df_valido = _subset_por_corpo(df[df["VALIDO_PARA_CALCULO"]], corpo)
    robusto, moderado, baixo = carregar_grupos_robusto_moderado_baixo()
    todos = sorted(robusto + moderado) + sorted(baixo)

    corr_secao = df_valido[todos].corr(method="pearson")
    labels_secao = [f"{rotulo(p)}{'*' if p in baixo else ''}" for p in todos]
    fig = go.Figure(
        data=go.Heatmap(
            z=corr_secao.values,
            x=list(range(len(todos))), y=list(range(len(todos))),
            zmin=-1, zmax=1, colorscale=DIVERGENTE_CORRELACAO,
            text=[[("" if pd.isna(v) else f"{v:.2f}") for v in row] for row in corr_secao.values],
            texttemplate="%{text}", textfont={"size": 7}, colorbar=dict(title="r"),
        )
    )
    fig.update_xaxes(tickmode="array", tickvals=list(range(len(todos))), ticktext=labels_secao, tickangle=-60)
    fig.update_yaxes(tickmode="array", tickvals=list(range(len(todos))), ticktext=labels_secao, autorange="reversed")
    layout_editorial(fig, height=560, margin=dict(l=10, r=10, t=20, b=10))
    return fig, len(df_valido)


@st.cache_data
def figura_regressao_corpo(corpo: str) -> tuple[go.Figure, dict] | None:
    """Grafico de barras dos coeficientes padronizados (Plotly) da regressao
    ao vivo (TURBIDEZ ou VAZAO ~ nucleo robusto) para um corpo d'agua.
    Retorna None se o N do recorte for insuficiente para nenhum dos dois
    alvos (ver _regressao_disponivel_galeria())."""
    df = carregar_dados()
    df_valido = _subset_por_corpo(df[df["VALIDO_PARA_CALCULO"]], corpo)
    robusto, _, _ = carregar_grupos_robusto_moderado_baixo()

    reg_ok, alvo = _regressao_disponivel_galeria(df_valido, robusto)
    if not reg_ok:
        return None

    preditores = [p for p in robusto if p not in ("SALINIDADE", alvo)]
    resultado = ajustar_ols(df_valido, alvo, preditores, min_n_por_preditor=REGRESSAO_MIN_RATIO)
    modelo = resultado["modelo"]

    coef_ord = pd.DataFrame(
        {
            "Parâmetro": [rotulo(v) for v in preditores],
            "β": resultado["coef_padronizado"][preditores].values,
            "p-valor": modelo.pvalues[preditores].values,
        }
    ).sort_values("β")
    cores_b = [CORES["petroleo"] if p < 0.05 else CORES["texto_mudo"] for p in coef_ord["p-valor"]]
    fig = go.Figure(go.Bar(x=coef_ord["β"], y=coef_ord["Parâmetro"], orientation="h", marker_color=cores_b))
    fig.add_vline(x=0, line_color=CORES["grade"])
    layout_editorial(
        fig, title=f"Regressão — {rotulo(alvo)} ~ núcleo robusto", xaxis_title="β padronizado",
        height=100 + 40 * len(coef_ord), margin=dict(l=10, r=40, t=40, b=10),
    )
    stats = {"alvo": alvo, "n": resultado["n"], "r2": modelo.rsquared}
    return fig, stats


@st.cache_data
def figura_pca_corpo(corpo: str) -> tuple[go.Figure, dict] | None:
    """Biplot PCA/clustering ao vivo (Plotly), restrito aos parametros
    ROBUSTO, para um corpo d'agua. Retorna None se o N do recorte for
    insuficiente (ver _pca_disponivel_galeria())."""
    df = carregar_dados()
    df_valido = _subset_por_corpo(df[df["VALIDO_PARA_CALCULO"]], corpo)
    robusto, _, _ = carregar_grupos_robusto_moderado_baixo()

    if not _pca_disponivel_galeria(df_valido, robusto):
        return None

    resultado = calcular_pca_clustering_live(df_valido, robusto)
    scores = resultado["scores"]
    var = resultado["var"]
    var_pc1 = float(var.loc[var["COMPONENTE"] == "PC1", "VARIANCIA_EXPLICADA_PCT"].iloc[0])
    var_pc2 = float(var.loc[var["COMPONENTE"] == "PC2", "VARIANCIA_EXPLICADA_PCT"].iloc[0])

    fig = go.Figure()
    for i, c in enumerate(sorted(scores["CLUSTER"].unique())):
        sub_c = scores[scores["CLUSTER"] == c]
        fig.add_trace(
            go.Scatter(
                x=sub_c["PC1"], y=sub_c["PC2"], mode="markers", name=f"cluster {c}",
                marker=dict(color=CORES_CLUSTER[i % len(CORES_CLUSTER)], size=9),
            )
        )
    layout_editorial(
        fig, title="PCA/Clustering", xaxis_title=f"PC1 ({var_pc1:.1f}%)", yaxis_title=f"PC2 ({var_pc2:.1f}%)",
        height=380, margin=dict(l=10, r=10, t=40, b=10),
    )
    stats = {"n": resultado["n"], "melhor_k": resultado["melhor_k"]}
    return fig, stats


# ------------------------------------------------- relacoes esperadas pela literatura ----

def render_relacoes_esperadas(mostrar_tudo: bool) -> None:
    """Secao "Relacoes esperadas pela literatura" -- sempre bacia inteira
    (comparacao contra a fisico-quimica classica nao faz sentido recortada
    por corpo d'agua com poucas amostras). Usada so pela pagina Bacia toda."""
    st.subheader("Relações esperadas pela literatura")
    st.caption(
        "Estes quatro pares têm justificativa física/química para uma relação específica, mesmo quando a "
        "correlação nos dados é mais fraca que o esperado."
    )
    pares_cache = montar_pares_correlacao()
    lookup_pares = {frozenset((p["a"], p["b"])): p for p in pares_cache}

    for a, b, sinal_esperado, explicacao in RELACOES_ESPERADAS:
        info = lookup_pares.get(frozenset((a, b)))
        col_txt, col_fig = st.columns([2, 1])
        with col_txt:
            st.markdown(f"**{rotulo(a)} × {rotulo(b)}**")
            st.caption(explicacao)
            if info is None:
                st.caption("Par não encontrado na grade (verificar cobertura dos parâmetros).")
            elif info["tipo"] == "Constante/quase sem variância":
                st.caption(f"Nos dados: uma das variáveis é quase constante nesse par (N={info['n']}) — sem correlação calculável.")
            else:
                sinal_encontrado = "positivo" if info["r_pearson"] >= 0 else "negativo"
                confere = "confere" if sinal_encontrado == sinal_esperado else "NÃO confere"
                st.caption(
                    f"Nos dados: Pearson r={info['r_pearson']:.2f}, Spearman ρ={info['r_spearman']:.2f} "
                    f"(N={info['n']}) — sinal {sinal_encontrado}, esperado {sinal_esperado} ({confere}). "
                    f"Classificação: {info['tipo']}."
                )
        with col_fig:
            fig_par, n_fora = figura_par_plotly(a, b, mostrar_tudo)
            st.plotly_chart(fig_par, use_container_width=True, key=f"literatura_{a}_{b}")
            if n_fora:
                st.caption(
                    f"Eixo ajustado para destacar a relação entre as variáveis; {n_fora} ponto(s) fora deste "
                    "intervalo não estão visíveis nesta visualização (arraste o gráfico para vê-los)."
                )

    st.divider()


# ---------------------------------------------------------- secao de 1 corpo d'agua ----

def render_secao_corpo_dagua(nome_secao: str, mostrar_tudo: bool, termo_busca: str = "") -> None:
    """Renderiza histogramas (univariada) + correlacao/dispersao/regressao/
    PCA (multivariada) para UM corpo d'agua (ou "Bacia toda"). Chamada uma
    vez por pagina -- cada pagina da Galeria (5a/5b/5c) e um corpo d'agua
    diferente, entao nao ha necessidade de um seletor de secoes aqui."""
    df = carregar_dados()
    df_valido_geral = df[df["VALIDO_PARA_CALCULO"]]
    df_secao = _subset_por_corpo(df_valido_geral, nome_secao)
    n_secao = len(df_secao)
    robusto, moderado, baixo = carregar_grupos_robusto_moderado_baixo()
    todos = sorted(robusto + moderado) + sorted(baixo)
    termo_busca = termo_busca.strip().lower() if termo_busca else ""

    st.caption(f"N = {n_secao} amostras válidas neste corpo d'água.")

    # --------- univariada ---------
    if nome_secao == "Bacia toda":
        itens_uni = [i for i in montar_itens_estaticos() if i["categoria"] == "Univariada"]
    else:
        itens_uni = []
        for param in todos:
            n_param = df_secao[param].dropna().shape[0]
            if n_param == 0:
                continue
            itens_uni.append({"param": param, "titulo": f"{rotulo(param)} (histograma)", "n": n_param})

    if termo_busca:
        itens_uni = [i for i in itens_uni if termo_busca in i["titulo"].lower()]

    if itens_uni:
        st.subheader(f"Univariada ({len(itens_uni)})")
        colunas = st.columns(3)
        for i, item in enumerate(itens_uni):
            with colunas[i % 3]:
                if nome_secao == "Bacia toda":
                    st.image(item["caminho"], caption=item["titulo"], use_container_width=True)
                else:
                    resultado_hist = figura_histograma_corpo(nome_secao, item["param"])
                    fig_h, n_h = resultado_hist
                    st.plotly_chart(fig_h, use_container_width=True, key=f"hist_{nome_secao}_{item['param']}")
                    st.caption(f"N = {n_h}")
    elif termo_busca:
        st.caption("Nenhum histograma corresponde à busca.")

    st.divider()
    st.subheader("Multivariada")

    if n_secao < 3:
        st.caption(
            "**Multivariada limitada — N insuficiente** neste corpo d'água para correlação, dispersão, "
            "regressão ou PCA (N < 3)."
        )
        return

    fig_corr, n_corr = figura_correlacao_heatmap(nome_secao)
    st.plotly_chart(fig_corr, use_container_width=True, key=f"corr_{nome_secao}")
    legenda_grafico(f"Correlação de Pearson — {nome_secao} (N={n_corr}). * = cobertura Pouca.")

    pares_secao = montar_pares_correlacao(nome_secao)
    if termo_busca:
        pares_secao = [p for p in pares_secao if termo_busca in rotulo(p["a"]).lower() or termo_busca in rotulo(p["b"]).lower()]

    if pares_secao:
        st.markdown(f"**Dispersão par-a-par** ({len(pares_secao)} pares, classificados por tipo de relação na legenda)")
        colunas_p = st.columns(3)
        for i, p in enumerate(pares_secao):
            with colunas_p[i % 3]:
                fig_par, n_fora = figura_par_plotly(p["a"], p["b"], mostrar_tudo, nome_secao)
                layout_editorial(fig_par, title=f"{rotulo(p['a'])} × {rotulo(p['b'])}", height=300, margin=dict(l=10, r=10, t=40, b=10), title_font_size=11)
                st.plotly_chart(fig_par, use_container_width=True, key=f"par_{nome_secao}_{p['a']}_{p['b']}")
                legenda_par = _legenda_par(p)
                if n_fora:
                    legenda_par += f" Eixo ajustado; {n_fora} ponto(s) fora não visíveis."
                st.caption(legenda_par)
    elif termo_busca:
        st.caption("Nenhum par de dispersão corresponde à busca.")

    resultado_reg = figura_regressao_corpo(nome_secao)
    resultado_pca = figura_pca_corpo(nome_secao)

    if resultado_reg is None and resultado_pca is None:
        st.caption(
            "**Regressão múltipla e PCA/Clustering: N insuficiente** neste corpo d'água (mesmos limiares "
            "usados na página 3 de Análise Multivariada)."
        )
        return

    if resultado_reg is not None:
        fig_reg, stats_reg = resultado_reg
        st.markdown(f"**Regressão — {rotulo(stats_reg['alvo'])} ~ núcleo robusto** (N={stats_reg['n']}, R²={stats_reg['r2']:.2f})")
        st.plotly_chart(fig_reg, use_container_width=True, key=f"reg_{nome_secao}")
    else:
        st.caption("Regressão múltipla: N insuficiente neste corpo d'água.")

    if resultado_pca is not None:
        fig_pca, stats_pca = resultado_pca
        st.markdown(f"**PCA/Clustering** (N={stats_pca['n']}, k={stats_pca['melhor_k']})")
        st.plotly_chart(fig_pca, use_container_width=True, key=f"pca_{nome_secao}")
    else:
        st.caption("PCA/Clustering: N insuficiente neste corpo d'água.")
