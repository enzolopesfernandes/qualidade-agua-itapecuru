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
from streamlit_folium import st_folium

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "scripts"))

from config.conama import descricao_limite_conama  # noqa: E402
from config.estilo import CORES, CORES_CLUSTER, DIVERGENTE_CORRELACAO  # noqa: E402
from config.nomes_unidades import rotulo  # noqa: E402
from dashboard_common import (  # noqa: E402
    ICONE_PAGINA,
    TITULO_TRABALHO,
    badge_confiabilidade,
    bloco_interpretativo,
    carregar_dados,
    carregar_grupos_robusto_moderado_baixo,
    carregar_pca,
    carregar_resumo_cobertura,
    carregar_silhouette,
    carregar_tipologia_pontos,
    construir_mapa_pontos,
    explicacao_zscore,
    layout_editorial,
    legenda_grafico,
    limites_iqr_expandido,
    linhas_referencia_conama,
    render_header,
    secao,
)
from _lib_analise import calcular_pca_clustering_live  # noqa: E402

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

st.markdown("**Recorte espacial** (aplica-se a toda a página, seções 01 a 03 — a seção 04 é sempre bacia inteira)")
st.caption(
    "Correlação (01) e Dispersão (02) recalculam direto sobre as amostras do recorte. PCA/Clustering (03) "
    "também recalcula ao vivo quando um corpo d'água é escolhido — mas só é exibido se o N do recorte for "
    "suficiente para o método (ver nota na seção); com N insuficiente, mostramos apenas descritivas, "
    "histogramas e correlação, com um aviso explícito."
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

usa_bacia_inteira = nivel_recorte3 == "Toda a bacia"

if usa_bacia_inteira:
    st.caption(f"Recorte atual: **{descricao_recorte3}** — N = {len(df_recorte)} amostras válidas.")
else:
    st.metric(f"N — {descricao_recorte3}", len(df_recorte), help="Amostras válidas neste recorte, de um total de " f"{len(df_valido)} na bacia inteira.")
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
    "positiva (tom escuro de verde) ou negativa (tom escuro de roxo) — e células claras/brancas no meio "
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
        colorscale=DIVERGENTE_CORRELACAO,
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

mostrar_tudo_disp = st.checkbox(
    "Mostrar todos os pontos (incluindo outliers)",
    value=False,
    key="disp_mostrar_tudo",
    help="Por padrão, o eixo de cada gráfico é ajustado para destacar a nuvem principal de pontos "
    "(intervalo interquartil expandido). Ative para voltar ao range completo dos dados.",
)

outros_parametros = [p for p in todos if p != parametro_disp]
cols_scatter = st.columns(3)
n_ocultos = 0
total_fora_da_vista = 0
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
    fig_sc.update_traces(marker=dict(color=CORES["petroleo"], size=6), selector=dict(mode="markers"))
    fig_sc.update_traces(line=dict(color=CORES["linha_tendencia"], width=2), selector=dict(mode="lines"))
    linhas_referencia_conama(fig_sc, parametro_disp, eixo="y", mostrar_anotacao=False)

    n_fora_par = 0
    if not mostrar_tudo_disp:
        x_ini, x_fim = limites_iqr_expandido(dados[outro])
        y_ini, y_fim = limites_iqr_expandido(dados[parametro_disp])
        fora = dados[
            (dados[outro] < x_ini) | (dados[outro] > x_fim)
            | (dados[parametro_disp] < y_ini) | (dados[parametro_disp] > y_fim)
        ]
        n_fora_par = len(fora)
        if n_fora_par:
            total_fora_da_vista += n_fora_par
            fig_sc.update_xaxes(range=[x_ini, x_fim])
            fig_sc.update_yaxes(range=[y_ini, y_fim])

    layout_editorial(fig_sc, height=330, margin=dict(l=10, r=10, t=45, b=10), title_font_size=12)
    with cols_scatter[(i - n_ocultos) % 3]:
        st.plotly_chart(fig_sc, use_container_width=True)
        if n_fora_par:
            st.caption(f"Eixo ajustado; {n_fora_par} ponto(s) fora do intervalo não visível(is) aqui.")

nota_zoom = ""
if not mostrar_tudo_disp and total_fora_da_vista:
    nota_zoom = (
        f" Eixos ajustados para destacar a relação entre as variáveis (intervalo interquartil expandido); "
        f"{total_fora_da_vista} ponto(s), somados em todos os gráficos acima, ficam fora do intervalo "
        "visível e não aparecem nesta visualização — ative \"Mostrar todos os pontos\" para vê-los."
    )
_desc_conama_disp = descricao_limite_conama(parametro_disp)
nota_conama_disp = (
    f" Linha vermelha tracejada horizontal: {_desc_conama_disp} para {rotulo(parametro_disp)} (eixo Y)."
    if _desc_conama_disp
    else ""
)
legenda_grafico(
    f"{len(outros_parametros) - n_ocultos} de {len(outros_parametros)} pares exibidos "
    f"(N ≥ 3 amostras em comum)." + (f" {n_ocultos} par(es) ocultos por N < 3." if n_ocultos else "")
    + f" Recorte: {descricao_recorte3}." + nota_zoom + nota_conama_disp
)

st.divider()

# ======================================================== pca/clustering ====

secao("03", "PCA e Clustering")

pca_disponivel = True

if usa_bacia_inteira:
    st.caption("Bacia inteira: usa o PCA/clustering pré-computado pelo script 03 (exclui o outlier ITA-0220).")
    scores, var, loadings, perfil = carregar_pca(sufixo="_sem_outlier")
    sil = carregar_silhouette(sufixo="_sem_outlier")
    melhor_k = int(sil.loc[sil["SILHOUETTE"].idxmax(), "K"])
    melhor_sil = float(sil["SILHOUETTE"].max())
    n_pca = scores.shape[0]
    var_pc1 = float(var.loc[var["COMPONENTE"] == "PC1", "VARIANCIA_EXPLICADA_PCT"].iloc[0])
    var_pc2 = float(var.loc[var["COMPONENTE"] == "PC2", "VARIANCIA_EXPLICADA_PCT"].iloc[0])
    variaveis_pca_ativas = principal
else:
    st.caption(
        f"Recorte: {descricao_recorte3} (N={len(df_recorte)}) — PCA/clustering recalculado ao vivo, restrito "
        f"aos {len(robusto)} parâmetros ROBUSTO (mesma redução usada na seção 04, Tipologia dos pontos, para "
        "preservar N com um corpo d'água menor)."
    )
    resultado_pca_live = calcular_pca_clustering_live(df_recorte, robusto)
    if resultado_pca_live is None:
        pca_disponivel = False
        n_disp_pca = df_recorte[robusto].dropna().shape[0]
        bloco_interpretativo(
            f"**N insuficiente para PCA/clustering neste recorte** (N={n_disp_pca} amostras completas para "
            f"{len(robusto)} parâmetros ROBUSTO — precisaria exceder o número de variáveis). Use as seções "
            "01 (Correlação) e 02 (Dispersão) acima como alternativa exploratória."
        )
    else:
        scores = resultado_pca_live["scores"]
        var = resultado_pca_live["var"]
        sil = resultado_pca_live["silhouette"]
        perfil = resultado_pca_live["perfil"]
        melhor_k = resultado_pca_live["melhor_k"]
        melhor_sil = float(sil["SILHOUETTE"].max())
        n_pca = resultado_pca_live["n"]
        var_pc1 = float(var.loc[var["COMPONENTE"] == "PC1", "VARIANCIA_EXPLICADA_PCT"].iloc[0])
        var_pc2 = float(var.loc[var["COMPONENTE"] == "PC2", "VARIANCIA_EXPLICADA_PCT"].iloc[0])
        variaveis_pca_ativas = robusto

if pca_disponivel:
    if usa_bacia_inteira:
        bloco_interpretativo(
            "**Conclusão: não há estrutura de cluster forte nestes dados — e este é um resultado válido, não uma "
            "lacuna da análise.**\n\n"
            f"- PCA/clustering usam só os {len(variaveis_pca_ativas)} parâmetros ROBUSTO+MODERADO, em complete-case (sem "
            f"imputação), o que restringe a análise às **N={n_pca}** amostras com todos os parâmetros preenchidos "
            "simultaneamente.\n"
            f"- As duas primeiras componentes explicam apenas **{var_pc1 + var_pc2:.0f}%** da variância total "
            f"(PC1={var_pc1:.1f}%, PC2={var_pc2:.1f}%) — não há um eixo dominante de variação.\n"
            f"- O melhor agrupamento testado (k={melhor_k}) tem silhouette = **{melhor_sil:.2f}**; valores abaixo de "
            "0,25 geralmente indicam ausência de estrutura de cluster real (a referência usual considera > 0,5 "
            "como estrutura forte).\n"
            f"- N={n_pca} para {len(variaveis_pca_ativas)} variáveis é pequeno frente à regra prática de N ≥ 5× o número de "
            f"variáveis (≥ {5 * len(variaveis_pca_ativas)}) — mesmo que houvesse estrutura, esta amostra não teria poder "
            "estatístico para detectá-la com confiança.\n\n"
            "Esta execução já exclui a amostra `ITA-0220`, um outlier extremo de condutividade/cloreto que "
            "dominava sozinho um cluster isolado na primeira tentativa — mesmo removendo-a, nenhuma segmentação "
            "natural emergiu (ver metodologia do script 03)."
        )
    else:
        razao_pca = n_pca / len(variaveis_pca_ativas)
        aviso_exploratorio = (
            f" Razão N/variáveis = {razao_pca:.1f}×, abaixo da referência de ≥5× — tratar como **exploratório**."
            if razao_pca < 5
            else f" Razão N/variáveis = {razao_pca:.1f}×."
        )
        bloco_interpretativo(
            f"PCA/clustering restrito aos {len(variaveis_pca_ativas)} parâmetros ROBUSTO. N={n_pca}.{aviso_exploratorio}\n\n"
            f"Melhor agrupamento (k={melhor_k}) tem silhouette = **{melhor_sil:.2f}**; PC1+PC2 explicam "
            f"**{var_pc1 + var_pc2:.0f}%** da variância entre as amostras deste recorte."
        )

    fig_bi = go.Figure()
    for i, c in enumerate(sorted(scores["CLUSTER"].unique())):
        sub = scores[scores["CLUSTER"] == c]
        fig_bi.add_trace(
            go.Scatter(
                x=sub["PC1"], y=sub["PC2"], mode="markers", name=f"cluster {c} (N={len(sub)})",
                marker=dict(color=CORES_CLUSTER[i % len(CORES_CLUSTER)], size=10, line=dict(width=1, color="white")),
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

    if usa_bacia_inteira:
        legenda_grafico(
            "Cada cor identifica um cluster testado — mas o achado central desta seção é justamente a "
            "**ausência de separação real** entre eles (silhouette baixo, variância pouco concentrada em PC1/PC2): "
            "cores distintas aqui marcam grupos formalmente atribuídos pelo algoritmo, não uma segmentação "
            "biologicamente/quimicamente evidente na nuvem de pontos."
        )
    else:
        legenda_grafico(f"PCA/clustering ao vivo. Recorte: {descricao_recorte3} (N={n_pca}).")

st.divider()

# ============================================= tipologia dos pontos ====

secao("04", "Tipologia dos pontos de coleta")

bloco_interpretativo(
    "Em vez de perguntar se dois parâmetros variam juntos, aqui perguntamos **quais pontos de coleta têm "
    "um comportamento parecido entre si**, comparando o perfil típico de cada um ao longo de todo o "
    "período monitorado. Isso pode revelar grupos de pontos com características semelhantes (por exemplo, "
    "mais turvos ou mais limpos), possivelmente ligados à sua localização na bacia."
)

medianas_tip, scores_tip, var_tip, sil_tip, perfil_tip = carregar_tipologia_pontos()
variaveis_tip = [c for c in perfil_tip.columns if c not in ("CLUSTER", "N_PONTOS")]
n_pontos_total = medianas_tip.shape[0]
n_pontos_pca = scores_tip.shape[0]
melhor_k_tip = int(sil_tip.loc[sil_tip["SILHOUETTE"].idxmax(), "K"])
melhor_sil_tip = float(sil_tip["SILHOUETTE"].max())
var_pc1_tip = float(var_tip.loc[var_tip["COMPONENTE"] == "PC1", "VARIANCIA_EXPLICADA_PCT"].iloc[0])
var_pc2_tip = float(var_tip.loc[var_tip["COMPONENTE"] == "PC2", "VARIANCIA_EXPLICADA_PCT"].iloc[0])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Pontos RNQA (total)", n_pontos_total)
c2.metric("Pontos usados no PCA", n_pontos_pca)
c3.metric("Clusters (k escolhido)", melhor_k_tip)
c4.metric("Silhouette", f"{melhor_sil_tip:.2f}")

bloco_interpretativo(
    f"PCA/clustering usa só os **{len(variaveis_tip)} parâmetros ROBUSTO** (não ROBUSTO+MODERADO): "
    f"exigindo mediana preenchida nos 14 parâmetros ROBUSTO+MODERADO, a amostra cairia para 20 dos "
    f"{n_pontos_total} pontos; restrito aos ROBUSTO, {n_pontos_pca} dos {n_pontos_total} ficam "
    "disponíveis (o único de fora tem apenas 2 amostras válidas em todo o histórico, faltando "
    f"salinidade). Mesmo assim, N={n_pontos_pca} para {len(variaveis_tip)} variáveis "
    f"(razão {n_pontos_pca / len(variaveis_tip):.1f}×) fica abaixo da referência de ≥5× — tratar como "
    "**exploratório**, igual ao PCA/clustering das seções acima."
)

if melhor_sil_tip >= 0.5:
    forca_tip = "uma estrutura de cluster **forte**"
elif melhor_sil_tip >= 0.25:
    forca_tip = "uma estrutura de cluster **moderada** — nem forte, nem ausente"
else:
    forca_tip = "**nenhuma estrutura de cluster relevante** entre os pontos — resultado válido, não uma lacuna da análise"

bloco_interpretativo(
    f"Os {n_pontos_pca} pontos formam {forca_tip} (k={melhor_k_tip}, silhouette={melhor_sil_tip:.2f}). "
    f"PC1+PC2 explicam {var_pc1_tip + var_pc2_tip:.0f}% da variância entre pontos."
)

st.caption(
    "A coluna **Perfil** da tabela abaixo é lida em **Z-Score**: para cada cluster, mede quantos "
    "desvios-padrão o valor típico de um parâmetro está da média entre os clusters — os dois parâmetros "
    "com |z| maior viram a descrição \"acima/abaixo da média\"."
)
explicacao_zscore()

# perfil textual de cada cluster: parametros mais destoantes da media geral entre clusters
medias_gerais_tip = perfil_tip[variaveis_tip].mean()
desvios_tip = perfil_tip[variaveis_tip].std().replace(0, np.nan)
linhas_resumo_tip = []
for _, linha in perfil_tip.iterrows():
    z = (linha[variaveis_tip] - medias_gerais_tip) / desvios_tip
    destaques = z.dropna().abs().sort_values(ascending=False).head(2).index.tolist()
    partes = [f"{rotulo(v)} {'acima' if z[v] > 0 else 'abaixo'} da média" for v in destaques]
    pontos_do_cluster = scores_tip.loc[scores_tip["CLUSTER"] == linha["CLUSTER"], "RNQA"].tolist()
    linhas_resumo_tip.append(
        {
            "Cluster": int(linha["CLUSTER"]),
            "N pontos": int(linha["N_PONTOS"]),
            "Perfil (vs. média geral entre clusters)": "; ".join(partes) if partes else "sem diferença marcante",
            "Pontos": ", ".join(pontos_do_cluster),
        }
    )
st.dataframe(pd.DataFrame(linhas_resumo_tip), use_container_width=True, hide_index=True)

clusters_ordenados_tip = sorted(scores_tip["CLUSTER"].unique())
mapa_cor_cluster_tip = {c: CORES_CLUSTER[i % len(CORES_CLUSTER)] for i, c in enumerate(clusters_ordenados_tip)}

col_bi_tip, col_mapa_tip = st.columns([3, 2])

with col_bi_tip:
    fig_tip = go.Figure()
    for c in clusters_ordenados_tip:
        sub = scores_tip[scores_tip["CLUSTER"] == c]
        fig_tip.add_trace(
            go.Scatter(
                x=sub["PC1"], y=sub["PC2"], mode="markers+text", text=sub["RNQA"], textposition="top center",
                textfont=dict(size=8), name=f"cluster {c} (N={len(sub)})",
                marker=dict(color=mapa_cor_cluster_tip[c], size=11, line=dict(width=1, color="white")),
            )
        )
    layout_editorial(
        fig_tip,
        title=f"Tipologia dos pontos — PCA biplot (k={melhor_k_tip}, N={n_pontos_pca} pontos)",
        xaxis_title=f"PC1 ({var_pc1_tip:.1f}% da variância)",
        yaxis_title=f"PC2 ({var_pc2_tip:.1f}% da variância)",
        height=480,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig_tip, use_container_width=True)

with col_mapa_tip:
    st.markdown("**Mapa — pontos coloridos por cluster**")
    cores_por_rnqa_tip = {row["RNQA"]: mapa_cor_cluster_tip[row["CLUSTER"]] for _, row in scores_tip.iterrows()}
    pontos_mapa_tip = medianas_tip.merge(scores_tip[["RNQA", "CLUSTER"]], on="RNQA", how="left")
    pontos_mapa_tip["CLUSTER"] = pontos_mapa_tip["CLUSTER"].astype("Int64")
    mapa_tip = construir_mapa_pontos(
        pontos_mapa_tip,
        cor_por_rnqa=cores_por_rnqa_tip,
        cor_padrao=CORES["texto_mudo"],
        campos_popup=[("Cluster", "CLUSTER"), ("N amostras (histórico)", "N_AMOSTRAS")],
    )
    st_folium(mapa_tip, width=None, height=480, returned_objects=[])
    n_sem_cluster_tip = int(pontos_mapa_tip["CLUSTER"].isna().sum())
    if n_sem_cluster_tip:
        st.caption(f"{n_sem_cluster_tip} ponto(s) em cinza: dado insuficiente para entrar no PCA/clustering.")

legenda_grafico(
    "Rótulos no biplot são o código RNQA de cada ponto — a mesma cor identifica o mesmo cluster no "
    "biplot e no mapa. Padrão espacial: veja se os clusters formam agrupamentos geográficos (por trecho "
    "do rio/corpo d'água) ou se ficam dispersos pela bacia."
)
