"""
Pagina 5b -- Galeria de Graficos: RIO ITAPECURU.

RIO ITAPECURU concentra 241 das 340 amostras validas -- o unico corpo
d'agua, alem da bacia inteira, com N suficiente para regressao e PCA/
clustering completos (ver limiares em galeria_common.REGRESSAO_MIN_RATIO e
_pca_disponivel_galeria()). Ver galeria_common.py para a logica
compartilhada com as demais paginas da Galeria.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dashboard_common import ICONE_PAGINA, TITULO_TRABALHO, render_header  # noqa: E402
from galeria_common import render_secao_corpo_dagua  # noqa: E402

CORPO = "RIO ITAPECURU"

st.set_page_config(page_title=TITULO_TRABALHO, page_icon=ICONE_PAGINA, layout="wide")
render_header("Galeria — Rio Itapecuru")

st.title(f"5b. Galeria de Gráficos — {CORPO.title()}")
st.caption(
    "Maior corpo d'água da bacia em número de amostras — todos os gráficos (histogramas, correlação, "
    "dispersão, regressão e PCA/clustering) recalculados ao vivo, restritos a este corpo d'água."
)

st.checkbox(
    "Mostrar todos os pontos (incluindo outliers)",
    value=False,
    key="galeria_mostrar_tudo",
    help="Por padrão, os scatters de relação abaixo têm o eixo ajustado para destacar a nuvem principal "
    "de pontos (intervalo interquartil expandido). Ative para voltar ao range completo dos dados.",
)
mostrar_tudo = st.session_state["galeria_mostrar_tudo"]

busca = st.text_input("Buscar por nome do gráfico ou parâmetro", key="galeria_busca_itapecuru")
st.divider()

render_secao_corpo_dagua(CORPO, mostrar_tudo, busca)
