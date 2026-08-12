"""
Paleta visual do projeto -- estilo editorial: fundo creme, verde-petroleo como
cor de destaque unica, texto cinza-chumbo. As 3 cores de status (robusto/
moderado/pouco) sao reservadas EXCLUSIVAMENTE para a classificacao de
confiabilidade dos parametros -- nunca reaproveitadas para outra coisa (series
de grafico, clusters, etc.), para que a cor sempre signifique a mesma coisa em
qualquer pagina do dashboard.

Usado por scripts/_lib_analise.py e pelas paginas do dashboard (pages/).
"""

CORES = {
    # neutros -- fundo creme quente + texto cinza-chumbo (estilo editorial)
    "texto_primario": "#2A2A28",
    "texto_secundario": "#595652",
    "texto_mudo": "#8c8880",
    "grade": "#E4DFD2",
    "fundo": "#F5F3EE",
    "fundo_alt": "#ECE6D8",
    # azul-petroleo: cor de destaque UNICA para dados de agua (series, marcadores, barras)
    "petroleo": "#1f6f78",
    "petroleo_claro": "#6fa8ae",
    "petroleo_escuro": "#12454b",
    "petroleo_fundo": "#E7EEEA",
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

# variacoes tonais do verde-petroleo, para diferenciar ate 5 series no mesmo
# grafico (parametros padronizados, corpos d'agua, etc.) sem introduzir cores
# fora da paleta -- do mais escuro ao mais claro
CORES_SEQUENCIA = [CORES["petroleo_escuro"], CORES["petroleo"], "#4a8f96", CORES["petroleo_claro"], "#a9c9cc"]

# diverging para o heatmap de correlacao (r=-1 .. 0 .. +1): petroleo <-> cinza-escuro,
# deliberadamente SEM usar vermelho/amarelo aqui -- essas cores ja tem significado
# fixo (status BAIXO/MODERADO) e nao devem aparecer com outro sentido no mesmo dashboard
CORES["cinza_escuro"] = "#3d3d3d"
DIVERGENTE_CORRELACAO = [CORES["petroleo"], CORES["fundo_alt"], CORES["cinza_escuro"]]

# cor unica para linhas de tendencia/regressao em qualquer grafico (scatter, barras
# de referencia) -- reaproveita o polo escuro do diverging acima, pelo mesmo motivo:
# nao usar vermelho/amarelo (reservados para status) fora do seu contexto
CORES["linha_tendencia"] = CORES["cinza_escuro"]

# escala neutra para identificar clusters (ate 6), preferindo tons de cinza/petroleo
# a uma paleta "festiva" -- coerente com o achado de que o clustering nao encontrou
# estrutura forte (ver pagina 3)
CORES_CLUSTER = ["#1f6f78", "#8c8c8c", "#6fa8ae", "#404040", "#a9c9cc", "#c2c2c2"]
