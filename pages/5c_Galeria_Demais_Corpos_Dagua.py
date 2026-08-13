"""
Pagina 5c -- Galeria de Graficos: demais corpos d'agua.

Agrupa, numa unica pagina com um seletor, os corpos d'agua que sobram alem
de "Bacia toda" (5a) e RIO ITAPECURU (5b) -- cada um tem poucas amostras
(RIO PERITORO, RIO TAPUIO, RIO PIRAPEMAS, RIACHO PERITORO, RIO CODOZINHO,
RIO ALPERCATAS), entao nao justificam uma pagina Streamlit dedicada cada.
So um corpo d'agua e calculado por vez (o selecionado), nao os 6 juntos.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dashboard_common import ICONE_PAGINA, TITULO_TRABALHO, carregar_dados, render_header  # noqa: E402
from galeria_common import render_secao_corpo_dagua  # noqa: E402

st.set_page_config(page_title=TITULO_TRABALHO, page_icon=ICONE_PAGINA, layout="wide")
render_header("Galeria — Demais corpos d'água")

st.title("5c. Galeria de Gráficos — Demais corpos d'água")
st.caption(
    "Corpos d'água com poucas amostras em relação ao RIO ITAPECURU (página 5b) — histogramas, "
    "correlação e dispersão sempre disponíveis; regressão e PCA/clustering só quando o N permitir com "
    "segurança (ver nota na seção Multivariada)."
)

df = carregar_dados()
df_valido = df[df["VALIDO_PARA_CALCULO"]]
contagem_corpo = df_valido[df_valido["CORPODAGUA"] != "RIO ITAPECURU"]["CORPODAGUA"].value_counts()
corpos_restantes = contagem_corpo.index.tolist()

corpo_sel = st.selectbox(
    "Corpo d'água", corpos_restantes, format_func=lambda c: f"{c} (N={int(contagem_corpo[c])})",
)

st.checkbox(
    "Mostrar todos os pontos (incluindo outliers)",
    value=False,
    key="galeria_mostrar_tudo",
    help="Por padrão, os scatters de relação abaixo têm o eixo ajustado para destacar a nuvem principal "
    "de pontos (intervalo interquartil expandido). Ative para voltar ao range completo dos dados.",
)
mostrar_tudo = st.session_state["galeria_mostrar_tudo"]

busca = st.text_input("Buscar por nome do gráfico ou parâmetro", key="galeria_busca_demais")
st.divider()

render_secao_corpo_dagua(corpo_sel, mostrar_tudo, busca)
