"""
Pagina 5a -- Galeria de Graficos: Bacia toda.

Ver galeria_common.py para a logica compartilhada com as demais paginas da
Galeria (5b_Galeria_Rio_Itapecuru.py, 5c_Galeria_Demais_Corpos_Dagua.py) --
cada uma cobre um corpo d'agua diferente, em paginas Streamlit separadas de
proposito: trocar de pagina no Streamlit descarta o conteudo das demais, ao
contrario de abas/expanders (que ficam todos no mesmo script e sao
recalculados juntos a cada interacao).
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dashboard_common import ICONE_PAGINA, TITULO_TRABALHO, render_header  # noqa: E402
from galeria_common import render_relacoes_esperadas, render_secao_corpo_dagua  # noqa: E402

st.set_page_config(page_title=TITULO_TRABALHO, page_icon=ICONE_PAGINA, layout="wide")
render_header("Galeria — Bacia toda")

st.title("5a. Galeria de Gráficos — Bacia toda")
st.caption(
    "Todos os parâmetros, todas as amostras válidas da bacia inteira. Histogramas, PCA/clustering e "
    "regressão reusam os PNGs pré-gerados pelos scripts de análise; correlação e dispersão par-a-par são "
    "recalculadas ao vivo."
)

st.checkbox(
    "Mostrar todos os pontos (incluindo outliers)",
    value=False,
    key="galeria_mostrar_tudo",
    help="Por padrão, os scatters de relação abaixo têm o eixo ajustado para destacar a nuvem principal "
    "de pontos (intervalo interquartil expandido). Ative para voltar ao range completo dos dados.",
)
mostrar_tudo = st.session_state["galeria_mostrar_tudo"]

render_relacoes_esperadas(mostrar_tudo)

busca = st.text_input("Buscar por nome do gráfico ou parâmetro", key="galeria_busca_bacia")
st.divider()

render_secao_corpo_dagua("Bacia toda", mostrar_tudo, busca)
