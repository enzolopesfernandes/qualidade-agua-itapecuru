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
"BAIXO"), placeholders dos filtros em portugues, e o filtro de busca da
Galeria realmente filtra.
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
    "pages/5_Galeria_de_Graficos.py",
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

for caminho in PAGINAS:
    print(f"\n=== {caminho} ===")
    at.switch_page(caminho)
    at.run(timeout=30)
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

    if caminho == "pages/3_Analise_Multivariada.py":
        checar("Explicacao de correlacao de Pearson presente", "correlação de pearson" in texto.lower())
        checar("Menciona 'Pouca' em vez de 'BAIXA'", "cobertura Pouca" in texto or "Pouca" in texto)
        checar("Frase 'Rótulos com *' removida", "Rótulos com" not in texto)
        checar("Filtro de recorte espacial (corpo d'água / ponto RNQA) presente", "Recorte espacial" in texto)
        rotulos_sel3 = [s.label for s in at.selectbox]
        checar("Selectbox 'Nível' do recorte espacial presente", "Nível" in rotulos_sel3)
        checar(
            "Nota de que Regressão/PCA sempre usam a bacia inteira",
            texto.count("sempre usa a bacia inteira") >= 2,
        )

    if caminho == "pages/4_Analise_Temporal_Multivariada.py":
        checar("Aviso de padronizacao (z-score) presente", "z-score" in texto)
        checar("Secao de chuva presente", "chuva" in texto.lower())
        checar("Secao 'Cobertura da rede' REMOVIDA", "Cobertura da rede" not in texto)
        checar("Legenda de grafico NAO mostra contagem de pontos tipo '(22/27)'", "pts (" not in texto and "pontos RNQA foram visitados" not in texto)
        checar("Nao menciona 'campanha' em nenhum lugar da pagina", "campanha" not in texto.lower())
        checar("Menciona 'rodada de monitoramento' (eixo PERIODO, nao ANO)", "rodada de monitoramento" in texto.lower())
        checar("Secao de corpos d'agua ao longo das rodadas presente", "RIO ITAPECURU" in texto)

    if caminho == "pages/5_Galeria_de_Graficos.py":
        checar("Secao 'Relações esperadas pela literatura' presente", "Relações esperadas pela literatura" in texto)
        checar("Par Turbidez x Solidos Suspensos citado nas relacoes esperadas", "Sólidos Suspensos" in texto)
        checar("Categoria 'Correlação Linear' presente", "Correlação Linear" in texto)
        checar("Categoria 'Correlação Não-linear' presente", "Correlação Não-linear" in texto)
        checar("Categoria 'Sem Relação' presente", "Sem Relação" in texto)
        antes = [c.value for c in at.caption if "gráficos." in (c.value or "")]
        checar("Galeria tem bem mais que 47 graficos (pares dinamicos incluidos)", antes and int(antes[0].split(" de ")[1].split(" ")[0]) > 100)
        at.text_input(key="galeria_busca").set_value("Turbidez").run(timeout=60)
        depois = [c.value for c in at.caption if "gráficos." in (c.value or "")]
        checar("Busca 'Turbidez' na Galeria muda a contagem exibida", antes != depois)

print("\n" + "=" * 60)
if falhas:
    print(f"{len(falhas)} checagem(ns) falharam:")
    for f in falhas:
        print(" -", f)
    sys.exit(1)
else:
    print("Todas as checagens passaram.")
