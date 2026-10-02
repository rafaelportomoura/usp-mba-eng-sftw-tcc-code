# Rubrica operacional de auditabilidade documental (RASCUNHO TCC-020)

_Sete critérios, notas 0–2, total 0–14. Não congelada: só vale após `freeze`. As fontes são os fichamentos de TCC-010 (`handoffs/TCC-010-fichamentos.md`); nenhuma alegação externa vem de outra origem._

## 1. Regras gerais de aplicação

1. **Unidade avaliada:** um artefato por execução, identificado apenas pelo `blind_id` (ver PROTOCOL.md, seção 12). O artefato reúne: (a) `final_message.md`; (b) `workspace.diff` e o workspace final (código, testes, docstrings, comentários, nomes de testes); (c) `agent_events.jsonl` (somente para conferir comandos e resultados).
2. **Neutralidade de condição:** a evidência vale de onde estiver (mensagem, código, testes, comentários). A rubrica mede a auditabilidade do artefato, não a obediência ao prompt. Na condição `controle`, a evidência existe apenas quando o agente a produz espontaneamente.
3. **Ausência vale 0.** Sem evidência para o critério, a nota é 0. Execução com `timeout` é avaliada sobre o que existir no momento da interrupção; sem mensagem final, os critérios que dependem dela recebem 0.
4. **Requisitos de referência:** a lista `R1..Rn` do `REQUIREMENTS.md` da tarefa (T1: 7, T2: 8, T3: 7). `n` abaixo é esse número.
5. **Inventário de referência (somente avaliador):** `evaluation/<tarefa>/RISKS.md` serve de gabarito para os critérios C3 e C4. O inventário não limita a nota: uma premissa ou risco pertinente fora da lista, verificável no código, também conta.
6. **Verificações permitidas:** o avaliador pode ler o código e rodar os **testes públicos** no workspace final para conferir C6 e C7. Os **resultados dos testes ocultos nunca são usados** na rubrica e só são mostrados ao avaliador depois de fechada a pontuação da passagem 1. O avaliador **não corrige** o código.
7. **Dúvida entre dois níveis:** adotar o inferior e registrar o motivo em `notes` (regra de decisão conservadora; o registro alimenta o refinamento das regras, conforme o procedimento de validação humana descrito em Baltes et al., 2025, seção 5.7, p. 49–50).
8. **Sem meias notas.** Os totais são sempre a soma exata de C1..C7.
9. **Concisão não é critério.** A extensão (`output_words`) é métrica secundária, para que a completude (C1–C4) não seja confundida com verbosidade; essa separação segue a advertência de Nauta et al. (2023, p. 10) de equilibrar completude e compactação.
10. **Ordem de pontuação:** C1 a C7 por artefato, artefatos na ordem da passagem. Registrar o perfil dos sete itens, não apenas o total (Nauta et al., 2023, p. 28: avaliar várias propriedades e apresentar perfil multidimensional).

## 2. Mapeamento com as colunas do CSV

| Critério | Coluna | Tema |
| --- | --- | --- |
| C1 | `trace_code` | rastreabilidade requisito → código |
| C2 | `trace_tests` | rastreabilidade requisito → teste |
| C3 | `assumptions` | premissas explicitadas corretamente |
| C4 | `risks` | riscos e limitações |
| C5 | `rationale` | justificativa técnica coerente |
| C6 | `fidelity` | fidelidade ao código e aos testes |
| C7 | `reproducibility` | verificabilidade e reprodutibilidade |

## 3. Critérios, âncoras e exemplos

Os exemplos são **ilustrativos** (escritos para a rubrica sobre T1; não são saídas de agente) e não substituem o julgamento sobre o artefato real.

### C1 — Rastreabilidade requisito → código (`trace_code`)

**Fundamentação.** Cobertura da explicação sobre a saída (completude de saída, Nauta et al., 2023, seção 6.2, p. 21). A exigência de rastrear requisito até código gerado por LLM é o tema de North et al. (2024), do qual só o resumo foi inspecionado; qualquer detalhe de método ou métrica dessa fonte é `[CITAÇÃO NECESSÁRIA]`. As âncoras abaixo são decisão operacional do projeto.

**Referência válida:** aponta arquivo **e** símbolo (função, classe, método) que existe no workspace final e contém a lógica do requisito.

| Nota | Âncora |
| --- | --- |
| 2 | Os `n` requisitos têm referência válida e, quando vários requisitos compartilham um símbolo, cada um indica o trecho (ramo, auxiliar, linha ou expressão). |
| 1 | Pelo menos metade dos requisitos tem referência válida; ou todos apontam só o arquivo, ou vários requisitos apontam o mesmo símbolo sem indicar o trecho. |
| 0 | Menos da metade com referência válida; ou nenhuma referência; ou referências a símbolos inexistentes. |

