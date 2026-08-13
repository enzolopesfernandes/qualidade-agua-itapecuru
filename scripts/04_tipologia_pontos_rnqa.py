"""
Etapa 4 - Tipologia dos pontos de coleta (RNQA).
Qualidade da agua do rio Itapecuru - aba DADOS_ANALISE.

Contexto: uma analise multivariada por ponto individualmente (regressao/PCA
usando so as amostras de cada RNQA ao longo do tempo) NAO e viavel -- mediana
de 15 amostras por ponto, com 5 dos 27 pontos tendo so 1-2 amostras validas.
Em vez disso, os PONTOS (nao as amostras) sao as unidades de analise aqui:
cada um dos 27 pontos RNQA vira uma linha, resumida pela mediana de cada
parametro ao longo de TODO o periodo monitorado (agregando todas as amostras
validas daquele ponto, sem distincao temporal). Isso e uma unidade de analise
diferente do PCA/clustering do script 02 (onde cada AMOSTRA individual e uma
linha) -- aqui a pergunta e "que tipos de ponto de coleta existem na bacia",
nao "que tipos de amostra".

Fonte: output/dados_analise_com_outliers.csv (script 01), filtrado para
VALIDO_PARA_CALCULO == True. Categorias ROBUSTO/MODERADO vem de
output/resumo_cobertura_parametros.csv (mesmo criterio do script 02).

Decisoes metodologicas documentadas aqui:

1. A tabela de medianas por ponto (tipologia_pontos_medianas.csv) inclui os
   14 parametros ROBUSTO+MODERADO, para fins descritivos. Mas o PCA/
   clustering usa SO os 7 parametros ROBUSTO. Motivo: com os 14 parametros
   ROBUSTO+MODERADO, o complete-case (mediana preenchida em todos eles) cai
   para 20 dos 27 pontos; restrito aos 7 ROBUSTO, sobem para 26 dos 27 pontos
   (so MA-7187-I-1, que tem apenas N=2 amostras validas no total, fica de
   fora por faltar SALINIDADE). Como o objetivo aqui e caracterizar os
   PONTOS (nao detalhar todo parametro por ponto), preservar mais pontos com
   menos variaveis e a escolha mais util -- e explicitamente permitida pelo
   pedido original quando N=27 fica pequeno demais com mais parametros.

2. Mesmo com N=26 e 7 variaveis (razao ~3.7x), a amostra ainda fica abaixo da
   regra pratica de N >= 5x o numero de variaveis (>=35) usada em todo o
   projeto -- o resultado deve ser tratado como exploratorio, nao
   confirmatorio, igual ao PCA/clustering do script 02.

3. Padronizacao (z-score), PCA e seleccao de k via silhouette seguem
   exatamente a mesma metodologia do script 02/_lib_analise.bloco_pca_clustering
   -- so nao reusa a funcao porque ali a unidade e "amostra individual com
   id_col=ID_AMOSTRA", enquanto aqui a unidade e "ponto RNQA", exigindo uma
   agregacao (mediana) antes do complete-case.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

plt.rcParams["font.family"] = ["Segoe UI", "Arial", "DejaVu Sans"]  # DejaVu Sans (default) nao tem glifos de subscrito (ex. O2)

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
from config.estilo import CORES, CORES_SEQUENCIA  # noqa: E402
from config.nomes_unidades import rotulo  # noqa: E402
from _lib_analise import aplicar_fundo_branco  # noqa: E402

OUTPUT_DIR = BASE_DIR / "output"
FIG_DIR = OUTPUT_DIR / "figuras"
FIG_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42


def carregar_dados():
    df = pd.read_csv(OUTPUT_DIR / "dados_analise_com_outliers.csv")
    df = df[df["VALIDO_PARA_CALCULO"] == True].copy()  # noqa: E712

    resumo = pd.read_csv(OUTPUT_DIR / "resumo_cobertura_parametros.csv")
    robusto = resumo.loc[resumo["COBERTURA"] == "ROBUSTO", "PARAMETRO"].tolist()
    moderado = resumo.loc[resumo["COBERTURA"] == "MODERADO", "PARAMETRO"].tolist()
    return df, robusto, moderado


def agregar_por_ponto(df: pd.DataFrame, robusto: list[str], moderado: list[str]) -> pd.DataFrame:
    """Mediana por PONTO RNQA de cada parametro ROBUSTO+MODERADO (todas as
    amostras validas daquele ponto, agregando o periodo inteiro), mais
    metadados de localizacao/corpo d'agua e N de amostras por ponto."""
    principal = robusto + moderado
    medianas = df.groupby("RNQA")[principal].median()
    n_amostras = df.groupby("RNQA").size().rename("N_AMOSTRAS")
    meta = df.groupby("RNQA").agg(
        CORPODAGUA=("CORPODAGUA", "first"),
        LATITUDE=("LATITUDE", "mean"),
        LONGITUDE=("LONGITUDE", "mean"),
    )
    tabela = meta.join(n_amostras).join(medianas).reset_index()
    return tabela


