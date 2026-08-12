"""
Analise univariada + deteccao de outliers (IQR) - qualidade da agua do rio Itapecuru.

Fonte: aba DADOS_ANALISE (nivel de amostra) do arquivo "Dados tratados.xlsx".
Ver memoria do projeto para a justificativa de usar DADOS_ANALISE em vez de
Resumo_Descritiva.

Decisoes metodologicas (documentadas aqui porque nao sao obvias a partir do codigo):

1. FLAG_VALOR_INVALIDO == 'SIM' exclui a linha INTEIRA dos calculos (estatisticas
   e deteccao de outliers), mas a linha permanece no CSV de saida para auditoria.
   Sao 9 das 340 linhas.

2. Os quartis/IQR de cada parametro sao calculados de forma GLOBAL (usando todas
   as amostras validas daquele parametro), e nao por grupo RNQA+CORPODAGUA+PERIODO.
   Motivo: os grupos sao muito pequenos (varios tem N=1 a 4 amostras - ver
   Resumo_Descritiva), o que tornaria Q1/Q3 por grupo instavel/sem sentido
   estatistico. As estatisticas descritivas (media, mediana, etc.) SAO calculadas
   por grupo, conforme pedido; so a deteccao de outliers usa o parametro inteiro.

3. PERIODO e nulo para as 22 amostras de 2017 coletadas antes da numeracao de
   periodos existir (vinham das abas "2017 REMQAS" / "2017.2 REMQAS", distinguidas
   so por CAMPANHA 1/2). Usamos groupby(dropna=False) para essas linhas aparecerem
   como um grupo proprio (PERIODO = NaN) em vez de serem descartadas silenciosamente.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

plt.rcParams["font.family"] = ["Segoe UI", "Arial", "DejaVu Sans"]  # DejaVu Sans (default) nao tem glifos de subscrito (ex. O2)

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
from config.nomes_unidades import rotulo  # noqa: E402
from _lib_analise import figura_histograma_boxplot  # noqa: E402

DATA_PATH = BASE_DIR / "Dados tratados.xlsx"
OUTPUT_DIR = BASE_DIR / "output"
FIG_DIR = OUTPUT_DIR / "figuras"
OUTPUT_DIR.mkdir(exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

GROUP_COLS = ["RNQA", "CORPODAGUA", "PERIODO"]

PARAMETROS = [
    "PROFUNDIDADE",
    "VAZAO",
    "TEMPERATURA_AR",
    "TEMPERATURA_AGUA",
    "PH",
    "OXIGENIO_DISSOLVIDO",
    "COND_ELETRICA_ESPECIFICA",
    "TURBIDEZ",
    "SALINIDADE",
    "ALCALINIDADE",
    "TRANSPARENCIA_AGUA",
    "SOLIDOS_DISSOLVIDOS",
    "SOLIDOS_SUSPENSOS",
    "CLORETO_TOTAL",
    "FLUORETO_TOTAL",
    "BROMETO_TOTAL",
    "NITRATO",
    "NITRITO",
    "SULFATO",
    "FOSFATO_TOTAL",
    "ORTOFOSFATO",
    "FOSFORO_TOTAL",
    "NITROGENIO_AMONIACAL",
]

PARAMS_PRIORITARIOS = [
    "PH",
    "TURBIDEZ",
    "TEMPERATURA_AGUA",
    "COND_ELETRICA_ESPECIFICA",
    "OXIGENIO_DISSOLVIDO",
]

# limiares de N (amostras validas, apos excluir FLAG_VALOR_INVALIDO=SIM) usados
# para classificar cobertura e decidir se/como plotar
N_MIN_PLOT = 5      # abaixo disso: nao plota
N_ALERTA_PLOT = 30  # abaixo disso: plota mas com aviso de amostra pequena
N_ROBUSTO = 250     # acima disso: cobertura "robusta"
N_MODERADO = 50     # acima disso (e abaixo de N_ROBUSTO): cobertura "moderada"


def carregar_dados() -> pd.DataFrame:
    df = pd.read_excel(DATA_PATH, sheet_name="DADOS_ANALISE")
    df["VALIDO_PARA_CALCULO"] = df["FLAG_VALOR_INVALIDO"] != "SIM"
    return df


def calcular_estatisticas_por_grupo(df: pd.DataFrame) -> pd.DataFrame:
    df_calc = df[df["VALIDO_PARA_CALCULO"]]
    blocos = []
    for param in PARAMETROS:
        g = (
            df_calc.groupby(GROUP_COLS, dropna=False)[param]
            .agg(N_VALIDO="count", MEDIA="mean", MEDIANA="median", DESVIO_PADRAO="std", MINIMO="min", MAXIMO="max")
            .reset_index()
        )
        g.insert(3, "PARAMETRO", param)
        blocos.append(g)
    stats = pd.concat(blocos, ignore_index=True)
    # grupos sem nenhuma amostra valida para o parametro nao agregam informacao
    stats = stats[stats["N_VALIDO"] > 0].reset_index(drop=True)
    return stats


def calcular_limites_iqr_globais(df: pd.DataFrame) -> pd.DataFrame:
    df_calc = df[df["VALIDO_PARA_CALCULO"]]
    linhas = []
    for param in PARAMETROS:
        serie = df_calc[param].dropna()
        n = len(serie)
        if n == 0:
            linhas.append(
                {"PARAMETRO": param, "N_VALIDO_GLOBAL": 0, "Q1": None, "Q3": None, "IQR": None,
                 "LIMITE_INFERIOR": None, "LIMITE_SUPERIOR": None}
            )
            continue
        q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
        iqr = q3 - q1
        linhas.append(
            {
                "PARAMETRO": param,
                "N_VALIDO_GLOBAL": n,
                "Q1": q1,
                "Q3": q3,
                "IQR": iqr,
                "LIMITE_INFERIOR": q1 - 1.5 * iqr,
                "LIMITE_SUPERIOR": q3 + 1.5 * iqr,
            }
        )
    return pd.DataFrame(linhas)


def marcar_outliers(df: pd.DataFrame, limites: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    limites_idx = limites.set_index("PARAMETRO")
    for param in PARAMETROS:
        col = f"OUTLIER_{param}"
        lim = limites_idx.loc[param]
        if lim["N_VALIDO_GLOBAL"] == 0:
            df[col] = pd.NA
            continue
        valor = df[param]
        aplica = df["VALIDO_PARA_CALCULO"] & valor.notna()
        is_outlier = (valor < lim["LIMITE_INFERIOR"]) | (valor > lim["LIMITE_SUPERIOR"])
        resultado = pd.Series(pd.NA, index=df.index, dtype="object")
        resultado[aplica] = is_outlier[aplica]
        df[col] = resultado
    outlier_cols = [f"OUTLIER_{p}" for p in PARAMETROS]
    df["N_OUTLIERS_LINHA"] = df[outlier_cols].apply(lambda r: (r == True).sum(), axis=1)  # noqa: E712
    return df


def classificar_cobertura(n: int) -> str:
    if n >= N_ROBUSTO:
        return "ROBUSTO"
    if n >= N_MODERADO:
        return "MODERADO"
    return "BAIXO (cautela na interpretacao)"


def resumo_por_parametro(df: pd.DataFrame, limites: pd.DataFrame) -> pd.DataFrame:
    total_linhas = len(df)
    total_validas_flag = int(df["VALIDO_PARA_CALCULO"].sum())
    linhas = []
    for param in PARAMETROS:
        n_valido = int(limites.set_index("PARAMETRO").loc[param, "N_VALIDO_GLOBAL"])
        n_outliers = int((df[f"OUTLIER_{param}"] == True).sum())  # noqa: E712
        linhas.append(
            {
                "PARAMETRO": param,
                "N_TOTAL_AMOSTRAS": total_linhas,
                "N_VALIDAS_APOS_FLAG": total_validas_flag,
                "N_VALIDO_PARAMETRO": n_valido,
                "PERC_PREENCHIMENTO": round(100 * n_valido / total_validas_flag, 1) if total_validas_flag else 0.0,
                "N_OUTLIERS_IQR": n_outliers,
                "PERC_OUTLIERS_SOBRE_VALIDOS": round(100 * n_outliers / n_valido, 1) if n_valido else None,
                "COBERTURA": classificar_cobertura(n_valido),
            }
        )
    resumo = pd.DataFrame(linhas).sort_values("N_VALIDO_PARAMETRO", ascending=False).reset_index(drop=True)
    return resumo


def gerar_graficos(df: pd.DataFrame, resumo: pd.DataFrame) -> list[str]:
    sns.set_theme(style="whitegrid", rc={"font.family": ["Segoe UI", "Arial", "DejaVu Sans"]})
    resumo_idx = resumo.set_index("PARAMETRO")
    df_calc = df[df["VALIDO_PARA_CALCULO"]]
    avisos = []

    ordem = PARAMS_PRIORITARIOS + [p for p in PARAMETROS if p not in PARAMS_PRIORITARIOS]

    for param in ordem:
        n = int(resumo_idx.loc[param, "N_VALIDO_PARAMETRO"])
        prioritario = param in PARAMS_PRIORITARIOS

        if n < N_MIN_PLOT:
            msg = f"[PULADO] {param}: N={n} amostras validas -- insuficiente para qualquer visualizacao (minimo {N_MIN_PLOT})."
            avisos.append(msg)
            print(msg)
            continue

        if n < N_ALERTA_PLOT:
            msg = f"[AVISO] {param}: N={n} amostras validas -- amostra pequena, interpretar histograma/boxplot com cautela."
            avisos.append(msg)
            print(msg)
        elif not prioritario:
            print(f"[OK] {param}: N={n} amostras validas.")

        serie = df_calc[param].dropna()
        outlier_mask = df.loc[serie.index, f"OUTLIER_{param}"] == True  # noqa: E712

        rotulo_param = rotulo(param)
        titulo = f"{rotulo_param}  (N={n}{'  -- AMOSTRA PEQUENA' if n < N_ALERTA_PLOT else ''})"
        fig = figura_histograma_boxplot(serie, outlier_mask, titulo=titulo, rotulo_eixo=rotulo_param)

        prefixo = "00" if prioritario else "01"
        fig.savefig(FIG_DIR / f"{prefixo}_{param}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)

    return avisos


def main():
    df = carregar_dados()

    estatisticas_grupo = calcular_estatisticas_por_grupo(df)
    estatisticas_grupo.to_csv(OUTPUT_DIR / "estatisticas_por_grupo.csv", index=False)

    limites = calcular_limites_iqr_globais(df)
    limites.to_csv(OUTPUT_DIR / "limites_iqr_por_parametro.csv", index=False)

    df_com_outliers = marcar_outliers(df, limites)
    df_com_outliers.to_csv(OUTPUT_DIR / "dados_analise_com_outliers.csv", index=False)

    resumo = resumo_por_parametro(df_com_outliers, limites)
    resumo.to_csv(OUTPUT_DIR / "resumo_cobertura_parametros.csv", index=False)

    print("\n=== Resumo de cobertura por parametro ===")
    print(resumo.to_string(index=False))

    print("\n=== Gerando graficos ===")
    avisos = gerar_graficos(df_com_outliers, resumo)

    if avisos:
        (OUTPUT_DIR / "avisos_amostras_pequenas.txt").write_text("\n".join(avisos), encoding="utf-8")

    print(f"\nLinhas totais: {len(df)} | validas para calculo (FLAG != SIM): {int(df['VALIDO_PARA_CALCULO'].sum())}")
    print(f"CSVs salvos em: {OUTPUT_DIR}")
    print(f"Figuras salvas em: {FIG_DIR}")


if __name__ == "__main__":
    main()
