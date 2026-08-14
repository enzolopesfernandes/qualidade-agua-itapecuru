"""
Pagina 4 -- Analise Temporal Multivariada.

Tres visuais, aplicados apenas aos parametros de cobertura ROBUSTA (exceto o
item 2, que inclui VAZAO por pedido especifico apesar da cobertura Pouca --
ver nota na propria secao): series padronizadas (z-score) por rodada,
Turbidez/Vazao em dias com/sem chuva, e comparacao entre corpos d'agua ao
longo das rodadas.

EIXO TEMPORAL = PERIODO. PERIODO nao e uma unidade de calendario (um mesmo
periodo pode cair em dois anos-calendario, ex. periodo 6 = 2020-2021), mas e
um eixo cronologico legitimo: os mesmos pontos RNQA sao revisitados ao longo
das rodadas (~6 periodos distintos por ponto em media; so 5 dos 27 pontos
aparecem em uma unica rodada). Cada periodo e tratado como uma rodada unica,
sem subdivisao interna. Eventuais registros sem periodo preenchido ficariam
de fora de todo grafico temporal (nao ha nenhum na base atual). Ver
dashboard_common.tabela_periodos() e agrupar_por_periodo() para o eixo
ordenado.

Nao recalcula nada alem de medias/padronizacoes simples sobre o CSV ja
gerado por scripts/01.
"""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.estilo import CORES, CORES_SEQUENCIA  # noqa: E402
from config.nomes_unidades import rotulo  # noqa: E402
from dashboard_common import (  # noqa: E402
    ICONE_PAGINA,
    TITULO_TRABALHO,
    agrupar_por_periodo,
    bloco_interpretativo,
    carregar_dados,
    carregar_grupos_robusto_moderado_baixo,
    layout_editorial,
    legenda_grafico,
    render_header,
    secao,
    tabela_periodos,
)

PLACEHOLDER = "Selecione uma opção"

st.set_page_config(page_title=TITULO_TRABALHO, page_icon=ICONE_PAGINA, layout="wide")
render_header("Análise Temporal")

st.title("4. Análise Temporal Multivariada")

df = carregar_dados()
df_valido = df[df["VALIDO_PARA_CALCULO"]]
robusto, moderado, baixo = carregar_grupos_robusto_moderado_baixo()

TOTAL_PONTOS_RNQA = df_valido["RNQA"].nunique()
tab_periodos = tabela_periodos(df_valido)
ORDEM_EIXO = tab_periodos["ROTULO_CURTO"].tolist()

bloco_interpretativo(
    "A maior parte dos visuais desta página usa parâmetros de cobertura **Robusta** — a amostra dos "
    "parâmetros de cobertura Pouca é insuficiente para análises temporais cruzadas com confiança "
    "(exceção sinalizada na seção 02, abaixo). A seção 01 também permite alguns parâmetros de cobertura "
    "**Moderada**, sinalizando quando um deles não tem dado suficiente no recorte espacial escolhido."
)
bloco_interpretativo(
    "**Por que o eixo aqui é PERIODO, não ANO:** PERIODO não é uma unidade de calendário (um mesmo "
    "período pode cair em dois anos-calendário — ver rótulos do eixo X), mas é um eixo cronológico "
    "válido: os mesmos pontos RNQA são revisitados ao longo das rodadas (**~6 períodos distintos por "
    f"ponto, em média**; só **5 dos {TOTAL_PONTOS_RNQA} pontos** aparecem numa única rodada). Cada "
    "período é tratado como uma rodada única, sem nenhuma subdivisão interna."
)

# ============================================== 01 · series padronizadas ====

secao("01", "Múltiplos parâmetros na mesma linha do tempo (padronizados)")
bloco_interpretativo(
    "Cada parâmetro é convertido em **z-score** (média 0, desvio padrão 1) a partir da média por "
    "período, o que permite comparar visualmente tendências apesar das escalas e unidades originais "
    "serem diferentes. **Os valores no eixo Y são padronizados — não estão na unidade original do "
    "parâmetro.**"
)

st.markdown("**Recorte espacial**")
st.caption(
    "As duas comparações abaixo (z-score e valores absolutos) só têm utilidade real com o recorte "
    "fixado num corpo d'água ou ponto de coleta — misturar tudo dilui o sinal, já que RIO ITAPECURU "
    "sozinho concentra a maior parte da amostra."
)

