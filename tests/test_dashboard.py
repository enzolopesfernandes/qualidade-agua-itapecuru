"""
Testes de fumaca do dashboard com streamlit.testing.v1.AppTest.

Nao usa pytest (projeto nao tinha framework de teste antes) -- roda como
script mesmo: `python tests/test_dashboard.py`. Cada pagina e carregada via
AppTest a partir de Home.py + switch_page(), que e a unica forma de o
AppTest resolver corretamente st.page_link() num app multipagina (rodar
AppTest.from_file() direto num arquivo de pages/ falha, porque ele nao
enxerga o restante do app).

Cobre: nenhuma pagina lanca excecao, titulo oficial exato aparece na Home,
badges usam a nomenclatura simplificada (Robusto/Moderado/Pouco, nunca
"BAIXO"), placeholders dos filtros em portugues, tipologia dos pontos RNQA
(pagina 3), regressao removida da pagina 3, e a segmentacao por corpo d'agua
nas paginas 2/3/Galeria (5a/5b/5c, uma pagina Streamlit por corpo d'agua) --
incluindo casos-limite de N baixo (RIO ALPERCATAS, N=1) e N moderado
(RIO PERITORO).
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from streamlit.testing.v1 import AppTest  # noqa: E402

TITULO_ESPERADO = (
    "Análise Exploratória e Visualização Interativa de Dados da Qualidade da Água: "
    "um estudo aplicado à Bacia do Rio Itapecuru"
)

PAGINAS = [
    "pages/1_Contexto_e_Dados.py",
    "pages/2_Analise_Univariada.py",
    "pages/3_Analise_Multivariada.py",
    "pages/4_Analise_Temporal_Multivariada.py",
    "pages/5a_Galeria_Bacia_Toda.py",
    "pages/5b_Galeria_Rio_Itapecuru.py",
    "pages/5c_Galeria_Demais_Corpos_Dagua.py",
]

falhas = []


def checar(descricao: str, condicao: bool) -> None:
    status = "OK  " if condicao else "FAIL"
    print(f"[{status}] {descricao}")
    if not condicao:
        falhas.append(descricao)


def texto_completo(at: AppTest) -> str:
    partes = []
    for lista in (at.markdown, at.caption, at.title, at.header, at.subheader, at.text):
        for el in lista:
            partes.append(getattr(el, "value", "") or "")
    return "\n".join(partes)


print("=== Home.py ===")
at = AppTest.from_file(str(BASE_DIR / "Home.py")).run(timeout=30)
checar("Home carrega sem excecao", len(at.exception) == 0)
texto_home = texto_completo(at)
_titulo_principal, _, _titulo_sub = TITULO_ESPERADO.partition(": ")
checar(
    "Titulo oficial exato aparece na Home (partes antes/depois do ':', a segunda em <em>)",
    _titulo_principal in texto_home and _titulo_sub in texto_home,
)
checar("Home NAO explica mais o menu (sem 'Use o menu')", "Use o menu" not in texto_home)
checar("Home NAO menciona mais TCC / artigo academico", "TCC" not in texto_home and "artigo acadêmico" not in texto_home.lower())

for caminho in PAGINAS:
    print(f"\n=== {caminho} ===")
    at.switch_page(caminho)
    at.run(timeout=60)
    checar(f"{caminho} carrega sem excecao", len(at.exception) == 0)
    if at.exception:
        for exc in at.exception:
            print("   ", exc.value if hasattr(exc, "value") else exc)

    texto = texto_completo(at)

    if caminho == "pages/1_Contexto_e_Dados.py":
        checar("Badge usa 'Pouco' (nao 'BAIXO')", "Pouco" in texto)
        checar("Menciona ANA / RNQA na proveniencia dos dados", "Agência Nacional de Águas" in texto and "2013" in texto)
        checar("Nao menciona mais 'planilha' como fonte", "planilha" not in texto.lower())

    if caminho == "pages/2_Analise_Univariada.py":
        placeholders = [m.placeholder for m in at.multiselect]
        checar("Todos os multiselect tem placeholder em portugues", all(p == "Selecione uma opção" for p in placeholders))
        checar("Secao 'Comparação entre corpos d'água' presente", "Comparação entre corpos d'água" in texto)
        rotulos_multiselect = [m.label for m in at.multiselect]
        checar(
            "Filtro renomeado para 'Rodada de monitoramento' (nao 'Período'/'Ciclo')",
            "Rodada de monitoramento" in rotulos_multiselect and "Período" not in rotulos_multiselect,
        )
        checar("Nao menciona 'campanha' em nenhum lugar da pagina", "campanha" not in texto.lower())
        checar("Legenda reporta outliers em texto ('identificadas como outlier')", "identificadas como outlier" in texto)
        checar("Nao menciona mais 'X vermelhos' (marcacao visual removida)", "vermelhos" not in texto.lower())

        # segmentacao por corpo d'agua: selecionar 1 corpo especifico deve mostrar N em destaque (st.metric)
        at.multiselect(key="filtro_corpo").set_value(["RIO PERITORO"]).run(timeout=60)
        checar(
            "Selecionar 1 corpo d'água mostra N em destaque (st.metric) no topo",
            any("RIO PERITORO" in (m.label or "") for m in at.metric),
        )
        at.multiselect(key="filtro_corpo").set_value([]).run(timeout=60)

    if caminho == "pages/3_Analise_Multivariada.py":
        checar("Explicacao de correlacao de Pearson presente", "correlação de pearson" in texto.lower())
        checar("Menciona 'Pouca' em vez de 'BAIXA'", "cobertura Pouca" in texto or "Pouca" in texto)
        checar("Frase 'Rótulos com *' removida", "Rótulos com" not in texto)
        checar("Filtro de recorte espacial (corpo d'água / ponto RNQA) presente", "Recorte espacial" in texto)
        rotulos_sel3 = [s.label for s in at.selectbox]
        checar("Selectbox 'Nível' do recorte espacial presente", "Nível" in rotulos_sel3)
        checar("Toggle 'Mostrar todos os pontos' presente na Dispersão", any(c.key == "disp_mostrar_tudo" for c in at.checkbox))
        checar(
            "Nota de zoom ajustado (eixo recortado) aparece com TURBIDEZ selecionado por padrão",
            "para destacar a relação" in texto,
        )
        at.checkbox(key="disp_mostrar_tudo").set_value(True).run(timeout=30)
        texto_sem_zoom = texto_completo(at)
        checar(
            "Ativar 'Mostrar todos os pontos' remove a nota de zoom",
            "para destacar a relação" not in texto_sem_zoom,
        )
        at.checkbox(key="disp_mostrar_tudo").set_value(False).run(timeout=30)

        # regressao multipla removida completamente da pagina
        checar("Seção de regressão múltipla REMOVIDA da página 3", "Regressão múltipla" not in texto and "Variável alvo" not in [s.label for s in at.selectbox])
        checar("Seletor de 'Modelo' (núcleo robusto/completo) REMOVIDO", not any(r.label == "Modelo" for r in at.radio))

        # secao de tipologia dos pontos de coleta (unidade = ponto RNQA, nao amostra) -- agora secao 04
        checar("Secao 'Tipologia dos pontos de coleta' presente", "Tipologia dos pontos de coleta" in texto)
        checar(
            "Texto de abertura simplificado da Tipologia presente",
            "quais pontos de coleta têm um comportamento parecido" in texto,
        )
        checar("Metrica de N de pontos usados no PCA presente", any("Pontos usados no PCA" in (m.label or "") for m in at.metric))
        checar("Grafico de silhouette por k REMOVIDO da secao PCA/Clustering", "Silhouette por número de clusters" not in texto)

        # segmentacao por corpo d'agua: N insuficiente (RIO ALPERCATAS, N=1) bloqueia PCA
        at.selectbox(key="nivel_recorte_multivariada").set_value("Corpo d'água").run(timeout=60)
        sel_corpo3 = at.selectbox(key="valor_recorte_corpo_multivariada")
        sel_corpo3.set_value("RIO ALPERCATAS").run(timeout=60)
        checar("RIO ALPERCATAS (N=1) carrega sem excecao", len(at.exception) == 0)
        texto_alpercatas = texto_completo(at)
        checar(
            "RIO ALPERCATAS: nota de N insuficiente para PCA aparece",
            "N insuficiente para PCA/clustering" in texto_alpercatas,
        )

        # N suficiente (RIO ITAPECURU) deve exibir PCA normalmente
        sel_corpo3.set_value("RIO ITAPECURU").run(timeout=60)
        checar("RIO ITAPECURU carrega sem excecao", len(at.exception) == 0)
        texto_itapecuru = texto_completo(at)
        checar(
            "RIO ITAPECURU: PCA ao vivo exibido (sem nota de N insuficiente)",
            "N insuficiente para PCA/clustering" not in texto_itapecuru,
        )
        at.selectbox(key="nivel_recorte_multivariada").set_value("Toda a bacia").run(timeout=60)

    if caminho == "pages/4_Analise_Temporal_Multivariada.py":
        checar("Aviso de padronizacao (z-score) presente", "z-score" in texto)
        checar("Secao de chuva presente", "chuva" in texto.lower())
        checar("Secao 'Cobertura da rede' REMOVIDA", "Cobertura da rede" not in texto)
        checar("Legenda de grafico NAO mostra contagem de pontos tipo '(22/27)'", "pts (" not in texto and "pontos RNQA foram visitados" not in texto)
        checar("Nao menciona 'campanha' em nenhum lugar da pagina", "campanha" not in texto.lower())
        checar("Menciona 'rodada de monitoramento' (eixo PERIODO, nao ANO)", "rodada de monitoramento" in texto.lower())
        checar("Secao de corpos d'agua ao longo dos periodos presente", "RIO ITAPECURU" in texto)
        checar("Secao 03 usa 'períodos' (nao mais 'rodadas') no titulo", "ao longo dos períodos" in texto)

    if caminho == "pages/5a_Galeria_Bacia_Toda.py":
        checar("Secao 'Relações esperadas pela literatura' presente", "Relações esperadas pela literatura" in texto)
        checar("Par Turbidez x Solidos Suspensos citado nas relacoes esperadas", "Sólidos Suspensos" in texto)
        checar(
            "Tipo de relação (ex. 'Linear forte') aparece na legenda, não mais como estrutura de navegação",
            "Linear forte" in texto or "Monotônica não-linear" in texto or "Fraca/sem relação" in texto,
        )
        checar("Toggle 'Mostrar todos os pontos' presente", any(c.key == "galeria_mostrar_tudo" for c in at.checkbox))
        checar("Nota de zoom ajustado (eixo recortado) aparece em algum par", "para destacar a relação" in texto)

        antes = [i.proto.imgs[0].caption for i in at.get("imgs")]
        checar("Galeria Bacia toda tem varios PNGs estaticos (histogramas/PCA/regressao)", len(antes) > 15)
        at.text_input(key="galeria_busca_bacia").set_value("Turbidez").run(timeout=90)
        depois = [i.proto.imgs[0].caption for i in at.get("imgs")]
        checar("Busca 'Turbidez' muda a quantidade de imagens exibidas", antes != depois)
        at.text_input(key="galeria_busca_bacia").set_value("").run(timeout=90)

    if caminho == "pages/5b_Galeria_Rio_Itapecuru.py":
        checar("Titulo menciona RIO ITAPECURU", "Itapecuru" in texto)
        checar("N (241 amostras) aparece", "N = 241" in texto or "N=241" in texto)
        checar("Regressão ao vivo exibida para RIO ITAPECURU (N suficiente)", "Regressão —" in texto)
        checar("PCA/Clustering ao vivo exibido para RIO ITAPECURU (N suficiente)", "PCA/Clustering** (N=" in texto)

    if caminho == "pages/5c_Galeria_Demais_Corpos_Dagua.py":
        rotulos_sel5c = [s.label for s in at.selectbox]
        checar("Selectbox 'Corpo d'água' presente", any("Corpo d" in r for r in rotulos_sel5c))
        sel5c = at.selectbox(key=None) if False else at.selectbox[0]

        # caso-limite: corpo d'agua com N muito baixo (RIO ALPERCATAS, N=1) -> "Multivariada limitada"
        sel5c.set_value("RIO ALPERCATAS").run(timeout=90)
        checar("RIO ALPERCATAS (N=1) carrega sem excecao", len(at.exception) == 0)
        texto_alperc_gal = texto_completo(at)
        checar("'Multivariada limitada' aparece para RIO ALPERCATAS", "Multivariada limitada" in texto_alperc_gal)

        # N moderado (RIO PERITORO, N=30): correlacao/dispersao/PCA disponiveis
        sel5c.set_value("RIO PERITORO").run(timeout=90)
        checar("RIO PERITORO (N=30) carrega sem excecao", len(at.exception) == 0)
        texto_peritoro_gal = texto_completo(at)
        checar("RIO PERITORO: Multivariada NAO fica limitada", "Multivariada limitada" not in texto_peritoro_gal)
        checar("RIO PERITORO: PCA/Clustering ao vivo exibido", "PCA/Clustering** (N=" in texto_peritoro_gal)

print("\n" + "=" * 60)
if falhas:
    print(f"{len(falhas)} checagem(ns) falharam:")
    for f in falhas:
        print(" -", f)
    sys.exit(1)
else:
    print("Todas as checagens passaram.")
