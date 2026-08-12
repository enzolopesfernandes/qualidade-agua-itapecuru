"""
Funcoes compartilhadas entre os scripts de analise (01, 02, 03) e o dashboard
Streamlit (pages/) -- histograma+boxplot univariado e o bloco de PCA/clustering.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
from config.nomes_unidades import rotulo  # noqa: E402

OUTPUT_DIR = BASE_DIR / "output"
FIG_DIR = OUTPUT_DIR / "figuras"

RANDOM_STATE = 42


def figura_histograma_boxplot(serie, outlier_mask=None, titulo="", rotulo_eixo=None, cor="#4C72B0", figsize=(11, 4.5)):
    """
    Histograma + boxplot lado a lado para uma serie de valores validos de um
    parametro, com outliers (mascara booleana no mesmo indice de `serie`)
    marcados em vermelho no histograma. Usado pelo script 01 (que salva a
    figura em PNG) e pela pagina 2 do dashboard (que embute a figura ao vivo
    via st.pyplot) -- para nao duplicar essa logica em dois lugares.

    A cor padrao aqui e a mesma que o script 01 sempre usou ("#4C72B0", azul
    seaborn) -- NAO foi trocada para o azul-petroleo do dashboard, para nao
    mudar retroativamente as figuras estaticas ja aprovadas em output/figuras
    sem pedido explicito. O dashboard passa `cor=CORES["petroleo"]`
    explicitamente para usar a paleta nova so ali.
    """
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    if titulo:
        fig.suptitle(titulo)

    sns.histplot(serie, kde=True, ax=axes[0], color=cor)
    if outlier_mask is not None and outlier_mask.any():
        axes[0].scatter(
            serie[outlier_mask], [0] * int(outlier_mask.sum()),
            color="crimson", marker="x", s=60, zorder=5, label="outlier (IQR)",
        )
        axes[0].legend()
    if rotulo_eixo:
        axes[0].set_xlabel(rotulo_eixo)
    axes[0].set_ylabel("Contagem")
    axes[0].set_title("Histograma")

    sns.boxplot(x=serie, ax=axes[1], color=cor)
    if rotulo_eixo:
        axes[1].set_xlabel(rotulo_eixo)
    axes[1].set_title("Boxplot")

    fig.tight_layout()
    return fig


def figura_histograma(serie, outlier_mask=None, rotulo_eixo=None, cor="#1f6f78", figsize=(9, 4.5)):
    """
    Apenas o histograma (sem o boxplot ao lado) no estilo editorial do
    dashboard -- usado pela pagina 2 (Analise Univariada), que decidiu manter
    somente o histograma na visualizacao interativa. Nao mexe em
    figura_histograma_boxplot() acima, que continua gerando as figuras
    estaticas (histograma+boxplot) do script 01 em output/figuras/.

    outlier_mask e recebido mas NAO marcado visualmente no grafico (decisao
    de manter o histograma discreto) -- a contagem de outliers e reportada
    so em texto, pela pagina que chama esta funcao (ver legenda_grafico na
    pagina 2). O parametro continua aqui so para nao quebrar a assinatura
    usada pela pagina.
    """
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_facecolor("#F5F3EE")
    fig.patch.set_facecolor("#F5F3EE")

    sns.histplot(serie, kde=True, ax=ax, color=cor, edgecolor="#F5F3EE")
    if rotulo_eixo:
        ax.set_xlabel(rotulo_eixo)
    ax.set_ylabel("Contagem")
    ax.grid(axis="y", color="#E4DFD2", linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#8c8880")
    fig.tight_layout()
    return fig


def bloco_pca_clustering(df, robusto, moderado, sufixo="", excluir_ids=None, nota_titulo="", id_col="ID_AMOSTRA"):
    """
    PCA + KMeans nos parametros ROBUSTO/MODERADO, complete-case, sem imputacao.

    sufixo: anexado aos nomes dos arquivos de saida (ex. "_sem_outlier"), para
        poder rodar mais de uma vez sem sobrescrever a versao anterior.
    excluir_ids: lista de valores de id_col a remover do complete-case antes
        de padronizar/rodar PCA e clustering.
    nota_titulo: texto extra apendado aos titulos dos graficos (ex.
        "(sem outlier ITA-0220)").
    """
    principal = robusto + moderado
    id_cols = [c for c in ["ID_AMOSTRA", "RNQA", "CORPODAGUA", "ANO", "PERIODO"] if c in df.columns]

    completos = df[id_cols + principal].dropna().reset_index(drop=True)

    if excluir_ids:
        n_antes = completos.shape[0]
        completos = completos[~completos[id_col].isin(excluir_ids)].reset_index(drop=True)
        print(f"\n[pca{sufixo}] excluindo {excluir_ids}: {n_antes} -> {completos.shape[0]} linhas.")

    n, p = completos.shape[0], len(principal)
    print(f"[pca{sufixo}] complete-case com os {p} parametros ROBUSTO/MODERADO: N={n} linhas.")
    if n < 5 * p:
        print(f"  [AVISO] N={n} e menor que 5x o numero de variaveis ({5*p}) -- tratar PCA/clustering como exploratorio, nao confirmatorio.")

    X = completos[principal].values
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
    var_df.to_csv(OUTPUT_DIR / f"pca_variancia_explicada{sufixo}.csv", index=False)

    loadings = pd.DataFrame(
        pca.components_.T, index=principal, columns=[f"PC{i+1}" for i in range(len(var_exp))]
    )
    loadings.to_csv(OUTPUT_DIR / f"pca_loadings{sufixo}.csv")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(var_df["COMPONENTE"], var_df["VARIANCIA_EXPLICADA_PCT"], color="#4C72B0", label="% variancia explicada")
    ax.plot(var_df["COMPONENTE"], var_df["VARIANCIA_ACUMULADA_PCT"], color="crimson", marker="o", label="% acumulada")
    ax.set_ylabel("% da variancia")
    ax.set_title(f"PCA - variancia explicada (N={n} amostras completas, {p} variaveis) {nota_titulo}".strip())
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"pca_variancia_explicada{sufixo}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    sil_scores = {}
    for k in range(2, 7):
        km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
        labels_k = km.fit_predict(X_z)
        sil_scores[k] = silhouette_score(X_z, labels_k)

    melhor_k = max(sil_scores, key=sil_scores.get)
    print(f"[clustering{sufixo}] silhouette por k: {dict((k, round(v,3)) for k,v in sil_scores.items())} -> melhor k={melhor_k}")

    pd.DataFrame({"K": list(sil_scores.keys()), "SILHOUETTE": list(sil_scores.values())}).to_csv(
        OUTPUT_DIR / f"clustering_silhouette{sufixo}.csv", index=False
    )

    kmeans_final = KMeans(n_clusters=melhor_k, random_state=RANDOM_STATE, n_init=10)
    clusters = kmeans_final.fit_predict(X_z)

    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(list(sil_scores.keys()), list(sil_scores.values()), marker="o", color="#4C72B0")
    ax.axvline(melhor_k, color="crimson", linestyle="--", label=f"k escolhido = {melhor_k}")
    ax.set_xlabel("Numero de clusters (k)")
    ax.set_ylabel("Silhouette score")
    ax.set_title(f"Selecao de k - KMeans {nota_titulo}".strip())
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"clustering_silhouette{sufixo}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    scores_df = completos[id_cols].copy()
    for i in range(min(scores.shape[1], 5)):
        scores_df[f"PC{i+1}"] = scores[:, i]
    scores_df["CLUSTER"] = clusters
    scores_df.to_csv(OUTPUT_DIR / f"pca_scores{sufixo}.csv", index=False)

    perfil = completos[principal].copy()
    perfil["CLUSTER"] = clusters
    perfil_medias = perfil.groupby("CLUSTER")[principal].mean()
    perfil_medias["N_AMOSTRAS"] = perfil.groupby("CLUSTER").size()
    perfil_medias.to_csv(OUTPUT_DIR / f"clustering_perfil_clusters{sufixo}.csv")

    fig, ax = plt.subplots(figsize=(8, 7))
    palette = sns.color_palette("tab10", melhor_k)
    for c in range(melhor_k):
        mask = clusters == c
        ax.scatter(scores[mask, 0], scores[mask, 1], color=palette[c], label=f"cluster {c}", alpha=0.75, s=45)

    escala = np.max(np.abs(scores[:, :2])) * 0.9
    for i, var in enumerate(principal):
        vx, vy = pca.components_[0, i], pca.components_[1, i]
        ax.arrow(0, 0, vx * escala, vy * escala, color="black", alpha=0.6, head_width=0.05, linewidth=0.8)
        ax.text(vx * escala * 1.12, vy * escala * 1.12, rotulo(var), fontsize=7.5, ha="center", va="center")

    ax.axhline(0, color="grey", linewidth=0.5)
    ax.axvline(0, color="grey", linewidth=0.5)
    ax.set_xlabel(f"PC1 ({var_exp[0]*100:.1f}% da variancia)")
    ax.set_ylabel(f"PC2 ({var_exp[1]*100:.1f}% da variancia)")
    ax.set_title(f"PCA biplot - PC1 x PC2, clusters KMeans (k={melhor_k}, N={n}) {nota_titulo}".strip())
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"pca_biplot{sufixo}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"[pca{sufixo}] variancia explicada, loadings, scores e perfil de clusters salvos em output/.")

    return {"n": n, "melhor_k": melhor_k, "sil_scores": sil_scores, "clusters": clusters, "completos": completos}