_contagem_corpo = df_valido["CORPODAGUA"].value_counts()
_contagem_rnqa = df_valido["RNQA"].value_counts()

col_nivel, col_valor = st.columns([1, 2])
nivel_recorte = col_nivel.selectbox(
    "Nível", ["Toda a bacia", "Corpo d'água", "Ponto de coleta (RNQA)"], key="nivel_recorte_temporal"
)

if nivel_recorte == "Corpo d'água":
    valor_recorte = col_valor.selectbox(
        "Corpo d'água",
        _contagem_corpo.index.tolist(),
        format_func=lambda c: f"{c} (N={int(_contagem_corpo[c])})",
        key="valor_recorte_corpo",
    )
    df_temporal = df_valido[df_valido["CORPODAGUA"] == valor_recorte]
    descricao_recorte = f"corpo d'água {valor_recorte}"
elif nivel_recorte == "Ponto de coleta (RNQA)":
    valor_recorte = col_valor.selectbox(
        "Ponto RNQA",
        _contagem_rnqa.index.tolist(),
        format_func=lambda r: f"{r} (N={int(_contagem_rnqa[r])})",
        key="valor_recorte_rnqa",
    )
    df_temporal = df_valido[df_valido["RNQA"] == valor_recorte]
    descricao_recorte = f"ponto {valor_recorte}"
else:
    df_temporal = df_valido
    descricao_recorte = "toda a bacia (todos os pontos)"

n_periodos_recorte = df_temporal["PERIODO"].nunique(dropna=False)
st.caption(f"Recorte atual: **{descricao_recorte}** — N = {len(df_temporal)} amostras válidas, {n_periodos_recorte} rodada(s) distinta(s).")

PARAMS_MODERADO_TEMPORAL = ["ALCALINIDADE", "SOLIDOS_DISSOLVIDOS", "TRANSPARENCIA_AGUA", "SOLIDOS_SUSPENSOS", "CLORETO_TOTAL", "NITRATO"]
opcoes_params_temporal = robusto + [p for p in PARAMS_MODERADO_TEMPORAL if p in moderado]

_default_series = [p for p in ["TURBIDEZ", "OXIGENIO_DISSOLVIDO", "TEMPERATURA_AGUA", "PH", "COND_ELETRICA_ESPECIFICA"] if p in robusto][:5]
params_sel = st.multiselect(
    "Parâmetros (2 ou mais — todos os Robusto + Alcalinidade, Sólidos Dissolvidos, Transparência da "
    "Água, Sólidos Suspensos, Cloreto Total e Nitrato, de cobertura Moderada)",
    opcoes_params_temporal,
    default=_default_series,
    format_func=rotulo,
    placeholder=PLACEHOLDER,
)

if len(params_sel) < 2:
    bloco_interpretativo("Selecione ao menos 2 parâmetros para comparar.")
elif n_periodos_recorte < 2:
    bloco_interpretativo(
        f"O recorte **{descricao_recorte}** tem dados em menos de 2 rodadas distintas — não é possível "
        "padronizar (z-score) nem comparar tendência. Escolha outro corpo d'água/ponto, ou volte para "
        "\"Toda a bacia\"."
    )
else:
    media_periodo = agrupar_por_periodo(df_temporal, tab_periodos, params_sel)

    cobertura_valida = media_periodo.notna().sum()
    params_insuficientes = [p for p in params_sel if cobertura_valida[p] < 2]
    params_plotaveis = [p for p in params_sel if p not in params_insuficientes]

    if params_insuficientes:
        detalhes = "; ".join(f"{rotulo(p)} (dado em {int(cobertura_valida[p])} período(s))" for p in params_insuficientes)
        bloco_interpretativo(
            f"**{len(params_insuficientes)} parâmetro(s) excluído(s) deste gráfico por falta de dado no recorte "
            f"{descricao_recorte}:** {detalhes}. Parâmetros de cobertura Moderada, em especial, nem sempre têm "
            "amostra em todo corpo d'água/ponto de coleta — mude o recorte espacial acima, ou volte para "
            "\"Toda a bacia\", para incluí-los."
        )

    if len(params_plotaveis) < 2:
        bloco_interpretativo("Menos de 2 parâmetros com dado suficiente neste recorte para padronizar (z-score) e comparar.")
    else:
        padronizado = (media_periodo[params_plotaveis] - media_periodo[params_plotaveis].mean()) / media_periodo[params_plotaveis].std()

        fig_multi = go.Figure()
        for i, p in enumerate(params_plotaveis):
            fig_multi.add_trace(
                go.Scatter(
                    x=padronizado.index,
                    y=padronizado[p],
                    mode="lines+markers",
                    name=rotulo(p),
                    line=dict(color=CORES_SEQUENCIA[i % len(CORES_SEQUENCIA)], width=2.4),
                    marker=dict(size=7),
                )
            )
        layout_editorial(
            fig_multi,
            height=460,
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis_title="Rodada de monitoramento (PERIODO)",
            yaxis_title="Valor padronizado (z-score)",
            legend_title_text="Parâmetro (padronizado)",
        )
        fig_multi.update_xaxes(type="category", categoryorder="array", categoryarray=ORDEM_EIXO)
        st.plotly_chart(fig_multi, use_container_width=True)
        legenda_grafico(
            "Média por rodada de monitoramento, padronizada (z-score) — útil para comparar tendências entre "
            f"parâmetros de escalas diferentes, não para ler a magnitude original. Recorte: {descricao_recorte} "
            f"(N={len(df_temporal)})."
        )

