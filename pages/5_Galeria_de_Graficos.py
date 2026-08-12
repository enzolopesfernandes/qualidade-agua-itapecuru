"""
Pagina 5 -- Galeria de Graficos.

Reune, em um so lugar: (a) todas as figuras PNG estaticas ja geradas pelos
scripts de analise (scripts/01, 02 e 03) em output/figuras/ -- histogramas
univariados de TODOS os parametros, PCA/clustering, regressao; e (b) uma
grade dinamica com TODAS as combinacoes de pares entre os parametros
ROBUSTO/MODERADO (calculada aqui, nao pre-gerada), classificando cada par por
tipo de relacao aparente (linear / monotonica nao-linear / sem relacao /
constante). Os pares dinamicos usam matplotlib (nao plotly) de proposito --
sao ~90 graficos e imagens estaticas leves rendem muito mais rapido no
navegador do que 90 componentes interativos.

Parametros de cobertura Pouca NAO entram na grade de pares (amostra
insuficiente para classificar relacao com confianca -- mesmo criterio das
paginas 2-4), mas continuam com histograma individual na categoria Univariada.
"""

from __future__ import annotations

import io
import itertools
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.estilo import CORES  # noqa: E402
from config.nomes_unidades import rotulo  # noqa: E402
from dashboard_common import (  # noqa: E402
    ICONE_PAGINA,
    OUTPUT_DIR,
    TITULO_TRABALHO,
    carregar_dados,
    carregar_grupos_robusto_moderado_baixo,
    render_header,
)

st.set_page_config(page_title=TITULO_TRABALHO, page_icon=ICONE_PAGINA, layout="wide")
render_header("Galeria de Gráficos")

st.title("5. Galeria de Gráficos")
st.caption(
    "Todos os gráficos gerados pelas análises deste projeto, reunidos em um só lugar: histogramas de "
    "todos os parâmetros, e a dispersão de cada par possível entre parâmetros de cobertura Robusta/"
    "Moderada, já classificada por tipo de relação."
)

FIG_DIR = OUTPUT_DIR / "figuras"

LIMIAR_LINEAR = 0.7
LIMIAR_MONOTONICA = 0.5
GANHO_MONOTONICA = 0.15
DESVIO_MINIMO = 1e-9

# ---------------------------------------------------------- conteudo estatico ----

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


@st.cache_data
def montar_itens_estaticos() -> list[dict]:
    """Histogramas (todos os ~23 parametros), PCA/clustering, regressao e a
    matriz de correlacao -- imagens ja geradas por scripts/01 e scripts/02."""
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


# ---------------------------------------------------- pares dinamicos (ROBUSTO/MODERADO) ----

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


@st.cache_data
def montar_pares_correlacao() -> list[dict]:
    """Todas as combinacoes de pares entre parametros ROBUSTO/MODERADO
    (cobertura Pouca fica de fora -- amostra insuficiente para classificar
    relacao com confianca), com Pearson, Spearman e classificacao do tipo de
    relacao aparente."""
    df = carregar_dados()
    df_valido = df[df["VALIDO_PARA_CALCULO"]]
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
def figura_par_bytes(a: str, b: str) -> bytes:
    """PNG (bytes) de um scatter a-vs-b no estilo editorial -- matplotlib
    (nao plotly) de proposito: ~90 desses precisam ser leves para o navegador."""
    df = carregar_dados()
    df_valido = df[df["VALIDO_PARA_CALCULO"]]
    sub = df_valido[[a, b]].dropna()

    fig, ax = plt.subplots(figsize=(4.0, 3.4))
    fig.patch.set_facecolor(CORES["fundo"])
    ax.set_facecolor(CORES["fundo"])
    ax.scatter(sub[a], sub[b], color=CORES["petroleo"], alpha=0.55, s=16, edgecolor="none")

    if sub[a].std() > DESVIO_MINIMO and sub[b].std() > DESVIO_MINIMO and len(sub) >= 2:
        coef = np.polyfit(sub[a], sub[b], 1)
        xs = np.linspace(sub[a].min(), sub[a].max(), 50)
        ax.plot(xs, np.polyval(coef, xs), color=CORES["texto_primario"], linewidth=1.3)

    ax.set_xlabel(rotulo(a), fontsize=8)
    ax.set_ylabel(rotulo(b), fontsize=8)
    ax.tick_params(labelsize=7, colors=CORES["texto_secundario"])
    ax.grid(axis="both", color=CORES["grade"], linewidth=0.6)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(CORES["texto_mudo"])
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()


