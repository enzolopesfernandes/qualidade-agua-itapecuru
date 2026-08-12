"""
Pagina 3 -- Analise Multivariada.

Correlacao (heatmap interativo, recalculado ao vivo para respeitar o recorte
espacial), dispersao par-a-par (ao vivo), regressao multipla (TURBIDEZ/VAZAO)
e PCA/clustering. Regressao e PCA/clustering le os CSVs ja gerados pelos
scripts 02 e 03 -- nao recalcula (sempre bacia inteira: amostra menor
invalidaria essas analises). Correlacao e dispersao usam pandas .corr()
direto sobre o CSV de amostras (mesmo metodo do script 02), o que permite
respeitar o filtro de corpo d'agua/ponto RNQA -- e reproduz os mesmos numeros
do CSV estatico quando o recorte e "Toda a bacia".
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.estilo import CORES, CORES_CLUSTER  # noqa: E402
from config.nomes_unidades import rotulo  # noqa: E402
from dashboard_common import (  # noqa: E402
    ICONE_PAGINA,
    TITULO_TRABALHO,
    badge_confiabilidade,
    bloco_interpretativo,
    carregar_dados,
    carregar_grupos_robusto_moderado_baixo,
    carregar_pca,
    carregar_regressao,
    carregar_resumo_cobertura,
    carregar_silhouette,
    layout_editorial,
    legenda_grafico,
    render_header,
    secao,
)

st.set_page_config(page_title=TITULO_TRABALHO, page_icon=ICONE_PAGINA, layout="wide")
render_header("Análise Multivariada")

st.title("3. Análise Multivariada")

df = carregar_dados()
df_valido = df[df["VALIDO_PARA_CALCULO"]]
robusto, moderado, baixo = carregar_grupos_robusto_moderado_baixo()
principal = robusto + moderado
todos = principal + baixo
resumo_cobertura = carregar_resumo_cobertura()

# --------------------------------------------------------- recorte espacial ----

st.markdown("**Recorte espacial** (aplica-se às seções 01 e 02, abaixo)")
st.caption(
    "Regressão múltipla (03) e PCA/Clustering (04) sempre usam a bacia inteira, mesmo com um recorte "
    "escolhido aqui — essas análises exigem uma amostra maior para serem estatisticamente válidas."
)

_contagem_corpo3 = df_valido["CORPODAGUA"].value_counts()
_contagem_rnqa3 = df_valido["RNQA"].value_counts()

col_nivel3, col_valor3 = st.columns([1, 2])
nivel_recorte3 = col_nivel3.selectbox(
    "Nível", ["Toda a bacia", "Corpo d'água", "Ponto de coleta (RNQA)"], key="nivel_recorte_multivariada"
)

if nivel_recorte3 == "Corpo d'água":
    valor_recorte3 = col_valor3.selectbox(
        "Corpo d'água",
        _contagem_corpo3.index.tolist(),
        format_func=lambda c: f"{c} (N={int(_contagem_corpo3[c])})",
        key="valor_recorte_corpo_multivariada",
    )
    df_recorte = df_valido[df_valido["CORPODAGUA"] == valor_recorte3]
    descricao_recorte3 = f"corpo d'água {valor_recorte3}"
elif nivel_recorte3 == "Ponto de coleta (RNQA)":
    valor_recorte3 = col_valor3.selectbox(
        "Ponto RNQA",
        _contagem_rnqa3.index.tolist(),
        format_func=lambda r: f"{r} (N={int(_contagem_rnqa3[r])})",
        key="valor_recorte_rnqa_multivariada",
    )
    df_recorte = df_valido[df_valido["RNQA"] == valor_recorte3]
    descricao_recorte3 = f"ponto {valor_recorte3}"
else:
    df_recorte = df_valido
    descricao_recorte3 = "toda a bacia (todos os pontos)"

st.caption(f"Recorte atual: **{descricao_recorte3}** — N = {len(df_recorte)} amostras válidas.")
if nivel_recorte3 != "Toda a bacia":
    bloco_interpretativo(
        f"Recorte estreito (N={len(df_recorte)}): correlações e dispersões abaixo ficam mais instáveis "
        "quanto menor o N — trate como exploratório, sobretudo com poucas dezenas de amostras."
    )

st.divider()

# ============================================================ correlacao ====

secao("01", "Correlação")

bloco_interpretativo(
    "A **correlação de Pearson** mede o quanto duas variáveis se movem juntas de forma linear, numa "
    "escala de **−1 a +1**. Valores próximos de +1 indicam que as duas sobem/descem juntas; próximos "
    "de −1, que uma sobe quando a outra desce; próximos de 0, que não há relação linear detectável. "
    "Na escala de cor abaixo, **quanto mais escura/intensa a célula, mais forte a relação** — seja "
    "positiva (tom escuro de petróleo) ou negativa (tom escuro de grafite) — e células claras no meio "
    "da escala indicam relação fraca. A **linha preta** separa o bloco principal de parâmetros com "
    "cobertura Robusta/Moderada (mais confiáveis) do bloco de cobertura Pouca (mais exploratório, "
    "marcado com \\*). Os pares destacados na tabela abaixo do mapa **não devem ser usados para "
    "conclusões fortes**: a correlação alta entre eles é, em boa parte, artefato de amostras pequenas "
    "ou censuradas no limite de detecção — não uma relação físico-química comprovada."
)

corr = df_recorte[todos].corr(method="pearson")
n_pairwise = pd.DataFrame(index=todos, columns=todos, dtype="float")
for _a in todos:
    for _b in todos:
        n_pairwise.loc[_a, _b] = df_recorte[[_a, _b]].dropna().shape[0]
n_pairwise = n_pairwise.astype(int)
n_total = len(todos)
labels = [f"{rotulo(p)}{'*' if p in baixo else ''}" for p in todos]

z = corr.values
n_matrix = n_pairwise.reindex(index=todos, columns=todos).values
texto = np.array([[("" if np.isnan(z[i, j]) else f"{z[i, j]:.2f}") for j in range(n_total)] for i in range(n_total)])

customdata = np.empty((n_total, n_total, 3), dtype=object)
for i in range(n_total):
    for j in range(n_total):
        customdata[i, j, 0] = labels[i]
        customdata[i, j, 1] = labels[j]
        customdata[i, j, 2] = int(n_matrix[i, j])

fig_corr = go.Figure(
    data=go.Heatmap(
        z=z,
        x=list(range(n_total)),
        y=list(range(n_total)),
        zmin=-1,
        zmax=1,
        colorscale=[[0.0, CORES["petroleo"]], [0.5, CORES["fundo_alt"]], [1.0, CORES["cinza_escuro"]]],
        customdata=customdata,
        hovertemplate="%{customdata[0]} × %{customdata[1]}<br>r = %{z:.3f}<br>N = %{customdata[2]}<extra></extra>",
        text=texto,
        texttemplate="%{text}",
        textfont={"size": 9},
        colorbar=dict(title="r"),
    )
)
fig_corr.update_xaxes(tickmode="array", tickvals=list(range(n_total)), ticktext=labels, tickangle=-60)
fig_corr.update_yaxes(tickmode="array", tickvals=list(range(n_total)), ticktext=labels, autorange="reversed")

corte = len(principal) - 0.5
fig_corr.add_shape(type="line", x0=corte, x1=corte, y0=-0.5, y1=n_total - 0.5, line=dict(color=CORES["texto_primario"], width=2))
fig_corr.add_shape(type="line", x0=-0.5, x1=n_total - 0.5, y0=corte, y1=corte, line=dict(color=CORES["texto_primario"], width=2))

layout_editorial(fig_corr, height=760, margin=dict(l=10, r=10, t=30, b=10))
st.plotly_chart(fig_corr, use_container_width=True)

PARES_ATENCAO = [
    ("FLUORETO_TOTAL", "NITRITO", "Ambos censurados no limite de detecção (LOD) — todas as amostras desse subconjunto (N=20) foram registradas como metade do LOD (ex. \"< 0,1\" → 0,05). A correlação é artefato da codificação, não relação física real."),
    ("ALCALINIDADE", "FLUORETO_TOTAL", "Mesma origem: subconjunto de amostras com Fluoreto censurado no LOD coincide com valores baixos de Alcalinidade — coincidência de subamostra, não relação causal estabelecida."),
    ("CLORETO_TOTAL", "BROMETO_TOTAL", "N=20 — amostra pequena demais para confirmar a relação com confiança, mesmo sendo fisicamente plausível (íons associados em água salobra)."),
]
linhas_atencao = []
for a, b, nota in PARES_ATENCAO:
    linhas_atencao.append(
        {
            "Par": f"{rotulo(a)} × {rotulo(b)}",
            "r": corr.loc[a, b],
            "N": int(n_pairwise.loc[a, b]),
            "Por que ter cautela": nota,
        }
    )
st.markdown("**Pares de atenção (destacados na matriz acima) — não usar para conclusões fortes:**")
st.dataframe(linhas_atencao, use_container_width=True, hide_index=True)

st.divider()

# =================================================== dispersao (explorador) ====

secao("02", "Dispersão: um parâmetro comparado com todos os outros")
st.caption(
    "Escolha um parâmetro no filtro abaixo para ver sua dispersão contra **cada um** dos demais "
    "parâmetros, com reta de tendência OLS simples, N e r de cada par."
)

col_disp_sel, col_disp_badge = st.columns([2, 4])
parametro_disp = col_disp_sel.selectbox(
    "Parâmetro",
    todos,
    format_func=rotulo,
    index=todos.index("TURBIDEZ") if "TURBIDEZ" in todos else 0,
    key="disp_parametro",
)
with col_disp_badge:
    st.write("")
    badge_confiabilidade(parametro_disp, resumo_cobertura)

outros_parametros = [p for p in todos if p != parametro_disp]
cols_scatter = st.columns(3)
n_ocultos = 0
for i, outro in enumerate(outros_parametros):
    dados = df_recorte[[parametro_disp, outro]].dropna()
    if len(dados) < 3:
        n_ocultos += 1
        continue
    r = dados[parametro_disp].corr(dados[outro])
    fig_sc = px.scatter(
        dados, x=outro, y=parametro_disp, trendline="ols",
        labels={outro: rotulo(outro), parametro_disp: rotulo(parametro_disp)},
        title=f"{rotulo(parametro_disp)} vs. {rotulo(outro)}  (N={len(dados)}, r={r:.2f})",
    )
    fig_sc.update_traces(marker=dict(color=CORES["petroleo"], size=6, opacity=0.5), selector=dict(mode="markers"))
    fig_sc.update_traces(line=dict(color=CORES["linha_tendencia"], width=2), selector=dict(mode="lines"))
    layout_editorial(fig_sc, height=330, margin=dict(l=10, r=10, t=45, b=10), title_font_size=12)
    cols_scatter[(i - n_ocultos) % 3].plotly_chart(fig_sc, use_container_width=True)

legenda_grafico(
    f"{len(outros_parametros) - n_ocultos} de {len(outros_parametros)} pares exibidos "
    f"(N ≥ 3 amostras em comum)." + (f" {n_ocultos} par(es) ocultos por N < 3." if n_ocultos else "")
    + f" Recorte: {descricao_recorte3}."
)

st.divider()

# ============================================================ regressao ====

secao("03", "Regressão múltipla — o que influencia Turbidez e Vazão")
st.caption("Esta seção sempre usa a bacia inteira, independente do recorte espacial escolhido acima.")

st.subheader("Coeficientes da regressão múltipla")

coef, met = carregar_regressao()
alvos_disponiveis = met["ALVO"].unique().tolist()

c_sel1, c_sel2 = st.columns(2)
alvo_sel = c_sel1.selectbox("Variável alvo", alvos_disponiveis, format_func=rotulo)
modelos_disponiveis = met.loc[met["ALVO"] == alvo_sel, "MODELO"].tolist()
modelo_sel = c_sel2.radio(
    "Modelo",
    modelos_disponiveis,
    index=modelos_disponiveis.index("nucleo_robusto") if "nucleo_robusto" in modelos_disponiveis else 0,
    format_func=lambda m: "Núcleo robusto (recomendado)" if m == "nucleo_robusto" else "Completo (todos ROBUSTO+MODERADO)",
    horizontal=True,
)

linha_met = met[(met["ALVO"] == alvo_sel) & (met["MODELO"] == modelo_sel)]
if linha_met.empty:
    bloco_interpretativo(
        f"O modelo '{modelo_sel}' não pôde ser ajustado para {rotulo(alvo_sel)}: a amostra completa é menor "
        "que o número de preditores (matriz singular). Ver metodologia do script 02."
    )
else:
    m = linha_met.iloc[0]
    if modelo_sel == "completo" or m["RAZAO_N_PREDITORES"] < 5:
        bloco_interpretativo(
            f"N={int(m['N'])} para {int(m['N_PREDITORES'])} preditores (razão N/preditores = "
            f"{m['RAZAO_N_PREDITORES']:.1f}). Abaixo de ~5, trate este modelo como **exploratório**, não conclusivo."
        )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("N", int(m["N"]))
    c2.metric("R²", f"{m['R2']:.2f}")
    c3.metric("R² ajustado", f"{m['R2_AJUSTADO']:.2f}")
    c4.metric("VIF máximo", f"{m['VIF_MAXIMO']:.2f}", help="Variance Inflation Factor — acima de ~5 sugere multicolinearidade relevante.")

    coef_sel = coef[(coef["ALVO"] == alvo_sel) & (coef["MODELO"] == modelo_sel)].copy()
    coef_sel["Parâmetro"] = coef_sel["VARIAVEL"].apply(rotulo)
    coef_sel["Significativo"] = coef_sel["P_VALOR"] < 0.05

    tabela_coef = coef_sel[["Parâmetro", "COEFICIENTE", "COEFICIENTE_PADRONIZADO", "P_VALOR", "VIF", "Significativo"]].rename(
        columns={"COEFICIENTE": "Coeficiente", "COEFICIENTE_PADRONIZADO": "Coef. padronizado (β)", "P_VALOR": "p-valor"}
    )
    st.dataframe(
        tabela_coef.style.format({"Coeficiente": "{:.3f}", "Coef. padronizado (β)": "{:.3f}", "p-valor": "{:.4f}", "VIF": "{:.2f}"}),
        use_container_width=True,
        hide_index=True,
    )

    coef_ordenado = coef_sel.sort_values("COEFICIENTE_PADRONIZADO")
    cores_barras = [CORES["petroleo"] if sig else CORES["texto_mudo"] for sig in coef_ordenado["Significativo"]]
    fig_bar = go.Figure(
        go.Bar(
            x=coef_ordenado["COEFICIENTE_PADRONIZADO"],
            y=coef_ordenado["Parâmetro"],
            orientation="h",
            marker_color=cores_barras,
            text=[f"p={p:.3f}" for p in coef_ordenado["P_VALOR"]],
            textposition="outside",
        )
    )
    fig_bar.add_vline(x=0, line_color=CORES["grade"])
    layout_editorial(
        fig_bar,
        title=f"Coeficientes padronizados (β) — {rotulo(alvo_sel)} ~ {modelo_sel}",
        xaxis_title="β padronizado",
        height=120 + 45 * len(coef_ordenado),
        margin=dict(l=10, r=60, t=40, b=10),
    )
    st.plotly_chart(fig_bar, use_container_width=True)
    legenda_grafico(
        "Barras em petróleo escuro: p < 0,05 (significativo). Barras em cinza: não significativo. "
        "O β padronizado permite comparar a magnitude do efeito entre parâmetros medidos em unidades diferentes."
    )

st.divider()

# ======================================================== pca/clustering ====

secao("04", "PCA e Clustering")
st.caption("Esta seção sempre usa a bacia inteira, independente do recorte espacial escolhido acima.")

scores, var, loadings, perfil = carregar_pca(sufixo="_sem_outlier")
sil = carregar_silhouette(sufixo="_sem_outlier")
melhor_k = int(sil.loc[sil["SILHOUETTE"].idxmax(), "K"])
melhor_sil = float(sil["SILHOUETTE"].max())
n_pca = scores.shape[0]
var_pc1 = float(var.loc[var["COMPONENTE"] == "PC1", "VARIANCIA_EXPLICADA_PCT"].iloc[0])
var_pc2 = float(var.loc[var["COMPONENTE"] == "PC2", "VARIANCIA_EXPLICADA_PCT"].iloc[0])

bloco_interpretativo(
    "**Conclusão: não há estrutura de cluster forte nestes dados — e este é um resultado válido, não uma "
    "lacuna da análise.**\n\n"
    f"- PCA/clustering usam só os {len(principal)} parâmetros ROBUSTO+MODERADO, em complete-case (sem "
    f"imputação), o que restringe a análise às **N={n_pca}** amostras com todos os parâmetros preenchidos "
    "simultaneamente.\n"
    f"- As duas primeiras componentes explicam apenas **{var_pc1 + var_pc2:.0f}%** da variância total "
    f"(PC1={var_pc1:.1f}%, PC2={var_pc2:.1f}%) — não há um eixo dominante de variação.\n"
    f"- O melhor agrupamento testado (k={melhor_k}) tem silhouette = **{melhor_sil:.2f}**; valores abaixo de "
    "0,25 geralmente indicam ausência de estrutura de cluster real (a referência usual considera > 0,5 "
    "como estrutura forte).\n"
    f"- N={n_pca} para {len(principal)} variáveis é pequeno frente à regra prática de N ≥ 5× o número de "
    f"variáveis (≥ {5 * len(principal)}) — mesmo que houvesse estrutura, esta amostra não teria poder "
    "estatístico para detectá-la com confiança.\n\n"
    "Esta execução já exclui a amostra `ITA-0220`, um outlier extremo de condutividade/cloreto que "
    "dominava sozinho um cluster isolado na primeira tentativa — mesmo removendo-a, nenhuma segmentação "
    "natural emergiu (ver metodologia do script 03)."
)

col_bi, col_sil = st.columns([3, 2])

with col_bi:
    fig_bi = go.Figure()
    for i, c in enumerate(sorted(scores["CLUSTER"].unique())):
        sub = scores[scores["CLUSTER"] == c]
        fig_bi.add_trace(
            go.Scatter(
                x=sub["PC1"], y=sub["PC2"], mode="markers", name=f"cluster {c} (N={len(sub)})",
                marker=dict(color=CORES_CLUSTER[i % len(CORES_CLUSTER)], size=10, opacity=0.85, line=dict(width=1, color="white")),
            )
        )
    layout_editorial(
        fig_bi,
        title=f"PCA biplot — PC1 × PC2 (k={melhor_k}, N={n_pca})",
        xaxis_title=f"PC1 ({var_pc1:.1f}% da variância)",
        yaxis_title=f"PC2 ({var_pc2:.1f}% da variância)",
        height=460,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig_bi, use_container_width=True)

with col_sil:
    fig_sil = go.Figure(
        go.Scatter(x=sil["K"], y=sil["SILHOUETTE"], mode="lines+markers", line=dict(color=CORES["petroleo"], width=2), marker=dict(size=9))
    )
    fig_sil.add_hline(y=0.25, line_dash="dot", line_color=CORES["texto_mudo"], annotation_text="~sem estrutura real")
    layout_editorial(
        fig_sil,
        title="Silhouette por número de clusters (k)",
        xaxis_title="k", yaxis_title="Silhouette score",
        height=460, margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig_sil, use_container_width=True)

legenda_grafico(
    "O biplot usa tons de cinza/verde-petróleo (não uma paleta colorida) porque o próprio achado é a "
    "ausência de separação — uma paleta vibrante sugeriria uma segmentação mais forte do que a que existe."
)