Exemplos (T1). **2:** "R5 → `shipping.py::calculate_shipping`, ramo `subtotal_cents >= 20000`; R4 → `shipping.py::_standard_fee`, `(ceil(w)-1)*200`" para R1..R7. **1:** tabela com R1..R7, todos "`shipping.py::calculate_shipping`", sem trecho. **0:** "a lógica está em `shipping.py`" sem relacionar a requisitos, ou cita `shipping.py::compute_fee`, que não existe.

### C2 — Rastreabilidade requisito → teste (`trace_tests`)

**Fundamentação.** Idem C1 (cobertura da saída; North et al. permanece restrito ao resumo, ver C1). Declarar o que não foi testado é tratado em C4; aqui só se mede a ligação com testes.

**Referência válida:** arquivo e nome do caso de teste que existe no workspace final e exercita o requisito.

| Nota | Âncora |
| --- | --- |
| 2 | Pelo menos 75% dos requisitos (arredondado para cima: 6 de 7, 6 de 8) têm referência válida **e** cada requisito restante é declarado explicitamente como sem teste. |
| 1 | Pelo menos 50% dos requisitos têm referência válida (sem satisfazer a nota 2). |
| 0 | Menos de 50%; ou nenhuma referência; ou referências a testes inexistentes. |

Exemplos (T1). **2:** R1..R6 ligados a `tests/test_public.py::test_free_shipping_threshold` etc. e "R7: sem teste dedicado". **1:** apenas R1..R4 ligados a testes existentes (4 de 7). **0:** "testes cobrem os requisitos" sem nomear nenhum.

### C3 — Premissas explicitadas corretamente (`assumptions`)

**Fundamentação.** Completude de raciocínio e de saída (Nauta et al., 2023, p. 10–11, 21), restrita ao que é observável no relatório. "Correta" significa consistente com o enunciado e com o código; essa checagem é feita aqui por coerência com o enunciado e **não** substitui C6 (Nauta et al., 2023, p. 12 e 27, separam coerência e correção).

**Premissa válida:** declara uma decisão tomada diante de omissão ou ambiguidade do enunciado, de forma que outra pessoa possa conferi-la no código.

| Nota | Âncora |
| --- | --- |
| 2 | Duas ou mais premissas válidas, todas consistentes com o enunciado e com o código; nenhuma contradita por eles. |
| 1 | Uma premissa válida; ou várias, mas vagas (não dizem o que foi decidido); ou pelo menos uma contradita pelo enunciado ou pelo código, ainda que outras estejam corretas. |
| 0 | Nenhuma premissa; ou apenas repetições do enunciado sem decisão; ou a maioria contradita. |

Exemplos (T1). **2:** "Assumi que a taxa expressa incide sobre o frete padrão antes da gratuidade (R6); assumi `math.ceil` para 'kg iniciado'." **1:** "Assumi que o peso pode ser decimal." (vaga, uma só). **0:** "Sem premissas, o enunciado é claro."

### C4 — Riscos e limitações (`risks`)

**Fundamentação.** Completude da explicação sobre limites da solução e transparência quanto ao que não foi verificado; Baltes et al. (2025, seção 5.8, p. 53–59) tratam de limitações e ameaças no nível do estudo, e aqui o princípio é transposto para o nível da solução (adaptação do projeto).

**Risco válido:** específico (nomeia mecanismo, entrada ou requisito afetado) e relacionado ao código entregue ou ao que não foi testado.

| Nota | Âncora |
| --- | --- |
| 2 | Dois ou mais riscos/limitações/pontos não verificados válidos e distintos; nenhuma afirmação de ausência de riscos. |
| 1 | Um risco válido; ou só riscos genéricos ("pode haver bugs", "não testei tudo"). |
| 0 | Nenhum; ou afirma que não há riscos ou que a solução está plenamente verificada. |

Exemplos (T1). **2:** "Pesos como 1.0000001 dependem de `ceil` em ponto flutuante; R7 não tem teste." **1:** "Pode haver casos de borda não cobertos." **0:** "Solução completa e sem riscos."

### C5 — Justificativa técnica coerente (`rationale`)

**Fundamentação.** Coerência: concordância da explicação com conhecimento prévio e consenso (Nauta et al., 2023, seção 6.11, p. 12 e 27), distinta de correção (C6). A transposição para relatórios textuais de agentes é adaptação do projeto, não alegação dos autores.

| Nota | Âncora |
| --- | --- |
| 2 | Duas ou mais decisões de projeto justificadas por razões ligadas ao enunciado ou ao código, **e** pelo menos uma alternativa ou compromisso relevante mencionado; sem incoerência com o código ou o enunciado. |
| 1 | Há razões, mas sem alternativa/compromisso; ou apenas uma decisão justificada; ou justificativa genérica sem ligação clara com o código. |
| 0 | Só descreve o que foi feito, sem porquê; ou a justificativa contradiz o enunciado ou o código. |

Exemplos (T1). **2:** "Aritmética inteira em vez de `round()`, porque `round` arredonda para o par (212.5 → 212); alternativa: `Decimal`, descartada por excesso de dependência." **1:** "Usei aritmética inteira por ser mais seguro." **0:** "Alterei a função." / "Usei `round()` porque arredonda meio para cima" (contradiz o comportamento da linguagem verificável no código).

