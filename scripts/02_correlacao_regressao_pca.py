"""
Etapa 3 - correlacao, regressao multipla e PCA/clustering.
Qualidade da agua do rio Itapecuru - aba DADOS_ANALISE.

Fonte: output/dados_analise_com_outliers.csv (gerado pelo script 01), filtrado
para VALIDO_PARA_CALCULO == True (ver script 01 para a razao da exclusao).
As categorias de cobertura (ROBUSTO/MODERADO/BAIXO) vem de
output/resumo_cobertura_parametros.csv.

Decisoes metodologicas documentadas aqui:

1. CORRELACAO: uma unica matriz de Pearson pairwise com os 23 parametros
   (14 principais ROBUSTO/MODERADO + 9 exploratorios BAIXO), calculada com
   pandas .corr() (usa todos os pares disponiveis, ignorando NaN par a par).
   As colunas/linhas BAIXO sao marcadas com "*" no heatmap e reportadas com
   sua propria matriz de N pairwise, para deixar claro quando uma correlacao
   vem de poucas amostras.

2. REGRESSAO MULTIPLA (TURBIDEZ e VAZAO): testamos dois modelos por alvo:
   - "completo": todos os outros 13 parametros ROBUSTO/MODERADO como preditores,
     em complete-case (linhas sem nenhum NaN em nenhuma variavel envolvida).
   - "nucleo_robusto": so os outros parametros ROBUSTO (6) como preditores.
   Isso e necessario porque o complete-case com os 14 parametros principais
   junto cai para N=36 (TURBIDEZ) e N=5 (VAZAO) -- o segundo caso e menor que
   o numero de preditores (14) e a regressao nem pode ser ajustada (matriz
   singular), entao o modelo "completo" de VAZAO e pulado e reportado como
   inviavel. O modelo "nucleo_robusto" tem N muito maior (284 para TURBIDEZ,
   31 para VAZAO) e e o que deve ser usado para qualquer conclusao.
   Reportamos a razao N/preditores em todos os modelos para deixar a
   confiabilidade explicita.

3. REGRESSAO - MULTICOLINEARIDADE: COND_ELETRICA_ESPECIFICA e SALINIDADE tem
   correlacao de Pearson = 0.9997 (sao essencialmente a mesma grandeza fisica,
   salinidade e derivada da condutividade). Incluir as duas juntas como
   preditoras faz o numero de condicao da regressao explodir (>80000, contra
   um limiar de alerta usual de ~30) e gera coeficientes padronizados
   fisicamente implausiveis (ex.: beta=-12 para SALINIDADE). Por isso
   SALINIDADE e excluida do conjunto de preditores em todos os modelos de
   regressao (mantendo COND_ELETRICA_ESPECIFICA, a grandeza medida
   diretamente). Ela continua normalmente na matriz de correlacao e no PCA,
   onde essa redundancia nao e um problema (so aparece como duas variaveis
   com loading quase identico no mesmo componente).

4. PCA/CLUSTERING: usa apenas os 14 parametros ROBUSTO/MODERADO, sem imputacao
   (conforme pedido), o que restringe a analise as N=36 linhas completas nessas
   14 variaveis. Essa amostra e pequena para 14 variaveis (regra pratica
   sugere N >= ~5x o numero de variaveis) -- o resultado deve ser tratado como
   exploratorio, nao confirmatorio. Variaveis padronizadas (z-score) antes do
   PCA e do KMeans, ja que estao em unidades muito diferentes (pH, uS/cm,
   NTU, graus C, mg/L...).

Nenhuma linha e removida do dataset original; os filtros de completude sao
aplicados apenas dentro de cada analise, e o N usado e sempre reportado.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import statsmodels.api as sm

plt.rcParams["font.family"] = ["Segoe UI", "Arial", "DejaVu Sans"]  # DejaVu Sans (default) nao tem glifos de subscrito (ex. O2)
from statsmodels.stats.outliers_influence import variance_inflation_factor

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
from config.nomes_unidades import rotulo  # noqa: E402
from _lib_analise import bloco_pca_clustering  # noqa: E402

OUTPUT_DIR = BASE_DIR / "output"
FIG_DIR = OUTPUT_DIR / "figuras"
FIG_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------- carga ----

def carregar_dados():
    df = pd.read_csv(OUTPUT_DIR / "dados_analise_com_outliers.csv")
    df = df[df["VALIDO_PARA_CALCULO"] == True].copy()  # noqa: E712

    resumo = pd.read_csv(OUTPUT_DIR / "resumo_cobertura_parametros.csv")
    robusto = resumo.loc[resumo["COBERTURA"] == "ROBUSTO", "PARAMETRO"].tolist()
    moderado = resumo.loc[resumo["COBERTURA"] == "MODERADO", "PARAMETRO"].tolist()
    baixo = resumo.loc[resumo["COBERTURA"].str.startswith("BAIXO"), "PARAMETRO"].tolist()

    return df, robusto, moderado, baixo


# ----------------------------------------------------------- correlacao ----

def bloco_correlacao(df, robusto, moderado, baixo):
    principal = robusto + moderado
    todos = principal + baixo

    corr = df[todos].corr(method="pearson")
    corr.to_csv(OUTPUT_DIR / "correlacao_pearson.csv")

    n_pairwise = pd.DataFrame(index=todos, columns=todos, dtype="float")
    for a in todos:
        for b in todos:
            n_pairwise.loc[a, b] = df[[a, b]].dropna().shape[0]
    n_pairwise = n_pairwise.astype(int)
    n_pairwise.to_csv(OUTPUT_DIR / "correlacao_pearson_n_amostras.csv")

    # heatmap: parametros principais primeiro, depois os BAIXO marcados com "*"
    labels = {p: (rotulo(p) if p in principal else f"{rotulo(p)}*") for p in todos}
    corr_plot = corr.rename(index=labels, columns=labels)

    fig, ax = plt.subplots(figsize=(13, 11))
    sns.heatmap(
        corr_plot, cmap="vlag", vmin=-1, vmax=1, center=0, annot=True, fmt=".2f",
        annot_kws={"size": 6.5}, square=True, linewidths=0.4, linecolor="white",
        cbar_kws={"label": "Correlacao de Pearson"}, ax=ax,
    )
    # linha separando bloco principal do bloco baixo
    corte = len(principal)
    ax.axhline(corte, color="black", linewidth=2)
    ax.axvline(corte, color="black", linewidth=2)
    for tick, param in zip(ax.get_xticklabels(), todos):
        if param in baixo:
            tick.set_color("crimson")
    for tick, param in zip(ax.get_yticklabels(), todos):
        if param in baixo:
            tick.set_color("crimson")

    ax.set_title(
        "Correlacao de Pearson pairwise - parametros fisico-quimicos\n"
        "Em vermelho/* : cobertura Pouca (N <= 39 amostras validas) - nao usar para conclusoes fortes",
        fontsize=11,
    )
    fig.tight_layout()
    fig.savefig(FIG_DIR / "correlacao_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"[correlacao] matriz {len(todos)}x{len(todos)} salva ({len(principal)} principais + {len(baixo)} baixo).")
    return corr, n_pairwise


# ------------------------------------------------------------- regressao ----

def ajustar_ols(df, alvo, preditores, min_n_por_preditor=5):
    cols = [alvo] + preditores
    dados = df[cols].dropna()
    n, p = dados.shape[0], len(preditores)

    if n <= p:
        print(f"  [INVIAVEL] {alvo} ~ {len(preditores)} preditores: N={n} <= numero de preditores ({p}). Modelo nao ajustavel (matriz singular). Pulado.")
        return None

    razao = n / p
    if razao < min_n_por_preditor:
        print(f"  [AVISO] {alvo} ~ {len(preditores)} preditores: N={n}, razao N/preditores={razao:.1f} (< {min_n_por_preditor}) -- resultado pouco confiavel, tratar como exploratorio.")
    else:
        print(f"  [OK] {alvo} ~ {len(preditores)} preditores: N={n}, razao N/preditores={razao:.1f}.")

    y = dados[alvo]
    X = sm.add_constant(dados[preditores])
    modelo = sm.OLS(y, X).fit()

    # coeficientes padronizados (z-score em y e X) para comparar magnitude de efeito
    y_z = (y - y.mean()) / y.std()
    X_z = (dados[preditores] - dados[preditores].mean()) / dados[preditores].std()
    X_z = sm.add_constant(X_z)
    modelo_padronizado = sm.OLS(y_z, X_z).fit()

    # VIF: diagnostico de colinearidade invariante a escala (diferente do numero de
    # condicao do statsmodels, que e sensivel a diferencas de escala entre preditores
    # e por isso pode parecer alto mesmo sem colinearidade real -- ver VIF nos csvs)
    vif = pd.Series(
        [variance_inflation_factor(X.values, i) for i in range(1, X.shape[1])],
        index=preditores,
    )

    return {
        "alvo": alvo,
        "preditores": preditores,
        "n": n,
        "p": p,
        "razao_n_p": razao,
        "modelo": modelo,
        "coef_padronizado": modelo_padronizado.params.drop("const"),
        "vif": vif,
    }


def salvar_resultado_regressao(resultado, label, coef_rows, metricas_rows):
    if resultado is None:
        return
    modelo = resultado["modelo"]
    alvo = resultado["alvo"]

    (OUTPUT_DIR / f"regressao_{alvo}_{label}.txt").write_text(str(modelo.summary()), encoding="utf-8")

    for var in resultado["preditores"]:
        coef_rows.append(
            {
                "ALVO": alvo,
                "MODELO": label,
                "VARIAVEL": var,
                "COEFICIENTE": modelo.params[var],
                "COEFICIENTE_PADRONIZADO": resultado["coef_padronizado"][var],
                "ERRO_PADRAO": modelo.bse[var],
                "T": modelo.tvalues[var],
                "P_VALOR": modelo.pvalues[var],
                "IC_95_INF": modelo.conf_int().loc[var, 0],
                "IC_95_SUP": modelo.conf_int().loc[var, 1],
                "VIF": resultado["vif"][var],
            }
        )

    metricas_rows.append(
        {
            "ALVO": alvo,
            "MODELO": label,
            "N": resultado["n"],
            "N_PREDITORES": resultado["p"],
            "RAZAO_N_PREDITORES": round(resultado["razao_n_p"], 1),
            "R2": modelo.rsquared,
            "R2_AJUSTADO": modelo.rsquared_adj,
            "F_STAT": modelo.fvalue,
            "F_PVALOR": modelo.f_pvalue,
            "NUMERO_CONDICAO": modelo.condition_number,
            "VIF_MAXIMO": resultado["vif"].max(),
        }
    )

    # diagnostico: observado vs previsto + histograma de residuos
    rotulo_alvo = rotulo(alvo)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].scatter(modelo.fittedvalues, modelo.model.endog, alpha=0.6, color="#4C72B0")
    lims = [min(axes[0].get_xlim()[0], axes[0].get_ylim()[0]), max(axes[0].get_xlim()[1], axes[0].get_ylim()[1])]
    axes[0].plot(lims, lims, "--", color="gray", linewidth=1)
    axes[0].set_xlabel(f"Previsto - {rotulo_alvo}")
    axes[0].set_ylabel(f"Observado - {rotulo_alvo}")
    axes[0].set_title(f"Observado vs. previsto (R2={modelo.rsquared:.2f})")

    sns.histplot(modelo.resid, kde=True, ax=axes[1], color="#4C72B0")
    axes[1].set_xlabel(f"Residuo - {rotulo_alvo}")
    axes[1].set_title("Distribuicao dos residuos")

    fig.suptitle(f"{rotulo_alvo} ~ {label}  (N={resultado['n']}, {resultado['p']} preditores)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"regressao_{alvo}_{label}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


EXCLUIR_DA_REGRESSAO = ["SALINIDADE"]  # ver nota 3 no cabecalho: colinear com COND_ELETRICA_ESPECIFICA (r=0.9997)


def bloco_regressao(df, robusto, moderado):
    principal = [p for p in robusto + moderado if p not in EXCLUIR_DA_REGRESSAO]
    robusto_reg = [p for p in robusto if p not in EXCLUIR_DA_REGRESSAO]
    coef_rows, metricas_rows = [], []

    for alvo in ["TURBIDEZ", "VAZAO"]:
        print(f"\n[regressao] alvo = {alvo}")
        preditores_completo = [p for p in principal if p != alvo]
        preditores_robusto = [p for p in robusto_reg if p != alvo]

        r_completo = ajustar_ols(df, alvo, preditores_completo)
        salvar_resultado_regressao(r_completo, "completo", coef_rows, metricas_rows)

        r_robusto = ajustar_ols(df, alvo, preditores_robusto)
        salvar_resultado_regressao(r_robusto, "nucleo_robusto", coef_rows, metricas_rows)

    pd.DataFrame(coef_rows).to_csv(OUTPUT_DIR / "regressao_coeficientes.csv", index=False)
    pd.DataFrame(metricas_rows).to_csv(OUTPUT_DIR / "regressao_metricas.csv", index=False)
    print("\n[regressao] coeficientes e metricas salvos em output/regressao_coeficientes.csv e output/regressao_metricas.csv")


# bloco_pca_clustering agora mora em _lib_analise.py (compartilhado com o script 03)


def main():
    df, robusto, moderado, baixo = carregar_dados()
    print(f"Linhas validas para calculo: {len(df)}")
    print(f"ROBUSTO ({len(robusto)}): {robusto}")
    print(f"MODERADO ({len(moderado)}): {moderado}")
    print(f"BAIXO ({len(baixo)}): {baixo}")

    print("\n=== Bloco 1a: correlacao ===")
    bloco_correlacao(df, robusto, moderado, baixo)

    print("\n=== Bloco 1b: regressao multipla ===")
    bloco_regressao(df, robusto, moderado)

    print("\n=== Bloco 2: PCA / clustering (so ROBUSTO+MODERADO) ===")
    bloco_pca_clustering(df, robusto, moderado)

    print(f"\nCSVs em: {OUTPUT_DIR}")
    print(f"Figuras em: {FIG_DIR}")


if __name__ == "__main__":
    main()