def _legenda_par(item: dict) -> str:
    if item["tipo"] == "Constante/quase sem variância":
        return f"{item['tipo']} (N={item['n']}) — não classificado como relação."
    return f"{item['tipo']} — Pearson r={item['r_pearson']:.2f}, Spearman ρ={item['r_spearman']:.2f} (N={item['n']})"


# ------------------------------------------------- relacoes esperadas pela literatura ----

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


def _render_relacao_esperada(a: str, b: str, sinal_esperado: str, explicacao: str, lookup: dict) -> None:
    info = lookup.get(frozenset((a, b)))
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
        st.image(figura_par_bytes(a, b), use_container_width=True)


# ---------------------------------------------------------------------- pagina ----

st.subheader("Relações esperadas pela literatura")
st.caption(
    "Estes quatro pares têm justificativa física/química para uma relação específica, mesmo quando a "
    "correlação nos dados é mais fraca que o esperado — por isso ficam destacados aqui, fora do filtro "
    "abaixo."
)
_pares_cache = montar_pares_correlacao()
_lookup_pares = {frozenset((p["a"], p["b"])): p for p in _pares_cache}
for a, b, sinal, explicacao in RELACOES_ESPERADAS:
    _render_relacao_esperada(a, b, sinal, explicacao, _lookup_pares)

st.divider()

# ---------------------------------------------------------------- grade filtravel ----

itens_estaticos = montar_itens_estaticos()
itens_pares = [
    {
        "tipo": "par",
        "par": (p["a"], p["b"]),
        "titulo": f"{rotulo(p['a'])} × {rotulo(p['b'])}",
        "categoria": p["categoria"],
        "legenda": _legenda_par(p),
    }
    for p in _pares_cache
]
itens = itens_estaticos + itens_pares
categorias = sorted({item["categoria"] for item in itens})

st.markdown("**Filtros**")
col_busca, col_cat = st.columns([2, 3])
busca = col_busca.text_input("Buscar por nome do gráfico ou parâmetro", key="galeria_busca")
categorias_sel = col_cat.multiselect(
    "Categoria", categorias, key="galeria_categorias", placeholder="Selecione uma opção"
)
st.divider()

filtrados = itens
if categorias_sel:
    filtrados = [i for i in filtrados if i["categoria"] in categorias_sel]
if busca:
    termo = busca.strip().lower()
    filtrados = [i for i in filtrados if termo in i["titulo"].lower()]

st.caption(f"{len(filtrados)} de {len(itens)} gráficos.")

if not filtrados:
    st.info("Nenhum gráfico encontrado para esse filtro.")

for categoria in categorias:
    itens_categoria = [i for i in filtrados if i["categoria"] == categoria]
    if not itens_categoria:
        continue
    st.subheader(f"{categoria} ({len(itens_categoria)})")
    colunas = st.columns(3)
    for i, item in enumerate(itens_categoria):
        with colunas[i % 3]:
            if item["tipo"] == "estatico":
                st.image(item["caminho"], caption=item["titulo"], use_container_width=True)
            else:
                a, b = item["par"]
                st.image(figura_par_bytes(a, b), caption=item["titulo"], use_container_width=True)
                st.caption(item["legenda"])
    st.divider()
