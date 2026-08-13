"""
Pagina 1 -- Contexto e Dados.

Visao geral do dataset (DADOS_ANALISE), mapa interativo dos pontos de coleta
(RNQA) e tabela de cobertura por parametro. Nao recalcula nada: le os CSVs
gerados por scripts/01_univariate_outliers.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.estilo import CORES, CORES_STATUS, ROTULOS_CATEGORIA  # noqa: E402
from config.nomes_unidades import rotulo  # noqa: E402
from dashboard_common import (  # noqa: E402
    ICONE_PAGINA,
    PARAMS_ROBUSTOS_PRIORITARIOS,
    TITULO_TRABALHO,
    badge_categoria,
    bloco_interpretativo,
    carregar_dados,
    carregar_resumo_cobertura,
    construir_mapa_pontos,
    render_header,
    secao,
)

st.set_page_config(page_title=TITULO_TRABALHO, page_icon=ICONE_PAGINA, layout="wide")
render_header("Contexto e Dados")

st.title("1. Contexto e Dados")

df = carregar_dados()
resumo = carregar_resumo_cobertura()

# ------------------------------------------------------- de onde vem os dados ----

secao("01", "De onde vêm os dados")
st.markdown(
    """
Os dados vêm do monitoramento periódico realizado pela **Agência Nacional de Águas e Saneamento
Básico (ANA)**, por meio da **Rede Nacional de Monitoramento da Qualidade da Água (RNQA)** — rede
criada em 2013, que reúne dados de qualidade da água coletados pelos órgãos estaduais em pontos
fixos, com frequência regular, seguindo metodologia padronizada nacionalmente. O código **RNQA**
presente nos dados é justamente o identificador do ponto de monitoramento dentro dessa rede.

No Maranhão, essa coleta é organizada em **períodos** (P1 a P10) e, dentro de cada período, em
**campanhas** (1ª/2ª). Este painel usa o recorte já filtrado para a Bacia do Itapecuru: as amostras
abaixo, em pontos identificados pelo código RNQA — alguns desses pontos também têm um código de
estação da ANA vinculado.

Cada amostra reúne parâmetros medidos em campo (profundidade, vazão, temperatura, pH, oxigênio
dissolvido, condutividade, turbidez, transparência) e parâmetros de laboratório (cloreto, fluoreto,
brometo, nitrato, nitrito, sulfato, fosfatos, nitrogênio amoniacal). No tratamento da base original:

- **9 registros** com valores fisicamente implausíveis (ex. profundidade ou vazão negativa) foram
  sinalizados — mantidos na base para auditoria, mas excluídos dos cálculos deste painel.
- Vários parâmetros de nutrientes têm resultados **abaixo do limite de quantificação (LQ)** do método
  analítico; nesses casos, o valor de laboratório (ex. "< 0,1") foi substituído por metade do LQ, prática
  padrão em química ambiental — o texto original censurado foi preservado em colunas de auditoria
  separadas, não usadas nos cálculos.
