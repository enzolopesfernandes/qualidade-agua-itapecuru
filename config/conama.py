"""
Limites da Resolucao CONAMA no 357/2005 -- aguas doces, Classe 2 (enquadramento
assumido para a bacia do Itapecuru na ausencia de portaria de enquadramento
especifica; a Classe 2 e a referencia usual para corpos d'agua destinados ao
abastecimento apos tratamento convencional, recreacao de contato primario,
irrigacao de hortalicas e protecao de comunidades aquaticas).

DICIONARIO CENTRALIZADO parametro -> limite legal, reutilizado por todas as
paginas do dashboard que desenham a linha de referencia (via
dashboard_common.linhas_referencia_conama() para figuras Plotly).

Cada entrada tem:
    tipo   : "max"  -> valor maximo permitido (linha no teto)
             "min"  -> valor minimo permitido (linha no piso)
             "faixa"-> intervalo permitido (duas linhas)
    valor  : float            (tipo "max" / "min")
    min/max: float            (tipo "faixa")
    unidade: str curta para o rotulo da linha
    nota   : ressalva quando o limite depende de condicao nao modelada aqui

ATENCAO -- ressalvas que o grafico NAO expressa sozinho:
  * FOSFORO_TOTAL: 0,1 mg/L vale para ambiente lotico (rios) e tributarios de
    ambiente intermediario; ambiente lentico (lagos/lagoas) = 0,030 mg/L,
    intermediario = 0,050 mg/L. A bacia e predominantemente lotica -> 0,1.
  * NITROGENIO_AMONIACAL: o limite varia com o pH da amostra (3,7 mg/L para
    pH <= 7,5; 2,0 para 7,5 < pH <= 8,0; 1,0 para 8,0 < pH <= 8,5; 0,5 para
    pH > 8,5). Adotamos 3,7 (faixa de pH mais comum na base, mediana ~7,0)
    como linha unica -- e o limite MENOS restritivo, entao amostras acima
    dele violam a resolucao em qualquer pH.
  * SOLIDOS_DISSOLVIDOS: 500 mg/L e o limite de solidos dissolvidos totais.
  * As unidades de FOSFORO_TOTAL / NITROGENIO_AMONIACAL no dataset ainda
    estao "a confirmar" (ver config/nomes_unidades.py) -- a comparacao com o
    limite so vale se a unidade real for mesmo mg/L de P / mg/L de N.

Parametros SEM limite numerico direto na CONAMA 357 para Classe 2 (nao entram
no dicionario, e a funcao de desenho simplesmente nao adiciona linha):
temperatura, condutividade, profundidade, vazao, transparencia, solidos
suspensos, alcalinidade, salinidade, brometo, ortofosfato, fosfato.
"""

from __future__ import annotations

LIMITES_CONAMA: dict[str, dict] = {
    "PH": {"tipo": "faixa", "min": 6.0, "max": 9.0, "unidade": ""},
    "OXIGENIO_DISSOLVIDO": {"tipo": "min", "valor": 5.0, "unidade": "mg/L O₂"},
    "TURBIDEZ": {"tipo": "max", "valor": 100.0, "unidade": "UNT"},
    "NITRATO": {"tipo": "max", "valor": 10.0, "unidade": "mg/L N"},
    "NITRITO": {"tipo": "max", "valor": 1.0, "unidade": "mg/L N"},
    "FOSFORO_TOTAL": {
        "tipo": "max",
        "valor": 0.1,
        "unidade": "mg/L P",
        "nota": "ambiente lótico (rios); lêntico = 0,030; intermediário = 0,050",
    },
    "NITROGENIO_AMONIACAL": {
        "tipo": "max",
        "valor": 3.7,
        "unidade": "mg/L N",
        "nota": "para pH ≤ 7,5; o limite cai até 0,5 mg/L conforme o pH sobe",
    },
    "CLORETO_TOTAL": {"tipo": "max", "valor": 250.0, "unidade": "mg/L Cl"},
    "FLUORETO_TOTAL": {"tipo": "max", "valor": 1.4, "unidade": "mg/L F"},
    "SULFATO": {"tipo": "max", "valor": 250.0, "unidade": "mg/L SO₄"},
    "SOLIDOS_DISSOLVIDOS": {"tipo": "max", "valor": 500.0, "unidade": "mg/L"},
}

# rotulo curto da fonte, usado nas anotacoes das linhas
FONTE_CONAMA = "CONAMA 357"


def tem_limite_conama(parametro: str) -> bool:
    """True se o parametro possui limite mapeado na Resolucao CONAMA 357/2005."""
    return parametro in LIMITES_CONAMA


def _fmt(valor: float) -> str:
    """Numero enxuto para o rotulo da linha (sem zeros a direita desnecessarios)."""
    return f"{valor:g}".replace(".", ",")


def descricao_limite_conama(parametro: str) -> str | None:
    """Frase curta do limite legal do parametro (para legendas/tooltips), ou
    None se nao houver limite mapeado."""
    lim = LIMITES_CONAMA.get(parametro)
    if lim is None:
        return None
    unidade = f" {lim['unidade']}" if lim.get("unidade") else ""
    if lim["tipo"] == "faixa":
        base = f"faixa permitida {_fmt(lim['min'])}–{_fmt(lim['max'])}{unidade}"
    elif lim["tipo"] == "min":
        base = f"mínimo {_fmt(lim['valor'])}{unidade}"
    else:
        base = f"máximo {_fmt(lim['valor'])}{unidade}"
    nota = f" ({lim['nota']})" if lim.get("nota") else ""
    return f"{FONTE_CONAMA} — {base}{nota}"


def valores_linha_conama(parametro: str) -> list[tuple[float, str]]:
    """Lista de (valor, rotulo) das linhas de referencia a desenhar para o
    parametro. Vazia quando nao ha limite mapeado.

    O rotulo ja vem pronto no formato "CONAMA 357: max 100 UNT" /
    "CONAMA 357: min 5 mg/L O2" / (para faixa) "CONAMA 357: min 6" + "max 9".
    """
    lim = LIMITES_CONAMA.get(parametro)
    if lim is None:
        return []
    unidade = f" {lim['unidade']}" if lim.get("unidade") else ""
    if lim["tipo"] == "faixa":
        return [
            (float(lim["min"]), f"{FONTE_CONAMA}: mín {_fmt(lim['min'])}{unidade}"),
            (float(lim["max"]), f"{FONTE_CONAMA}: máx {_fmt(lim['max'])}{unidade}"),
        ]
    if lim["tipo"] == "min":
        return [(float(lim["valor"]), f"{FONTE_CONAMA}: mín {_fmt(lim['valor'])}{unidade}")]
    return [(float(lim["valor"]), f"{FONTE_CONAMA}: máx {_fmt(lim['valor'])}{unidade}")]