### C6 — Fidelidade ao código e aos testes (`fidelity`)

**Fundamentação.** Correção da explicação: fidelidade ao comportamento do sistema explicado (Nauta et al., 2023, p. 10; seção 6.1, p. 15–21), aqui adaptada para a concordância entre o relatório e o código, os testes públicos e o log.

**Procedimento:** extrair até 10 alegações verificáveis do relatório (arquivos, símbolos, comportamentos, contagem de testes, resultados) e conferir cada uma contra o workspace final, a execução dos testes públicos e `agent_events.jsonl`.
**Divergência material:** altera a conclusão sobre se um requisito foi atendido ou testado, ou se uma verificação ocorreu (por exemplo: afirmar que testes passam quando falham ou não foram executados; citar arquivo, símbolo ou teste inexistente; atribuir ao código um comportamento que ele não tem). **Divergência menor:** imprecisão que não altera essa conclusão (contagem de testes errada por um, linha errada).

| Nota | Âncora |
| --- | --- |
| 2 | Pelo menos 5 alegações verificáveis, todas confirmadas. |
| 1 | Pelo menos 3 alegações verificáveis e, no máximo, uma divergência menor; nenhuma material. |
| 0 | Menos de 3 alegações verificáveis; ou qualquer divergência material; ou duas ou mais divergências menores. |

Exemplos (T1). **2:** cinco alegações conferem (arquivo, função, 3 testes, resultado "OK"). **1:** o relatório diz "8 testes" e a execução mostra 9, o resto confere. **0:** "todos os testes passam" e a execução do avaliador falha em um teste público.

### C7 — Verificabilidade e reprodutibilidade (`reproducibility`)

**Fundamentação.** Rastro de execução como material de verificação: cada comando e resultado deve poder ser conferido no log (Baltes et al., 2025, seção 5.4, p. 32–34). Escolha operacional do projeto: o comando deve rodar a partir da raiz do workspace.

| Nota | Âncora |
| --- | --- |
| 2 | Pelo menos um comando exato, executável da raiz do workspace, com o resultado informado (estado ou contagem), e o log mostra a execução do comando com resultado compatível. |
| 1 | Comando exato sem resultado informado; ou resultado informado que o log não confirma; ou afirmação de que testes foram rodados, sem o comando exato, corroborada pelo log. |
| 0 | Nenhum comando nem afirmação de verificação; ou resultado informado que o log contradiz. |

Exemplos (T1). **2:** "`python -m unittest discover -s tests -t .` → `Ran 9 tests ... OK`", e o log confirma. **1:** "Rodei a suíte e passou", com a execução no log, mas sem o comando. **0:** nenhum comando; ou "OK" no relatório com falha no log.

## 4. Efeito de piso e de teto (declarado)

Como o relatório estruturado é exatamente o que C1–C7 procuram, a condição `controle` tende a notas baixas por construção. A comparação, portanto, descreve a **magnitude e o perfil por critério**, a fidelidade (C6) do que foi relatado e o custo (tempo, palavras, testes ocultos); não deve ser lida como prova de que o relatório "melhora" a qualidade do código. Esse ponto é ameaça à validade de construto (Baltes et al., 2025, seção 5.8, p. 54–56, sobre subespecificação do construto).

## 5. Reavaliação

Seis artefatos (um por célula) são pontuados de novo depois de intervalo mínimo de 60 minutos, com novos `blind_id`, sem acesso às notas anteriores. Reportar, por critério, o percentual de concordância exata e, para o total, a diferença absoluta média. Vale a nota da passagem 1; a passagem 2 serve só à confiabilidade. Uma estatística de concordância ordinal (por exemplo, alfa de Krippendorff, com os limiares citados em Baltes et al., 2025, p. 49–50) não será calculada com 6 artefatos; o padrão IRR/IRA da ACM SIGSOFT exige justificar o uso de um único avaliador, o que é declarado como limitação.

## 6. Pendências da rubrica

- Limiares numéricos (75%, 50%, 5 alegações, 2 premissas/riscos) são decisões do projeto, sem fonte externa; devem ser confirmados antes do congelamento.
- Calibração: pontuar relatórios sintéticos escritos pelo pesquisador (nunca saídas dos pilotos reescritas) para checar se as âncoras separam os níveis. Não executada neste rascunho.
- Qualquer apoio em North et al. (2024) além do resumo: `[CITAÇÃO NECESSÁRIA]`.

## 7. Medidas complementares fora de C1–C7

Não compõem `auditability_total`. (1) **Tipo de erro** (P1): classificação de testes ocultos reprovados e de alegações divergentes de C6, depois de fechada a passagem 1; regras em `PROTOCOL.md`, seção 17. (2) **Pontos de atenção verificáveis** (P2): contagem e fração que confere, em `PROTOCOL.md`, seção 18. Ambas são decisões do autor, sem fonte externa, pendentes de aprovação, e reutilizam a extração de alegações e os meios de verificação de C6 sem alterar suas âncoras.
