"""
Nomes legiveis + unidade de medida para os parametros fisico-quimicos do
monitoramento do rio Itapecuru. Usar SEMPRE rotulo(coluna) em titulos, eixos
e legendas de graficos -- nunca o nome literal da coluna (ex: "CLORETO_TOTAL").

ATENCAO - unidades assumidas (mg/L) por falta de confirmacao do usuario,
marcadas abaixo com "# a confirmar": SOLIDOS_SUSPENSOS, ORTOFOSFATO,
FOSFORO_TOTAL, NITROGENIO_AMONIACAL. Validar a unidade real (e o metodo/
referencia de analise) antes de publicar qualquer conclusao baseada nelas.
"""

NOMES_UNIDADES = {
    "PROFUNDIDADE": "Profundidade (m)",
    "VAZAO": "Vazão (m³/s)",
    "TEMPERATURA_AR": "Temperatura do Ar (°C)",
    "TEMPERATURA_AGUA": "Temperatura da Água (°C)",
    "PH": "pH",
    "OXIGENIO_DISSOLVIDO": "Oxigênio Dissolvido (mg/L O₂)",
    "COND_ELETRICA_ESPECIFICA": "Condutividade Elétrica Específica (µS/cm a 25°C)",
    "TURBIDEZ": "Turbidez (NTU)",
    "SALINIDADE": "Salinidade (‰)",
    "ALCALINIDADE": "Alcalinidade (mg/L)",
    "TRANSPARENCIA_AGUA": "Transparência da Água (m)",
    "SOLIDOS_DISSOLVIDOS": "Sólidos Dissolvidos (mg/L)",
    "SOLIDOS_SUSPENSOS": "Sólidos Suspensos (mg/L)",  # a confirmar
    "CLORETO_TOTAL": "Cloreto Total (mg/L de Cl)",
    "FLUORETO_TOTAL": "Fluoreto Total (mg/L de F)",
    "BROMETO_TOTAL": "Brometo Total (mg/L de Br)",
    "NITRATO": "Nitrato (mg/L de N)",
    "NITRITO": "Nitrito Total (mg/L de N)",
    "SULFATO": "Sulfato (mg/L de S)",
    "FOSFATO_TOTAL": "Fosfato Total (mg/L de P)",
    "ORTOFOSFATO": "Ortofosfato (mg/L de P)",  # a confirmar
    "FOSFORO_TOTAL": "Fósforo Total (mg/L de P)",  # a confirmar
    "NITROGENIO_AMONIACAL": "Nitrogênio Amoniacal (mg/L de N)",  # a confirmar
}


def rotulo(param: str) -> str:
    """Nome legivel + unidade para uso em graficos. Cai no nome bruto da
    coluna se ela ainda nao estiver mapeada, para nao quebrar graficos ao
    adicionar novas colunas."""
    return NOMES_UNIDADES.get(param, param)
