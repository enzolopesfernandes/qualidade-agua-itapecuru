"""
Etapa 3 (complemento) - dispersao (a/b/c pedidos pelo usuario) + reclustering
excluindo o outlier ITA-0220. Qualidade da agua do rio Itapecuru.

Fonte: output/dados_analise_com_outliers.csv, filtrado para
VALIDO_PARA_CALCULO == True (ver script 01).

Decisoes documentadas aqui:

1. TURBIDEZ vs preditores: usa os 4 preditores que ficaram significativos ou
   limitrofes (p<0.10) no modelo TURBIDEZ ~ nucleo_robusto do script 02 (PH,
   COND_ELETRICA_ESPECIFICA, TEMPERATURA_AR, TEMPERATURA_AGUA). OXIGENIO_DISSOLVIDO
   ficou de fora por nao ser significativo (p=0.85). Cada grafico mostra o
   ajuste linear e uma curva lowess, para comparar visualmente com o R2=0.11
   do modelo linear.

2. Pares de correlacao: curados a mao, nao pegos automaticamente pelo top-N
   |r|, porque os 3 pares com r=1.00 entre FLUORETO_TOTAL, NITRITO e
   FOSFATO_TOTAL (N=20) sao quase identicos entre si -- e sao artefato de
   TODAS as amostras desse lote estarem abaixo do limite de deteccao (LOD) e
   terem sido codificadas como metade do LOD (ex. "<0,1" -> 0.05), nao uma
   relacao fisica real. Mantemos 1 desses pares como exemplo desse artefato
   (marcado explicitamente no grafico) em vez de repetir os 3.

3. Reclustering: reexecuta o bloco de PCA/clustering do script 02 (via
   _lib_analise.bloco_pca_clustering) excluindo a amostra ITA-0220, que no
   script 02 dominava sozinha o cluster "k=2" por ter condutividade/cloreto
   muito acima do resto da amostra. Os arquivos de saida usam o sufixo
   "_sem_outlier" e NAO sobrescrevem os resultados originais do script 02,
   para permitir comparar as duas versoes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

plt.rcParams["font.family"] = ["Segoe UI", "Arial", "DejaVu Sans"]  # DejaVu Sans (default) nao tem glifos de subscrito (ex. O2)

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
from config.estilo import CORES, CORES_SEQUENCIA  # noqa: E402
from config.nomes_unidades import rotulo  # noqa: E402
from _lib_analise import aplicar_fundo_branco, bloco_pca_clustering  # noqa: E402

OUTPUT_DIR = BASE_DIR / "output"
FIG_DIR = OUTPUT_DIR / "figuras"
DISP_DIR = FIG_DIR / "dispersao"
DISP_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42

PREDITORES_TURBIDEZ = ["PH", "COND_ELETRICA_ESPECIFICA", "TEMPERATURA_AR", "TEMPERATURA_AGUA"]

# (var_x, var_y, e_baixo) -- ver nota 2 no cabecalho
PARES_CORRELACAO = [
    ("COND_ELETRICA_ESPECIFICA", "SALINIDADE", False),
    ("SOLIDOS_DISSOLVIDOS", "SOLIDOS_SUSPENSOS", False),
    ("FLUORETO_TOTAL", "NITRITO", True),
    ("ALCALINIDADE", "FLUORETO_TOTAL", True),
    ("CLORETO_TOTAL", "BROMETO_TOTAL", True),
]

PARAMS_TENDENCIA = ["PH", "TURBIDEZ", "TEMPERATURA_AGUA", "COND_ELETRICA_ESPECIFICA", "OXIGENIO_DISSOLVIDO"]


def carregar_dados():
    df = pd.read_csv(OUTPUT_DIR / "dados_analise_com_outliers.csv")
    df = df[df["VALIDO_PARA_CALCULO"] == True].copy()  # noqa: E712
    resumo = pd.read_csv(OUTPUT_DIR / "resumo_cobertura_parametros.csv")
    baixo = set(resumo.loc[resumo["COBERTURA"].str.startswith("BAIXO"), "PARAMETRO"])
    return df, baixo


# ----------------------------------------------------------- (a) turbidez ----

def scatter_turbidez_vs_preditores(df):
    sns.set_theme(style="whitegrid", rc={"font.family": ["Segoe UI", "Arial", "DejaVu Sans"]})
    rotulo_turbidez = rotulo("TURBIDEZ")
    for preditor in PREDITORES_TURBIDEZ:
        dados = df[["TURBIDEZ", preditor]].dropna()
        r = dados[preditor].corr(dados["TURBIDEZ"])

        fig, ax = plt.subplots(figsize=(7.5, 5.5))
        aplicar_fundo_branco(fig, ax)
        sns.regplot(
            data=dados, x=preditor, y="TURBIDEZ", ax=ax, ci=None,
            scatter_kws={"alpha": 0.5, "s": 30, "color": CORES["petroleo"]},
            line_kws={"color": CORES["linha_tendencia"], "label": "ajuste linear"},
        )
        sns.regplot(
            data=dados, x=preditor, y="TURBIDEZ", ax=ax, scatter=False, lowess=True, ci=None,
            line_kws={"color": CORES_SEQUENCIA[2], "linestyle": "--", "label": "lowess (nao-linear)"},
        )
        ax.set_xlabel(rotulo(preditor))
        ax.set_ylabel(rotulo_turbidez)
        ax.set_title(f"{rotulo_turbidez} vs. {rotulo(preditor)}  (N={len(dados)}, r={r:.2f})")
        ax.legend()
        fig.tight_layout()
        fig.savefig(DISP_DIR / f"turbidez_vs_{preditor}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  [ok] TURBIDEZ vs {preditor}: N={len(dados)}, r={r:.2f}")


# ------------------------------------------------------ (b) pares de corr ----

def scatter_pares_correlacao(df, baixo):
    for a, b, e_baixo in PARES_CORRELACAO:
        assert (a in baixo or b in baixo) == e_baixo, f"classificacao BAIXO inconsistente para {a}/{b}"

        dados = df[[a, b]].dropna()
        r = dados[a].corr(dados[b])

        fig, ax = plt.subplots(figsize=(7.5, 5.5))
        aplicar_fundo_branco(fig, ax)
        cor = CORES["pouco"] if e_baixo else CORES["petroleo"]
        ax.scatter(dados[a], dados[b], alpha=0.6, color=cor, s=35)
        ax.set_xlabel(rotulo(a))
        ax.set_ylabel(rotulo(b))
        titulo = f"{rotulo(a)} vs. {rotulo(b)}  (N={len(dados)}, r={r:.3f})"
        if e_baixo:
            titulo += "\nN baixo -- correlacao pode ser espuria, nao usar para conclusoes fortes"
        ax.set_title(titulo, color=(CORES["pouco"] if e_baixo else CORES["texto_primario"]))
        fig.tight_layout()
        fig.savefig(DISP_DIR / f"correlacao_{a}_vs_{b}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  [ok] {a} vs {b}: N={len(dados)}, r={r:.3f}{' (BAIXO)' if e_baixo else ''}")


# --------------------------------------------------------- (c) tendencia ----

def scatter_tendencia_temporal(df):
    rng = np.random.default_rng(RANDOM_STATE)
    for param in PARAMS_TENDENCIA:
        dados = df[["ANO", param]].dropna()
        jitter = rng.uniform(-0.15, 0.15, size=len(dados))

        fig, ax = plt.subplots(figsize=(8.5, 5))
        aplicar_fundo_branco(fig, ax)
        ax.scatter(dados["ANO"] + jitter, dados[param], alpha=0.45, color=CORES["petroleo"], s=28, label="amostras")
        medias = dados.groupby("ANO")[param].mean()
        ax.plot(medias.index, medias.values, color=CORES["linha_tendencia"], marker="o", linewidth=2, label="media anual")
        ax.set_xlabel("Ano")
        ax.set_ylabel(rotulo(param))
        ax.set_title(f"{rotulo(param)} ao longo do tempo (N={len(dados)})")
        ax.legend()
        fig.tight_layout()
        fig.savefig(DISP_DIR / f"tendencia_{param}_por_ano.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  [ok] {param} x ANO: N={len(dados)}")


# ------------------------------------------------------- reclustering ----

OUTLIER_A_EXCLUIR = "ITA-0220"  # ver nota 3 no cabecalho


def reclustering_sem_outlier(df):
    resumo = pd.read_csv(OUTPUT_DIR / "resumo_cobertura_parametros.csv")
    robusto = resumo.loc[resumo["COBERTURA"] == "ROBUSTO", "PARAMETRO"].tolist()
    moderado = resumo.loc[resumo["COBERTURA"] == "MODERADO", "PARAMETRO"].tolist()

    return bloco_pca_clustering(
        df, robusto, moderado,
        sufixo="_sem_outlier",
        excluir_ids=[OUTLIER_A_EXCLUIR],
        nota_titulo=f"(sem outlier {OUTLIER_A_EXCLUIR})",
    )


def main():
    df, baixo = carregar_dados()
    print(f"Linhas validas para calculo: {len(df)}")

    print("\n=== Dispersao (a): TURBIDEZ vs preditores da regressao nucleo_robusto ===")
    scatter_turbidez_vs_preditores(df)

    print("\n=== Dispersao (b): pares de maior correlacao ===")
    scatter_pares_correlacao(df, baixo)

    print("\n=== Dispersao (c): tendencia temporal (parametros ROBUSTO) ===")
    scatter_tendencia_temporal(df)

    print(f"\n=== Reclustering excluindo {OUTLIER_A_EXCLUIR} ===")
    resultado = reclustering_sem_outlier(df)
    antigo = pd.read_csv(OUTPUT_DIR / "clustering_perfil_clusters.csv")
    print(f"\n[comparacao] clusters originais (com outlier): k={antigo.shape[0]}, tamanhos={antigo['N_AMOSTRAS'].tolist()}")
    print(f"[comparacao] clusters sem outlier: k={resultado['melhor_k']}, N total={resultado['n']}")

    print(f"\nFiguras de dispersao em: {DISP_DIR}")
    print(f"Saidas do reclustering (sufixo _sem_outlier) em: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