"""
)

st.divider()

# ---------------------------------------------------------- visao geral ----

n_amostras = len(df)
n_validas = int(df["VALIDO_PARA_CALCULO"].sum())
n_invalidas = n_amostras - n_validas
n_pontos = df["RNQA"].nunique()
n_corpos = df["CORPODAGUA"].nunique()
ano_min, ano_max = int(df["ANO"].min()), int(df["ANO"].max())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Amostras", n_amostras, help=f"{n_validas} válidas para cálculo · {n_invalidas} excluídas (ver nota)")
c2.metric("Pontos de coleta (RNQA)", n_pontos)
c3.metric("Corpos d'água", n_corpos)
c4.metric("Período monitorado", f"{ano_min}–{ano_max}")

dominancia = df["CORPODAGUA"].value_counts()
st.caption(
    f"**{dominancia.index[0]}** concentra {dominancia.iloc[0]} das {n_amostras} amostras "
    f"({dominancia.iloc[0] / n_amostras:.0%}); os demais {n_corpos - 1} corpos d'água somam "
    f"{n_amostras - dominancia.iloc[0]} amostras."
)

st.divider()

# --------------------------------------------------------------- mapa ----

secao("02", "Mapa dos pontos de coleta")
st.caption(
    "Cada marcador é um ponto RNQA, posicionado na média das coordenadas registradas nele. "
    "Clique em um marcador para ver os valores mais recentes dos parâmetros ROBUSTO nesse ponto."
)


@st.cache_data
def preparar_dados_mapa(_df: pd.DataFrame) -> pd.DataFrame:
    coords = _df.groupby("RNQA")[["LATITUDE", "LONGITUDE"]].mean()

    validos = _df[_df["VALIDO_PARA_CALCULO"] & _df["DATA_COLETA"].notna()].copy()
    mais_recente = validos.groupby("RNQA")["DATA_COLETA"].transform("max") == validos["DATA_COLETA"]
    recentes = validos[mais_recente]

    agregacao = {"CORPODAGUA": "first", "MUNICIPIO": "first", "DATA_COLETA": "max"}
    agregacao.update({p: "mean" for p in PARAMS_ROBUSTOS_PRIORITARIOS})
    resumo_recente = recentes.groupby("RNQA").agg(agregacao)

    return coords.join(resumo_recente, how="left").reset_index()


pontos_mapa = preparar_dados_mapa(df)
sem_coordenadas = pontos_mapa[pontos_mapa["LATITUDE"].isna() | pontos_mapa["LONGITUDE"].isna()]

mapa = construir_mapa_pontos(
    pontos_mapa,
    campos_popup=[("última coleta válida", "DATA_COLETA")] + [(rotulo(p), p) for p in PARAMS_ROBUSTOS_PRIORITARIOS],
)
st_folium(mapa, width=None, height=560, returned_objects=[])

if len(sem_coordenadas) > 0:
    st.caption(
        f"{len(sem_coordenadas)} ponto(s) sem nenhuma coordenada registrada e por isso não exibido(s) no "
        f"mapa: {', '.join(sem_coordenadas['RNQA'].tolist())}."
    )

st.divider()

# ------------------------------------------------------ tabela de cobertura ----

secao("03", "Cobertura de dados por parâmetro")
st.caption("Classificação de confiabilidade usada em **todo** o dashboard (mesma cor sempre com o mesmo significado):")
leg1, leg2, leg3, _ = st.columns([1, 1, 1, 3])
with leg1:
    badge_categoria("ROBUSTO")
    st.caption("N ≥ 250 amostras válidas")
with leg2:
    badge_categoria("MODERADO")
    st.caption("50 ≤ N < 250")
with leg3:
    badge_categoria("BAIXO")
    st.caption("N < 50 — cautela")

tabela = resumo.copy()
tabela["CATEGORIA"] = tabela["COBERTURA"].apply(
    lambda c: ROTULOS_CATEGORIA["BAIXO"] if c.startswith("BAIXO") else ROTULOS_CATEGORIA.get(c, c)
)
tabela["Parâmetro"] = tabela["PARAMETRO"].apply(rotulo)
tabela = tabela.rename(
    columns={
        "N_VALIDO_PARAMETRO": "N válido",
        "PERC_PREENCHIMENTO": "% preenchido",
        "N_OUTLIERS_IQR": "N outliers (IQR)",
        "PERC_OUTLIERS_SOBRE_VALIDOS": "% outliers",
    }
)
tabela = tabela.sort_values("N válido", ascending=False)
colunas_exibir = ["Parâmetro", "N válido", "% preenchido", "N outliers (IQR)", "% outliers", "CATEGORIA"]

_ROTULO_PARA_CHAVE = {v: k for k, v in ROTULOS_CATEGORIA.items()}


def _cor_categoria(valor: str) -> str:
    chave = _ROTULO_PARA_CHAVE.get(valor)
    cor = CORES_STATUS.get(chave, CORES["texto_mudo"])
    return f"background-color:{cor}; color:#ffffff; font-weight:600;"


estilizada = tabela[colunas_exibir].style.applymap(_cor_categoria, subset=["CATEGORIA"])
st.dataframe(estilizada, use_container_width=True, hide_index=True)

st.divider()

# ------------------------------------------------------------- notas ----

secao("04", "Notas metodológicas importantes")

bloco_interpretativo(
    f"**{n_invalidas} registros excluídos dos cálculos** (`FLAG_VALOR_INVALIDO = SIM`): valores "
    "fisicamente implausíveis (ex. profundidade ou vazão negativa) identificados na auditoria dos "
    "dados brutos. Essas linhas permanecem no dataset para auditoria, mas não entram em nenhuma "
    "estatística, gráfico ou modelo deste painel."
)

bloco_interpretativo(
    "**Correlações quase perfeitas entre parâmetros de cobertura Pouca podem ser artefato, não relação "
    "real.** Nos parâmetros classificados como Pouco (N ≤ 39), o Fluoreto Total, o Nitrito e o Fosfato "
    "Total chegam a ter correlação de ±0,97–1,00 entre si — mas isso ocorre porque **todas as amostras "
    "desse subconjunto estavam abaixo do limite de detecção (LOD)** do método analítico e foram "
    "registradas como metade do LOD (ex. \"< 0,1\" → 0,05), não por uma relação físico-química real "
    "entre os parâmetros. Ver página 3 (Análise Multivariada) para o detalhamento."
)