st.markdown("**Comparação em valores absolutos (dois eixos)**")
bloco_interpretativo(
    "Aqui os dois parâmetros ficam nas **unidades originais** (não padronizadas), cada um com sua "
    "própria escala: a legenda/eixo da **esquerda** (linha verde, círculos) é do primeiro parâmetro; a da "
    "**direita** (linha azul, tracejada, losangos) é do segundo. Como as escalas são independentes, compare o "
    "formato/tendência das curvas — não a posição vertical de uma linha em relação à outra."
)

_default_esq = "TURBIDEZ" if "TURBIDEZ" in robusto else robusto[0]
_default_dir = "OXIGENIO_DISSOLVIDO" if "OXIGENIO_DISSOLVIDO" in robusto else robusto[min(1, len(robusto) - 1)]

col_esq, col_dir = st.columns(2)
param_esq = col_esq.selectbox(
    "Parâmetro (eixo esquerdo)", robusto, format_func=rotulo, index=robusto.index(_default_esq), key="param_abs_esq"
)
param_dir = col_dir.selectbox(
    "Parâmetro (eixo direito)", robusto, format_func=rotulo, index=robusto.index(_default_dir), key="param_abs_dir"
)

if param_esq == param_dir:
    bloco_interpretativo("Escolha dois parâmetros diferentes para comparar nos dois eixos.")
elif n_periodos_recorte < 2:
    bloco_interpretativo(
        f"O recorte **{descricao_recorte}** tem dados em menos de 2 rodadas distintas — não dá para "
        "traçar uma linha temporal. Escolha outro corpo d'água/ponto, ou volte para \"Toda a bacia\"."
    )
