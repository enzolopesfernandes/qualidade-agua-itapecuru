# Auditoria completa do projeto — lógica, matemática e metodologia científica

Data: 2026-08-14
Escopo: `scripts/01-04`, `dashboard_common.py`, `galeria_common.py`, `pages/1-4`, `pages/5a-5c`, dados em `output/*.csv` e no Excel bruto (`Dados tratados.xlsx`).
Método: leitura de código + reexecução independente de cálculos em Python (não apenas leitura — cada afirmação abaixo marcada "confirmado" foi checada rodando o cálculo de novo sobre os dados atuais, não só lida no código).

Este relatório é só diagnóstico — nenhuma mudança de código foi feita. Numeração das seções segue o pedido original.

---

## Resumo executivo

| Gravidade | Quantidade |
|---|---|
| 🔴 Crítico | 0 |
| 🟡 Moderado | 11 |
| ⚪ Cosmético | 5 |

**Nenhum problema crítico foi encontrado** — ou seja, nenhum cálculo hoje exibido no dashboard está matematicamente incorreto a ponto de mudar uma conclusão. Os 11 problemas moderados são principalmente: (a) uma inconsistência real e mensurável entre a nova "Tipologia dos pontos" e o clustering original quanto à exclusão do outlier ITA-0220, (b) lacunas de transparência metodológica que já existiam informalmente em partes do app mas não se propagaram para as seções novas (Galeria, segmentação por corpo d'água), e (c) duas limitações estatísticas conhecidas (comparações múltiplas, independência dos resíduos) que nunca foram formalmente endereçadas em nenhuma versão do projeto — não é uma regressão desta rodada, é uma lacuna de sempre que vale a pena registrar agora que o projeto está mais maduro.

### Recomendação de prioridade

**Prioridade 1 — baixo esforço, alto valor de transparência (fazer primeiro):**
1. §5.4 — Propagar a exclusão do outlier ITA-0220 para `scripts/04_tipologia_pontos_rnqa.py` (bug real, fix simples, uma linha).
2. §4.2 — Reinserir o aviso de "amostra pequena/exploratório" para o modelo de regressão "completo" (Turbidez, N=36), que sumiu da UI quando a seção de regressão foi removida da página 3.
3. §7.1 — Adicionar nota (ou remover) os 5 gráficos estáticos "X ao longo do tempo" na Galeria que usam ANO como eixo, contradizendo a decisão deliberada de usar PERIODO no resto do projeto.

**Prioridade 2 — consistência entre páginas (esforço médio):**
4. §5.2 — Adicionar a mesma nota de "N pequeno/exploratório" no bloco de PCA/Clustering da Galeria (hoje só existe na página 3).
5. §3.1 — Mostrar N por par no heatmap de correlação da Galeria (hoje só a página 3 mostra isso no hover).
6. §3.3 — Decidir: ou Spearman aparece consistentemente em todo lugar que classifica relação (heatmap, dispersão da página 3), ou o rótulo "Monotônica não-linear" da Galeria passa a citar explicitamente que só ali Spearman é calculado.

**Prioridade 3 — limitações estatísticas de fundo (maior esforço, considerar para uma versão futura):**
7. §4.1 — Nenhum teste formal de normalidade/homocedasticidade/independência dos resíduos existe em nenhuma regressão; a violação de independência é estruturalmente esperada (medidas repetidas por ponto RNQA ao longo dos períodos) e nunca foi mencionada como limitação em texto algum.
8. §3.2 — Nenhuma correção para comparações múltiplas (23×23 pares de correlação; múltiplos p-valores de regressão, agora multiplicados pelos 7 corpos d'água) — mencionar como limitação é suficiente para esta fase, correção formal é opcional.

**Prioridade 4 — cosmético, sem urgência:** itens de §1.2, §1.4, §5.3, §8.1.

---

## 1. Limpeza e tratamento de dados

### 1.1 Exclusão de FLAG_VALOR_INVALIDO=SIM apenas dos cálculos

**✅ Confirmado correto.** `scripts/01_univariate_outliers.py` marca `VALIDO_PARA_CALCULO = FLAG_VALOR_INVALIDO != 'SIM'` e nunca dropa linhas do DataFrame — `marcar_outliers()` faz `df.copy()` e preserva as 340 linhas no CSV de saída. Todas as páginas e scripts posteriores (incluindo os novos: `scripts/04_tipologia_pontos_rnqa.py`, `galeria_common.py`, a segmentação por corpo d'água) filtram por `df[df["VALIDO_PARA_CALCULO"]]` antes de qualquer cálculo, nunca por remoção física da linha. Reexecutei os scripts 01→04 do zero e o total de linhas no CSV de saída continua 340, com 9 marcadas como inválidas — igual à contagem original.

**Gravidade:** N/A (sem problema).

### 1.2 Padronização de códigos RNQA (hífen/inconsistência)

**⚪ Cosmético — não encontrei o código que faz essa padronização.** Busquei em todos os scripts (`grep` por `strip`, `replace`, `upper`, `padroniza` na coluna RNQA) e não há nenhuma linha de normalização de código RNQA em lugar nenhum do pipeline atual. Investigando os dados: os 27 códigos RNQA no Excel bruto (`Dados tratados.xlsx`, aba DADOS_ANALISE) já são idênticos, byte a byte, aos 27 códigos no CSV final — sem hífen faltando, sem espaços, sem variação de maiúscula/minúscula. Ou seja, **hoje não há inconsistência para corrigir** — o dado de origem já está limpo nesse quesito.

Duas interpretações possíveis: (a) essa padronização foi feita manualmente na planilha Excel antes deste pipeline Python existir (fora do que consigo auditar em código), ou (b) a preocupação é sobre uma versão anterior dos dados que já foi corrigida na fonte. De qualquer forma, **não há código defensivo** — se uma atualização futura da planilha reintroduzir uma inconsistência (ex. "MA 7181 I 1" sem hífen ao lado de "MA-7181-I-1"), o pipeline vai tratá-los como 28 pontos RNQA distintos, silenciosamente, sem aviso.

**Recomendação:** adicionar uma normalização defensiva simples (`df["RNQA"] = df["RNQA"].str.strip().str.upper()`) em `carregar_dados()` — barato, sem risco, e fecha essa lacuna para o futuro.

### 1.3 Varredura de valores fisicamente implausíveis (além dos 9 já sinalizados)

Refiz a varredura completa (todas as 23 colunas numéricas, todas as 340 linhas, incluindo as já marcadas como inválidas) em vez de confiar na lista de 9.

**✅ Confirmado correto — os 9 registros marcados são exatamente os que têm valores negativos.** Encontrei negativos em `PROFUNDIDADE` (6 linhas), `VAZAO` (1), `SOLIDOS_DISSOLVIDOS` (2) e `SOLIDOS_SUSPENSOS` (1) — nove IDs únicos (`ITA-0023, 25, 27, 29, 31, 33, 70, 202, 292`), e **todos os nove** já estão com `FLAG_VALOR_INVALIDO=SIM`. Nenhuma linha válida (`VALIDO_PARA_CALCULO=True`) tem valor negativo em nenhuma coluna. `PH` está inteiramente dentro de 0–14.

**🟡 Moderado (novo achado) — `TRANSPARENCIA_AGUA` maior que `PROFUNDIDADE` em 70 de 87 linhas comparáveis (80%).** Fisicamente, a transparência (profundidade de Secchi) não pode exceder a profundidade total da coluna d'água — você não consegue enxergar mais fundo do que a água é funda. Isso é sistemático, não um outlier isolado (ex. `ITA-0109`: transparência=1,00m com profundidade=0,00m). Duas explicações possíveis:
  - `PROFUNDIDADE` neste dataset representa **profundidade de coleta da amostra** (comum em protocolos de campo — "0,00m" = amostra de superfície), não a profundidade total do rio no ponto. Nesse caso a comparação não faz sentido e não há problema real.
  - Ou há de fato uma inconsistência de unidade/definição entre as duas colunas.

  **Não tenho como decidir sozinho sem o dicionário de dados original da ANA/RNQA.** Recomendo confirmar a definição exata de PROFUNDIDADE com a fonte antes de decidir se isso é um problema de dado (que afetaria a interpretação de PROFUNDIDADE em qualquer gráfico que a usa) ou um não-problema.

**🟡 Moderado (já conhecido, mas vale registrar formalmente aqui) — `TEMPERATURA_AGUA = 9,74°C`** (`ITA-0088`, ponto MA-7181-I-4) é fisicamente implausível para um rio tropical no Maranhão (o resto da amostra fica entre 24-38°C). **Já está marcado** como outlier IQR (`OUTLIER_TEMPERATURA_AGUA=True`), então é visível para quem usa o dashboard — mas, como outliers IQR são mantidos nos cálculos por design (não removidos, só sinalizados), esse valor **continua entrando** em qualquer média/regressão/PCA que use TEMPERATURA_AGUA. Isso é consistente com a política do projeto (outliers sinalizados, não removidos), mas vale considerar se esse caso específico merece uma segunda flag (ex. `FLAG_VALOR_INVALIDO`) por ser fisicamente implausível, não só estatisticamente atípico.

  Também encontrei os outliers extremos de condutividade/sólidos dissolvidos/salinidade (pontos `ITA-0057, 0058, 0113`, todos do ponto MA-7191-IE-4, condutividade até 28.150 µS/cm — nível de água salobra) — **já marcados como outlier IQR** e, importante, **confirmei que nenhum deles entra na amostra complete-case usada no PCA/clustering** (faltam outros parâmetros ROBUSTO/MODERADO nessas linhas), então não distorcem o PCA. Só `ITA-0220` (o outlier já conhecido e tratado no script 03) está na amostra complete-case — ver §5.4 para o problema real relacionado a ele.

**Gravidade combinada da seção:** 2 moderados (verificação com a fonte sobre PROFUNDIDADE, e reconsiderar a temperatura de 9,74°C).

### 1.4 Investigação sistemática de censura por LOD nos parâmetros de cobertura Pouca

Contei valores únicos e frequência do valor mais comum para os 9 parâmetros Pouco, não só o par Fluoreto×Nitrito.

**✅ Confirmado, e mais abrangente do que o texto atual do dashboard sugere.** Três parâmetros têm exatamente 2 valores únicos (0,05 e 0,10) com 65% das amostras no valor 0,10 — o padrão clássico de "abaixo do LOD reportado como metade do LOD, ou no próprio LOD":

| Parâmetro | N | valores únicos | % no valor mais comum |
|---|---|---|---|
| FLUORETO_TOTAL | 20 | 2 | 65% |
| NITRITO | 20 | 2 | 65% |
| FOSFATO_TOTAL | 20 | 2 | 65% |
| BROMETO_TOTAL | 20 | 6 | 45% |

O texto atual da página 1 já cita corretamente **três** parâmetros (Fluoreto, Nitrito, Fosfato Total) — bate com o que encontrei, então essa parte já estava certa, não é só o par Fluoreto×Nitrito como a pergunta original supôs.

**⚪ Cosmético — falta mencionar `BROMETO_TOTAL`**, que mostra o mesmo padrão de forma mais fraca (6 valores únicos em vez de 2, mas ainda 45% concentrados em 0,10). Ele já aparece na tabela de "pares de atenção" da página 3/Galeria (par Cloreto×Brometo, N=20) mas a justificativa dada lá é só "N pequeno", não menciona a suspeita de censura por LOD. `SULFATO` (20 valores únicos em 20 amostras) e `VAZAO` (32 em 33) **não** mostram esse padrão — são dados contínuos genuínos, sem sinal de censura.

**Gravidade:** cosmético (o achado central já estava correto; falta só uma menção ao Brometo).

---

## 2. Análise univariada

### 2.1 Fórmula IQR e decisão de cálculo global

**✅ Confirmado correto.** `LIMITE_INFERIOR = Q1 - 1.5*IQR`, `LIMITE_SUPERIOR = Q3 + 1.5*IQR` — fórmula de Tukey padrão, implementada certa em `calcular_limites_iqr_globais()`.

**🟡 Moderado — a decisão de manter o cálculo global (não por corpo d'água) continua defensável, mas o contexto mudou e isso não está documentado em todo lugar novo.** A justificativa original (grupos RNQA×CORPODAGUA×PERIODO têm N=1-4, pequenos demais) continua válida — mas agora existe uma unidade de agregação intermediária (CORPODAGUA sozinho) que a página 2 já usa para filtros. Reverifiquei o N por corpo d'água: só RIO ITAPECURU (N=241) teria amostra decente para um IQR próprio; os outros 6 corpos (N=1 a 30) continuam pequenos demais. **A decisão de manter global está correta na prática**, mas:
  - A página 2 já documenta isso explicitamente ("Outliers calculados... sobre todas as amostras válidas do parâmetro — não recalculado para o recorte filtrado") — bom.
  - A Galeria (páginas 5a/5b/5c) **não tem essa mesma nota** em nenhum lugar — um usuário olhando o histograma de RIO ITAPECURU na Galeria não sabe que os outliers ali seriam os mesmos vistos em "Bacia toda".

**Gravidade:** moderado (decisão correta, documentação incompleta).

### 2.2 Estatísticas recalculam corretamente por corpo d'água (sem herdar valor da bacia)

**✅ Confirmado correto.** Testei o caminho de código: a página 2 usa `df_filtrado` (já filtrado por corpo d'água/RNQA/ano/período) tanto para a legenda do histograma (`serie.mean()`, `.median()`, `.std()`) quanto para o boxplot comparativo (`px.box` recalcula quartis a partir de `dados_comp`, que vem de `df_filtrado`). A Galeria usa `df_secao` (resultado de `_subset_por_corpo()`) em toda função de estatística. Não há nenhum valor pré-calculado para a bacia inteira sendo reaproveitado por engano — cada seção recalcula do zero a partir do subconjunto correto.

**Gravidade:** N/A (sem problema).

### 2.3 Critérios ROBUSTO/MODERADO/POUCO consistentes entre páginas

**✅ Confirmado correto, e estruturalmente impossível de divergir.** A classificação (`N≥250`→ROBUSTO, `50≤N<250`→MODERADO, `N<50`→BAIXO) é calculada **uma única vez**, em `scripts/01_univariate_outliers.py::classificar_cobertura()`, salva em `resumo_cobertura_parametros.csv`, e toda página lê essa classificação via `carregar_grupos_robusto_moderado_baixo()`/`carregar_resumo_cobertura()` — não há nenhuma segunda implementação do limiar em nenhuma página, Galeria ou script novo (confirmei via busca por `N_ROBUSTO`/`N_MODERADO`/`>= 250` em todo o projeto: só aparecem no script 01). Fonte única de verdade — não há como divergir por acidente.

**Gravidade:** N/A (sem problema).

---

## 3. Correlação

### 3.1 Pairwise deletion e N por célula

**✅ Confirmado correto na página 3 e no script 02** — `corr = df[todos].corr(method="pearson")` usa pairwise deletion nativo do pandas (cada par usa suas próprias linhas não-nulas, não descarta a linha inteira se qualquer outra coluna tiver NaN). O N por célula é calculado à parte, par a par (`df[[a,b]].dropna().shape[0]`), e mostrado no hover do heatmap — reflete o par específico, não o dataset inteiro.

**🟡 Moderado — o heatmap da Galeria (`galeria_common.figura_correlacao_heatmap`) não mostra N por célula**, só o valor de r. Ele usa a mesma lógica de pairwise deletion internamente (correto), mas a informação de N — crucial para julgar se um r=0,95 é confiável ou vem de 3 amostras — só existe no heatmap da página 3, não no da Galeria. Um usuário que só olha a Galeria não tem como saber, célula a célula, qual correlação está apoiada em N grande e qual está apoiada em N pequeno.

**Gravidade:** moderado.

### 3.2 Risco de comparações múltiplas

**✅ Confirmado: não há correção alguma (Bonferroni, FDR ou outra) em nenhum lugar do projeto**, e nunca houve, em nenhuma versão anterior — busquei por "bonferroni", "fdr", "comparações múltiplas" em todo o código-fonte e não há nenhuma menção.

Vale separar dois riscos diferentes que a matriz de correlação 23×23 (253 pares) cria:
1. **A matriz de correlação em si só mostra r (magnitude), não p-valor/significância** — não há uma afirmação formal de "significativo" sendo feita por célula, então o risco clássico de inflação do erro tipo I (múltiplos testes com α=0,05) não se aplica tecnicamente. O risco real aqui é mais brando: "olhar 253 números e destacar mentalmente os maiores" tem um viés de garimpagem de dados (*data dredging*), mesmo sem teste de hipótese formal.
2. **A regressão múltipla, sim, mostra p-valor e marca "significativo" com p<0,05** — e agora, com a segmentação por corpo d'água, esse mesmo teste roda potencialmente 7 vezes (uma por corpo d'água) para cada alvo (Turbidez, Vazão), sem nenhuma correção. Esse é o lugar onde o risco de comparações múltiplas é mais concreto e mais sério, porque há uma afirmação binária ("significativo" sim/não) sendo feita repetidamente.

**Recomendação:** não é preciso implementar correção estatística formal agora (Bonferroni é frequentemente conservador demais para análise exploratória), mas o relatório final do projeto deveria ter uma frase explícita reconhecendo essa limitação — principalmente para os p-valores de regressão, que são reaproveitados em múltiplos corpos d'água sem ajuste.

**Gravidade:** moderado.

### 3.3 Spearman — uso consistente ou incompleto?

**⚠️ Confirmado incompleto, exatamente como a pergunta original suspeitava.** Busquei todas as ocorrências de "spearman" no projeto: aparece **só** dentro de `galeria_common.py`, na função `_classificar()` que decide se um par é "Linear forte", "Monotônica não-linear" ou "Fraca/sem relação" para a grade de dispersão da Galeria. Spearman:
  - **Não aparece** no heatmap de correlação (nem o da página 3, nem o da Galeria) — ambos são Pearson puro.
  - **Não aparece** na seção "Dispersão: um parâmetro comparado com todos os outros" da página 3 — só Pearson (`dados[parametro_disp].corr(dados[outro])`, método padrão = Pearson).
  - **Só aparece** na classificação de tipo de relação da Galeria e na seção "Relações esperadas pela literatura" (que reusa a mesma função).

Isso significa que a mesma dispersão entre duas variáveis pode ser classificada como "Monotônica não-linear" na Galeria (porque ali Spearman é calculado) sem que a página 3 (que mostra o mesmo par, com o mesmo N, na seção de Dispersão) tenha como confirmar isso — porque lá não há Spearman disponível para comparar.

**Gravidade:** moderado (não é um erro de cálculo — o Spearman que existe está calculado certo — é uma inconsistência de cobertura entre páginas que discutem os mesmos dados).

---

## 4. Regressão múltipla

### 4.1 Pressupostos da regressão: normalidade, homocedasticidade, independência

**⚠️ Confirmado: só verificação visual, nunca formal, e uma lacuna de independência nunca mencionada.**

- **Normalidade dos resíduos:** só o histograma de resíduos (matplotlib, gerado em `salvar_resultado_regressao`). Nenhum teste formal (Shapiro-Wilk, Jarque-Bera, D'Agostino) em nenhum lugar do código.
- **Homocedasticidade:** só o gráfico "observado vs. previsto". Nenhum teste formal (Breusch-Pagan, White) em nenhum lugar.
- **Independência dos resíduos:** **nunca verificada, nem visualmente, nem formalmente** — e aqui há um problema estrutural, não só uma lacuna de teste: os dados são de **medidas repetidas** (os mesmos 27 pontos RNQA são revisitados em ~6 períodos, em média, conforme a própria página 4 documenta extensivamente). OLS assume resíduos independentes; com pseudo-replicação desse tipo, o esperado é que amostras do mesmo ponto RNQA tenham resíduos correlacionados entre si (um ponto cronicamente mais turvo que o modelo não captura vai ter resíduos positivos em todas as suas medições). Isso tende a deixar os erros-padrão dos coeficientes **artificialmente pequenos**, inflando a aparência de significância estatística (p-valores otimistas). Esse problema afeta **todas** as regressões do projeto — a original (script 02) e todas as novas, ao vivo, por corpo d'água.

**Recomendação:** não é preciso resolver isso nesta fase, mas é a limitação estatística mais substancial encontrada nesta auditoria, e nunca foi mencionada em nenhum texto do dashboard. Mínimo recomendado: uma frase explícita reconhecendo que os p-valores devem ser lidos com cautela por causa da estrutura de medidas repetidas. Se quiser ir além: `statsmodels` suporta erros-padrão robustos a cluster (`cov_type="cluster"`, agrupando por RNQA) com poucas linhas de mudança.

**Gravidade:** moderado (mas o mais importante da lista — é o único item que pode estar sistematicamente enviesando uma métrica hoje exibida ao usuário, o p-valor/"significativo").

### 4.2 Modelo "completo" (Turbidez, N=36) — overfitting

**✅ Confirmado, exatamente como a pergunta original antecipou — e os números atuais são piores do que o R²=0,44 citado.** Reli `output/regressao_metricas.csv`:

| | N | preditores | N/preditores | R² | R² ajustado | nº de condição | VIF máx |
|---|---|---|---|---|---|---|---|
| completo | 36 | 12 | **3,0** | 0,643 | **0,457** | 7.320 | 5,32 |

N/preditores = 3,0 está bem abaixo até da regra mais permissiva (5-10x). A queda de R² (0,643) para R² ajustado (0,457) — **18,6 pontos percentuais** — é exatamente a assinatura de overfitting: o R² bruto parece "impressionante", mas o ajustado (que penaliza o número de preditores relativo ao N) mostra que boa parte disso é ruído absorvido pelo modelo, não sinal real. VIF máximo de 5,32 também já cruza o próprio limiar que o projeto usa em outros lugares ("acima de ~5 sugere multicolinearidade relevante").

**🟡 Moderado (achado novo, efeito colateral de uma mudança anterior desta sessão) — o aviso que alertava sobre isso sumiu da interface.** Até a rodada anterior de mudanças, a página 3 tinha uma seção de regressão com um aviso automático ("N/preditores abaixo de ~5, tratar como exploratório") sempre que esse modelo era selecionado. Essa seção inteira foi removida da página 3 por pedido explícito. O modelo "completo" continua sendo mostrado — como imagem estática na Galeria (`regressao_TURBIDEZ_completo.png`, categoria "Regressão") — mas **sem nenhum aviso vivo**; o único contexto é o N e o número de preditores escritos no título da própria imagem (`fig.suptitle(...)`), que o usuário precisaria interpretar sozinho para perceber o problema de N/preditores.

**Recomendação:** ou (a) adicionar uma legenda/caption na Galeria especificamente para essa imagem, explicando a razão N/preditores e recomendando o modelo "núcleo robusto" em vez do "completo", ou (b) considerar descontinuar a exibição do modelo "completo" e manter só "núcleo robusto" (que tem N=305, razão=61×, mais confiável, ainda que com R²=0,11 — mais honesto).

**Gravidade:** moderado.

### 4.3 Exclusão de SALINIDADE aplicada consistentemente

**✅ Confirmado correto em todo lugar que ajusta uma regressão nova.** `EXCLUIR_DA_REGRESSAO = ["SALINIDADE"]` no script 02 original, e a mesma exclusão está hardcoded (`p not in ("SALINIDADE", alvo)`) tanto em `_regressao_disponivel_galeria()` quanto em `figura_regressao_corpo()` — os dois pontos onde a Galeria ajusta uma regressão nova, ao vivo, por corpo d'água. Não encontrei nenhum caminho de código que inclua SALINIDADE como preditor.

**Gravidade:** N/A (sem problema).

### 4.4 Fórmula do coeficiente padronizado (β)

**✅ Confirmado correto — X e y são padronizados, não só X.** Em `ajustar_ols()` (`scripts/_lib_analise.py`):
```python
y_z = (y - y.mean()) / y.std()
X_z = (dados[preditores] - dados[preditores].mean()) / dados[preditores].std()
modelo_padronizado = sm.OLS(y_z, X_z).fit()
```
Essa é a forma correta e padrão de calcular coeficientes padronizados (equivalente a β_i = b_i × DP(x_i)/DP(y), mas calculado via reajuste direto sobre variáveis já padronizadas — numericamente mais robusto e menos sujeito a erro de fórmula manual). Confirmei que essa função é compartilhada (não duplicada) entre o script 02 e a Galeria.

**Gravidade:** N/A (sem problema).

---

## 5. PCA e clustering (incluindo tipologia de pontos)

### 5.1 Padronização (z-score) antes do PCA

**✅ Confirmado correto e consistente nas três implementações** — `bloco_pca_clustering()` (script 02/03, amostra individual), `calcular_pca_clustering_live()` (recorte ao vivo por corpo d'água) e `scripts/04_tipologia_pontos_rnqa.py` (por ponto de coleta) usam todas `sklearn.preprocessing.StandardScaler()` da mesma forma (`fit_transform` sobre a matriz de variáveis, antes do PCA e do KMeans). Nenhuma das três pula a padronização ou usa uma variação diferente (ex. min-max).

**Gravidade:** N/A (sem problema).

### 5.2 Documentação da fragilidade amostral em todos os lugares

**✅ Confirmado presente em quase todo lugar — com uma exceção real.**
- Página 3, PCA/Clustering (bacia inteira, N=36): bloco extenso explicando N vs. regra de 5×variáveis. ✅
- Página 3, PCA/Clustering ao vivo por corpo d'água: mostra razão N/variáveis e rótulo "tratar como exploratório" quando abaixo de 5×. ✅
- Página 3, Tipologia dos pontos (N=26, 7 variáveis): bloco dedicado explicando a razão 3,7× e por que fica abaixo da referência de 5×. ✅
- **Galeria (`galeria_common.render_secao_corpo_dagua`), bloco de PCA/Clustering: mostra só `N=X, k=Y` — sem razão N/variáveis, sem rótulo "exploratório".** Essa seção reusa a mesma função de cálculo (`calcular_pca_clustering_live`) da página 3, mas a camada de apresentação da Galeria não herdou o mesmo texto de alerta.

**Gravidade:** moderado (a limitação está corretamente calculada e documentada em 3 de 4 lugares onde aparece; falta só na Galeria).

### 5.3 Método de seleção de k (silhouette) — range e possíveis erros de implementação

**✅ Confirmado sem erro de implementação; k=1 nunca é testado (correto — silhouette não é definido para k=1).** Todas as implementações começam o range em `k=2`. O teto varia:
- `bloco_pca_clustering` (script 02/03): fixo em `range(2, 7)`, seguro porque N ali é sempre ≥35.
- `calcular_pca_clustering_live` e `script 04`: `max_k = min(6, N-1)`, corretamente limitado para nunca testar k≥N.

**⚪ Cosmético — para corpos d'água pequenos, o teto de 6 ainda permite testar k relativo a N bem alto.** Rodei o cálculo para os corpos d'água menores: RIACHO PERITORO (N=12) testa até k=6 (2 pontos por cluster, em média, no pior caso testado). Na prática, o silhouette **nunca escolheu** um k tão fragmentado em nenhum dos corpos que testei — os k's escolhidos foram sensatos (RIO PERITORO k=5 de N=26; os demais k=2), então não houve um resultado ruim de fato, só um espaço de busca tecnicamente mais largo do que o ideal.

**Gravidade:** cosmético (nenhum resultado ruim observado; recomendo um teto mais conservador, ex. `k ≤ N/3`, por rigor, não porque algo quebrou).

### 5.4 Propagação da exclusão de ITA-0220 para a tipologia de pontos

**⚠️ Confirmado: NÃO foi propagada — e o efeito é mensurável, embora não mude a conclusão final.**

`scripts/04_tipologia_pontos_rnqa.py` agrega por **mediana** de todas as amostras válidas de cada ponto RNQA, sem excluir `ITA-0220` (que pertence ao ponto `MA-7191-IE-4` e foi excluído explicitamente do clustering original, no script 03, por ser um outlier extremo de condutividade/cloreto).

Recalculei a mediana do ponto MA-7191-IE-4 (N=21 amostras) com e sem ITA-0220:

| Variável | Com ITA-0220 | Sem ITA-0220 | Diferença |
|---|---|---|---|
| COND_ELETRICA_ESPECIFICA | 145,9 | 124,5 | **+17,2%** |
| SALINIDADE | 0,10 | 0,08 | **+25,0%** |
| demais 5 variáveis ROBUSTO | — | — | <1% |

Ou seja, incluir ITA-0220 infla a condutividade e salinidade medianas reportadas para esse ponto na tabela de "tipologia dos pontos" em 17-25% — um efeito real, não desprezível, e diretamente contrário à razão pela qual esse mesmo dado foi excluído do clustering original.

**Testei também se isso muda o resultado final do clustering** (não só o número reportado): rodei o pipeline completo do script 04 com e sem ITA-0220 excluído da agregação. **O cluster minoritário (6 pontos) é idêntico nos dois casos** — os mesmos 6 pontos RNQA (incluindo MA-7191-IE-4) ficam agrupados juntos com ou sem ITA-0220. A conclusão da tipologia (quais pontos se parecem) **não muda**.

**Gravidade:** moderado — é um bug real de inconsistência metodológica (a mesma decisão de exclusão deveria valer em toda análise que usa esses dados), com impacto mensurável no número reportado para aquele ponto especificamente, mas sem impacto na conclusão de agrupamento. Fix é uma linha (`df[df["ID_AMOSTRA"] != "ITA-0220"]` antes do `groupby` em `agregar_por_ponto()`).

---

## 6. Segmentação por corpo d'água

### 6.1 Critérios de "N insuficiente" aplicados de forma consistente

**✅ Confirmado correto — não há hardcode por corpo d'água.** `REGRESSAO_MIN_RATIO = 5` é uma constante única, usada da mesma forma em `_regressao_disponivel_galeria()` e `figura_regressao_corpo()`; a disponibilidade de PCA usa a mesma condição (`N > número de variáveis`) tanto na função compartilhada `calcular_pca_clustering_live()` quanto na checagem prévia `_pca_disponivel_galeria()`. Busquei por qualquer `if corpo == "..."` que pudesse indicar uma exceção hardcoded para um corpo d'água específico e encontrei só um caso — em `pages/4_Analise_Temporal_Multivariada.py`, usado exclusivamente para destacar visualmente a linha de RIO ITAPECURU no gráfico (linha mais grossa), **não** para nenhuma decisão estatística. As páginas `5b_Galeria_Rio_Itapecuru.py` (dedicada) e `5c_Galeria_Demais_Corpos_Dagua.py` (agrupada) são uma escolha de **organização de página**, pedida explicitamente antes, não um atalho estatístico — o corpo d'água em `5b` foi escolhido por já ter N suficiente na prática, não por um hardcode que bypassa a checagem de N.

**Gravidade:** N/A (sem problema).

### 6.2 Comparação entre corpos d'água usa critérios uniformes de exclusão

**✅ Confirmado correto, sem viés.** O boxplot comparativo (página 2, seção "Comparação entre corpos d'água") filtra por `VALIDO_PARA_CALCULO` **antes** de separar por corpo d'água — o mesmo critério de exclusão (FLAG_VALOR_INVALIDO) se aplica igualmente a todos os grupos. Nenhum corpo d'água tem outliers IQR removidos e outro não — a política do projeto (outliers marcados, nunca removidos de nenhum cálculo) é uniforme em todos os 7 corpos d'água.

**Gravidade:** N/A (sem problema).

---

## 7. Eixo temporal (PERIODO)

### 7.1 Uso consistente de PERIODO (sem resquício de CAMPANHA ou ANO isolado)

**✅ CAMPANHA: confirmado ausente de toda lógica de código.** Busquei "campanha" em todo o projeto — as únicas 3 ocorrências restantes são texto explicativo (página 1, explicando o que é uma campanha no contexto da coleta RNQA; `dashboard_common.tabela_periodos()`, docstring explicando por que CAMPANHA foi deliberadamente excluída) — nenhuma é um filtro, coluna usada em groupby, ou controle de UI. Não há resquício funcional.

**⚠️ Confirmado: ANO isolado ainda aparece, e contradiz a decisão documentada de usar PERIODO.** `scripts/03_dispersao_e_reclustering.py::scatter_tendencia_temporal()` gera 5 imagens estáticas ("Turbidez ao longo do tempo", etc.) plotando os parâmetros ROBUSTO **contra ANO**, não PERIODO. Essas imagens continuam sendo geradas e aparecem na Galeria (`5a_Galeria_Bacia_Toda.py`, categoria "Temporal"), sem nenhuma nota conectando isso à extensa justificativa que a página 4 dá para **não** usar ANO ("um mesmo período pode cair em dois anos-calendário..."). Um usuário pode ver esse gráfico na Galeria e tirar conclusões usando exatamente o eixo que o resto do projeto argumenta ser enganoso.

**Gravidade:** moderado.

### 7.2 Indicador de cobertura por período

**N/A — não há indicador para auditar.** A seção "Cobertura da rede" (que mostrava % de pontos visitados por período) foi removida do dashboard por pedido explícito em uma iteração anterior deste mesmo projeto. Confirmei que não há nenhum resquício dela em nenhuma página atual, e nenhuma métrica equivalente foi reintroduzida em nenhum lugar novo (segmentação por corpo d'água, Galeria). Não há, portanto, nada para verificar quanto a "matematicamente correto e atualizado" — a pergunta pressupõe uma funcionalidade que não existe mais no app.

---

## 8. Coerência geral do dashboard

### 8.1 Números/textos/código desatualizados

Busquei por frases específicas que ficariam erradas após as mudanças mais recentes (remoção da regressão da página 3, renumeração de seções, mudança do limite de 5 parâmetros): nenhuma ocorrência de "sempre usa a bacia inteira" (texto que ficou órfão quando a página 3 passou a ter regressão/PCA condicionados ao recorte), nenhuma referência a "2 a 5" parâmetros (texto do multiselect antigo da página 4), nenhuma menção a R²=0,44 ou "13 preditores" desatualizados.

**⚪ Cosmético — 2 imports mortos.** Rodei `pyflakes` no projeto inteiro: `dashboard_common.py` importa `NOMES_UNIDADES` e `rotulo` de `config.nomes_unidades` só para reexportar (`# noqa: F401`), mas nenhuma página de fato importa esses nomes *de* `dashboard_common` (todas importam direto de `config.nomes_unidades`) — reexportação sem uso. `scripts/04_tipologia_pontos_rnqa.py` importa `CORES` mas usa só `CORES_SEQUENCIA`. Sem efeito funcional, só limpeza.

**Gravidade:** cosmético.

### 8.2 Cobertura de casos-limite no AppTest

Revisei `tests/test_dashboard.py` (46 checagens atualmente, todas passando na reexecução).

**✅ Bem coberto:** corpo d'água com N muito baixo (RIO ALPERCATAS, N=1 — testado nas páginas 3 e 5c, confirma que regressão/PCA ficam indisponíveis com aviso, sem exceção); parâmetro sem dado suficiente num filtro (ponto MA-7185-I-9, onde Nitrato tem 0 períodos válidos — testado na página 4, confirma exclusão com aviso, sem gráfico vazio/enganoso); N moderado (RIO PERITORO — confirma que regressão/PCA aparecem normalmente).

**⚪ Cosmético — falta um teste explícito para "período sem nenhuma amostra dentro de um recorte específico"** (a lacuna vira `NaN` no gráfico de linha, conforme `agrupar_por_periodo()` documenta, e o Plotly lida com isso nativamente sem erro) — o comportamento existe e é são pela forma como o código está estruturado (reindex com NaN é padrão do pandas, sem tratamento manual arriscado), mas não há uma asserção automatizada confirmando isso especificamente. Risco de regressão futura aqui é baixo, mas o teste é barato de adicionar.

**Gravidade:** cosmético.

---

## Apêndice — metodologia desta auditoria

Todos os achados marcados "confirmado" foram verificados executando código Python contra os dados atuais (`output/*.csv`, recarregados a partir do Excel bruto quando relevante), não apenas lendo o código-fonte. Em particular:
- A varredura de implausibilidade (§1.3) rodou sobre as 340 linhas, não só a amostra "válida".
- O teste de propagação do ITA-0220 (§5.4) rodou o pipeline de clustering duas vezes (com e sem o outlier) e comparou as duas partições ponto a ponto.
- Os números de regressão (§4.2) vêm de uma leitura direta de `output/regressao_metricas.csv`, não de memória.
- A checagem de fonte única de verdade para ROBUSTO/MODERADO/BAIXO (§2.3) foi feita por busca textual de qualquer segunda implementação do limiar em todo o repositório, não só nas páginas óbvias.

Nenhuma mudança de código foi feita nesta etapa.
