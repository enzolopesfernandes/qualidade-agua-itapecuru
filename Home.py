"""Pagina inicial do dashboard -- resumo do projeto e visao geral dos dados."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from dashboard_common import (  # noqa: E402
    ICONE_PAGINA,
    TITULO_TRABALHO,
    big_stats_row,
    carregar_dados,
    render_header,
    render_titulo_trabalho,
)

st.set_page_config(page_title=TITULO_TRABALHO, page_icon=ICONE_PAGINA, layout="wide")
render_header("Início")

st.markdown('<p class="kicker">TCC / Artigo Acadêmico</p>', unsafe_allow_html=True)
render_titulo_trabalho("h1")

st.markdown(
    """
A qualidade da água é um fator essencial para a saúde humana e a preservação ambiental. A Bacia
Hidrográfica do Rio Itapecuru, responsável pelo abastecimento de aproximadamente 1,4 milhão de
habitantes no Maranhão, vem sofrendo pressões como desmatamento e expansão agropecuária,
comprometendo seus recursos hídricos. Diante desse cenário, o monitoramento contínuo e a análise dos
dados de qualidade da água tornam-se fundamentais para a gestão sustentável da bacia.

Este projeto propõe a análise exploratória de dados de monitoramento da água do rio Itapecuru,
visando a construção de dashboards interativos e relatórios analíticos que possibilitem uma
interpretação mais acessível e estratégica dos indicadores ambientais. Para isso, são aplicadas
técnicas de análise univariada e multivariada, além de análise de correlação entre indicadores. Como
resultado, o projeto entrega produtos que podem ser utilizados tanto em pesquisas futuras quanto por
gestores públicos na tomada de decisões, fortalecendo a conservação da Bacia do Itapecuru e
promovendo o uso mais eficiente dos recursos hídricos.
"""
)
st.caption("Palavras-chave: Análise de Dados · Dashboards · Dados Ambientais")

st.divider()

df = carregar_dados()
big_stats_row(
    [
        (str(len(df)), "Amostras"),
        (str(df["RNQA"].nunique()), "Pontos de coleta (RNQA)"),
        (str(df["CORPODAGUA"].nunique()), "Corpos d'água"),
        (f"{int(df['ANO'].min())}–{int(df['ANO'].max())}", "Período"),
    ]
)