else:
    media_periodo_abs = agrupar_por_periodo(df_temporal, tab_periodos, [param_esq, param_dir])

    fig_dual = go.Figure()
    fig_dual.add_trace(
        go.Scatter(
            x=media_periodo_abs.index,
            y=media_periodo_abs[param_esq],
            mode="lines+markers",
            name=rotulo(param_esq),
            line=dict(color=CORES["petroleo"], width=2.6),
            marker=dict(size=8),
            yaxis="y1",
        )
    )
    _cor_dir = CORES_SEQUENCIA[2]
    fig_dual.add_trace(
        go.Scatter(
            x=media_periodo_abs.index,
            y=media_periodo_abs[param_dir],
            mode="lines+markers",
            name=rotulo(param_dir),
            line=dict(color=_cor_dir, width=2.6, dash="dot"),
            marker=dict(size=8, symbol="diamond"),
            yaxis="y2",
        )
    )
    layout_editorial(
        fig_dual,
        height=460,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title="Rodada de monitoramento (PERIODO)",
        yaxis=dict(
            title=dict(text=rotulo(param_esq), font=dict(color=CORES["petroleo"])),
            tickfont=dict(color=CORES["petroleo"]),
        ),
        yaxis2=dict(
            title=dict(text=rotulo(param_dir), font=dict(color=_cor_dir)),
            tickfont=dict(color=_cor_dir),
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig_dual.update_xaxes(type="category", categoryorder="array", categoryarray=ORDEM_EIXO)
    st.plotly_chart(fig_dual, use_container_width=True)
    legenda_grafico(
        f"Médias por rodada em unidade original. Esquerda (verde): {rotulo(param_esq)}. "
        f"Direita (azul, tracejado): {rotulo(param_dir)}. Recorte: {descricao_recorte} (N={len(df_temporal)})."
    )

st.divider()

# ==================================== 02 · turbidez/vazao x chuva em 24h ====

secao("02", "Turbidez e Vazão em dias com e sem chuva")
bloco_interpretativo(
    "**Vazão tem cobertura Pouca** (N pequeno) — incluída aqui por ser um dos dois parâmetros "
    "pedidos especificamente para esta comparação, mas o resultado deve ser tratado como "
    "exploratório, não conclusivo. Turbidez tem cobertura Robusta."
)

dados_chuva = df_valido[df_valido["CHOVEU_EM_24H"].isin(["SIM", "NAO"])].copy()
dados_chuva["GRUPO_CHUVA"] = dados_chuva["CHOVEU_EM_24H"].map({"SIM": "Choveu", "NAO": "Não choveu"})

col_tb, col_vz = st.columns(2)
for coluna, param in zip([col_tb, col_vz], ["TURBIDEZ", "VAZAO"]):
    dados_param = dados_chuva[["GRUPO_CHUVA", param]].dropna()
    if dados_param.empty:
        coluna.info(f"Sem dados de {rotulo(param)} com registro de chuva em 24h.")
        continue
    contagem = dados_param["GRUPO_CHUVA"].value_counts()
    dados_param["GRUPO_N"] = dados_param["GRUPO_CHUVA"].map(lambda g: f"{g} (N={contagem[g]})")
    ordem = [f"{g} (N={contagem[g]})" for g in ["Choveu", "Não choveu"] if g in contagem]

    fig_chuva = px.box(
        dados_param,
        x="GRUPO_N",
        y=param,
        category_orders={"GRUPO_N": ordem},
        labels={"GRUPO_N": "", param: rotulo(param)},
        color_discrete_sequence=[CORES["petroleo"]],
    )
    layout_editorial(fig_chuva, height=400, margin=dict(l=10, r=10, t=40, b=10), title=rotulo(param))
    coluna.plotly_chart(fig_chuva, use_container_width=True)

legenda_grafico(
    "Grupos definidos pela coluna CHOVEU_EM_24H (registro de chuva nas 24h anteriores à coleta); "
    "N de cada grupo indicado no eixo X. Amostras sem esse registro foram excluídas da comparação."
)

st.divider()

# ==================================== 03 · corpos d'agua ao longo dos periodos ====

secao("03", "Comparação entre corpos d'água ao longo dos períodos")
st.caption("Eixo X em PERIODO — ver bloco explicativo no topo da página para a justificativa.")

param_corpos = st.selectbox(
    "Parâmetro (cobertura Robusta)", robusto, format_func=rotulo, key="param_corpos_tempo"
)

contagem_corpo_total = df_valido["CORPODAGUA"].value_counts()

fig_corpos = go.Figure()
for i, corpo in enumerate(contagem_corpo_total.index.tolist()):
    sub_corpo = df_valido[df_valido["CORPODAGUA"] == corpo]
    media_corpo = agrupar_por_periodo(sub_corpo, tab_periodos, [param_corpos])
    eh_principal = corpo == "RIO ITAPECURU"
    cor = CORES["petroleo"] if eh_principal else CORES_SEQUENCIA[i % len(CORES_SEQUENCIA)]
    fig_corpos.add_trace(
        go.Scatter(
            x=media_corpo.index,
            y=media_corpo[param_corpos],
            mode="lines+markers",
            name=f"{corpo} (N={contagem_corpo_total[corpo]})",
            line=dict(color=cor, width=3.4 if eh_principal else 1.3),
            marker=dict(size=9 if eh_principal else 6, color=cor),
        )
    )
layout_editorial(
    fig_corpos,
    height=460,
    margin=dict(l=10, r=10, t=20, b=10),
    xaxis_title="Período",
    yaxis_title=rotulo(param_corpos),
)
fig_corpos.update_xaxes(type="category", categoryorder="array", categoryarray=ORDEM_EIXO)
st.plotly_chart(fig_corpos, use_container_width=True)
legenda_grafico(
    f"RIO ITAPECURU (linha mais grossa) concentra {contagem_corpo_total.get('RIO ITAPECURU', 0)} das "
    f"{len(df_valido)} amostras válidas; os demais corpos d'água têm poucas observações por período e "
    "suas linhas são menos confiáveis. Lacunas na linha = período sem amostra válida daquele corpo "
    "d'água, não zero."
)