def main():
    df, robusto, moderado = carregar_dados()
    print(f"Linhas validas para calculo: {len(df)} | pontos RNQA: {df['RNQA'].nunique()}")

    tabela = agregar_por_ponto(df, robusto, moderado)
    tabela.to_csv(OUTPUT_DIR / "tipologia_pontos_medianas.csv", index=False)

    n_pontos = tabela.shape[0]
    completos_full = tabela.dropna(subset=robusto + moderado)
    completos_robusto = tabela.dropna(subset=robusto).reset_index(drop=True)
    print(f"[tipologia] {n_pontos} pontos RNQA no total.")
    print(f"  complete-case ROBUSTO+MODERADO ({len(robusto) + len(moderado)} vars): N={len(completos_full)} pontos")
    print(f"  complete-case so ROBUSTO ({len(robusto)} vars): N={len(completos_robusto)} pontos -- usado no PCA/clustering (ver nota 1 no cabecalho)")

    variaveis = robusto
    completos = completos_robusto
    n = len(completos)

    X = completos[variaveis].values
    scaler = StandardScaler()
    X_z = scaler.fit_transform(X)

    pca = PCA(random_state=RANDOM_STATE)
    scores = pca.fit_transform(X_z)
    var_exp = pca.explained_variance_ratio_
    var_df = pd.DataFrame(
        {
            "COMPONENTE": [f"PC{i+1}" for i in range(len(var_exp))],
            "AUTOVALOR": pca.explained_variance_,
            "VARIANCIA_EXPLICADA_PCT": var_exp * 100,
            "VARIANCIA_ACUMULADA_PCT": np.cumsum(var_exp) * 100,
        }
    )
    var_df.to_csv(OUTPUT_DIR / "tipologia_pontos_pca_variancia.csv", index=False)

    loadings = pd.DataFrame(pca.components_.T, index=variaveis, columns=[f"PC{i+1}" for i in range(len(var_exp))])
    loadings.to_csv(OUTPUT_DIR / "tipologia_pontos_pca_loadings.csv")

    sil_scores = {}
    max_k = min(6, n - 1)
    for k in range(2, max_k + 1):
        km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
        labels_k = km.fit_predict(X_z)
        sil_scores[k] = silhouette_score(X_z, labels_k)
    melhor_k = max(sil_scores, key=sil_scores.get)
    print(f"[tipologia] silhouette por k: {dict((k, round(v, 3)) for k, v in sil_scores.items())} -> melhor k={melhor_k}")
    pd.DataFrame({"K": list(sil_scores.keys()), "SILHOUETTE": list(sil_scores.values())}).to_csv(
        OUTPUT_DIR / "tipologia_pontos_silhouette.csv", index=False
    )

    kmeans_final = KMeans(n_clusters=melhor_k, random_state=RANDOM_STATE, n_init=10)
    clusters = kmeans_final.fit_predict(X_z)

    scores_df = completos[["RNQA", "CORPODAGUA", "N_AMOSTRAS", "LATITUDE", "LONGITUDE"]].copy()
    for i in range(min(scores.shape[1], 5)):
        scores_df[f"PC{i+1}"] = scores[:, i]
    scores_df["CLUSTER"] = clusters
    scores_df.to_csv(OUTPUT_DIR / "tipologia_pontos_scores.csv", index=False)

    perfil = completos[variaveis].copy()
    perfil["CLUSTER"] = clusters
    perfil_medias = perfil.groupby("CLUSTER")[variaveis].mean()
    perfil_medias["N_PONTOS"] = perfil.groupby("CLUSTER").size()
    perfil_medias.to_csv(OUTPUT_DIR / "tipologia_pontos_perfil_clusters.csv")

    # figura estatica (biplot) para a Galeria, mesmo padrao visual do script 02
    fig, ax = plt.subplots(figsize=(8, 7))
    aplicar_fundo_branco(fig, ax)
    for c in range(melhor_k):
        mask = clusters == c
        cor_cluster = CORES_SEQUENCIA[c % len(CORES_SEQUENCIA)]
        ax.scatter(scores[mask, 0], scores[mask, 1], color=cor_cluster, label=f"cluster {c} (N={int(mask.sum())})", s=60)
        for idx in np.where(mask)[0]:
            ax.annotate(completos.loc[idx, "RNQA"], (scores[idx, 0], scores[idx, 1]), fontsize=6, alpha=0.75)

    escala = np.max(np.abs(scores[:, :2])) * 0.9
    for i, var in enumerate(variaveis):
        vx, vy = pca.components_[0, i], pca.components_[1, i]
        ax.arrow(0, 0, vx * escala, vy * escala, color="black", alpha=0.6, head_width=0.05, linewidth=0.8)
        ax.text(vx * escala * 1.12, vy * escala * 1.12, rotulo(var), fontsize=7.5, ha="center", va="center")

    ax.axhline(0, color="grey", linewidth=0.5)
    ax.axvline(0, color="grey", linewidth=0.5)
    ax.set_xlabel(f"PC1 ({var_exp[0] * 100:.1f}% da variancia)")
    ax.set_ylabel(f"PC2 ({var_exp[1] * 100:.1f}% da variancia)")
    ax.set_title(f"Tipologia dos pontos RNQA - PCA biplot (k={melhor_k}, N={n} pontos)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "tipologia_pontos_biplot.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"\n[tipologia] N final = {n} pontos, {len(variaveis)} variaveis (ROBUSTO). CSVs salvos em output/.")
    print(f"Figura salva em: {FIG_DIR / 'tipologia_pontos_biplot.png'}")


if __name__ == "__main__":
    main()
