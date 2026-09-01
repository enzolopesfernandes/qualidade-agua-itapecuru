"""
Paleta visual do projeto -- estilo cientifico: fundo da PAGINA em creme quente,
mas o fundo do PLOT em si (area onde os dados sao desenhados) sempre branco
puro (#FFFFFF), para o grafico contrastar com a pagina em vez de se misturar
nela. Cores de dado sao solidas e fortes (paleta qualitativa inspirada em
Okabe-Ito/ColorBrewer, segura para daltonismo) -- nunca variacao de opacidade
para diferenciar categoria/serie; se for preciso diferenciar pontos dentro da
mesma serie, usar forma do marcador, nao opacidade.

As 3 cores de status (robusto/moderado/pouco) sao reservadas EXCLUSIVAMENTE
para a classificacao de confiabilidade dos parametros (badges) -- nunca
reaproveitadas para series de grafico/clusters, para que a cor sempre
signifique a mesma coisa em qualquer pagina do dashboard.

Usado por scripts/_lib_analise.py, scripts/02 e 03, e pelas paginas do
dashboard (pages/).
"""

CORES = {
    # neutros -- fundo da PAGINA (creme) + texto cinza-chumbo
    "texto_primario": "#2A2A28",
    "texto_secundario": "#595652",
    "texto_mudo": "#8c8880",
    "grade": "#E4DFD2",  # divisorias entre secoes da pagina (fora dos graficos)
    "fundo": "#F5F3EE",  # fundo da PAGINA -- NUNCA usar dentro da area de um grafico
    "fundo_alt": "#ECE6D8",
    # fundo do PLOT em si -- branco puro, sempre, em todo grafico (plotly e matplotlib)
    "fundo_grafico": "#FFFFFF",
    "grade_grafico": "#E2E2E2",  # gridlines finas dentro dos graficos (contraste sutil no branco)
    # verde principal -- cor de destaque UNICA para series/marcadores/barras de dado
    "petroleo": "#1B7837",
    "petroleo_escuro": "#0B4A1E",  # variante escura p/ bordas/enfase -- NAO usar para diferenciar categoria
    # status -- uso exclusivo para ROBUSTO / MODERADO / POUCO (badges com fundo solido)
    "robusto": "#1E7D34",
    "moderado": "#B5790A",
    "pouco": "#C23B3B",
}

# mapeamento direto categoria -> cor solida do badge (fundo solido + texto branco)
# chave interna dos dados continua "BAIXO" (script 01 / CSVs) -- so o ROTULO exibido
# na tela virou "Pouco"; ver ROTULOS_CATEGORIA abaixo.
CORES_STATUS = {
    "ROBUSTO": CORES["robusto"],
    "MODERADO": CORES["moderado"],
    "BAIXO": CORES["pouco"],
}
ROTULOS_CATEGORIA = {
    "ROBUSTO": "Robusto",
    "MODERADO": "Moderado",
    "BAIXO": "Pouco",
}

# paleta qualitativa (inspirada em Okabe-Ito, segura para daltonismo) para ate 7
# series/categorias no mesmo grafico (parametros sobrepostos, corpos d'agua,
# clusters de PCA) -- cores solidas e distintas por HUE, nunca por opacidade/
# tom da mesma cor. Verde principal sempre primeiro (mesma cor de CORES["petroleo"]).
CORES_SEQUENCIA = ["#1B7837", "#D55E00", "#0072B2", "#CC79A7", "#E69F00", "#000000", "#56B4E9"]

# clusters de PCA usam a mesma paleta qualitativa (legibilidade da categoria
# prioritaria sobre estetica -- ver notas de interpretacao na pagina 3 para o
# porque de os clusters nao indicarem estrutura forte, independente da cor usada)
CORES_CLUSTER = CORES_SEQUENCIA

# diverging cientifico padrao ColorBrewer "PRGn" (7 classes, estojos oficiais)
# para o heatmap de correlacao (r=-1 .. 0 .. +1) -- unica excecao a "cor
# solida unica", pois e uma escala continua matematicamente necessaria.
# Roxo=negativo, verde=positivo -- o polo +1 e o mesmo verde principal do
# projeto (#1B7837 == CORES["petroleo"], nao e coincidencia: e o proprio tom
# de verde que a escala PRGn usa). matplotlib tem o cmap "PRGn" embutido com
# os mesmos estojos -- usar a string "PRGn" direto la, esta lista e so para
# plotly (que pede [posicao, cor]).
DIVERGENTE_CORRELACAO = [
    [0 / 6, "#762A83"],
    [1 / 6, "#AF8DC3"],
    [2 / 6, "#E7D4E8"],
    [3 / 6, "#F7F7F7"],
    [4 / 6, "#D9F0D3"],
    [5 / 6, "#7FBF7B"],
    [6 / 6, CORES["petroleo"]],
]

# cor unica para linhas de tendencia/ajuste (OLS, medias, referencias) em
# qualquer grafico -- preto solido, contraste neutro que nao compete com as
# cores categoricas de CORES_SEQUENCIA
CORES["linha_tendencia"] = "#000000"

# vermelho reservado EXCLUSIVAMENTE para as linhas de limite legal da Resolucao
# CONAMA 357/2005 (add_hline/add_vline tracejado, ver config/conama.py +
# dashboard_common.linhas_referencia_conama). Papel proprio -- nao e serie de
# dado nem badge de confiabilidade -- por isso um tom deliberadamente distinto
# do vermelho "pouco" (#C23B3B) dos badges: aqui a linha significa sempre
# "limite regulatorio", em qualquer pagina.
CORES["linha_conama"] = "#D1332E"
