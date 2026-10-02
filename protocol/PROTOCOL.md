# Protocolo do experimento de auditabilidade (RASCUNHO TCC-020)

_Status: **RASCUNHO, NÃO CONGELADO.** Sem versão, sem hashes finais, sem `FREEZE.json`. O congelamento só ocorre depois da liberação dos oráculos pelo revisor independente (`handoffs/TCC-030-review.md`) e do preenchimento de `config/execution_config.json`. Fontes metodológicas: fichamentos de TCC-010. Especificação-mãe: `EXPERIMENT.md` e `PLAN.md` do repositório do TCC. Decisões do autor incorporadas em 2026-10-02: Q03=A (tipo de estudo e normas, seção 22), Q04=A (ordem em blocos com limitação, seção 6), Q06=B (medida de auditabilidade do controle, seção 21). Decisões adicionais de 2026-10-02: Q08 (registro de revisão de IA, seção 20), Q09=A (Baltes v8, seção 24), Q10=A (avaliador único, seções 12 e 14), Q11 (modelo `gpt-5.5`, esforço `medium`, seção 19), Q12.1=A (limiares sem apoio nas fontes inspecionadas, seção 23) e Q12.2=B (reavaliação ≥ 24 h, seção 12). Nada foi congelado: `freeze` não foi executado e não há hashes finais._

## 1. Pergunta de pesquisa

Em tarefas de desenvolvimento de complexidade crescente, a exigência de explicações estruturadas no prompt aumenta a auditabilidade documental dos artefatos produzidos pelo Codex, sem reduzir sua correção funcional?

"Explicação" é a justificativa externa e verificável contida no relatório final; não se alega acesso ao raciocínio interno do modelo, e nenhum prompt solicita cadeia de pensamento.

## 2. Hipóteses

Delineamento descritivo, sem testes de significância (3 repetições por célula; ver seção 13).

- **H1 (auditabilidade).** Em cada tarefa e no conjunto, a mediana do escore de auditabilidade (0–14) na condição `explicacao` é maior que na condição `controle`.
- **H2 (correção funcional).** A mediana da proporção de testes ocultos aprovados em `explicacao` não é inferior à de `controle` em mais de 0,10. O limiar 0,10 é **decisão metodológica do autor** (Q12.1=A): não foi localizado apoio nas fontes inspecionadas para esse valor (seção 23, item L7). Será relatada também a diferença observada com seu intervalo (mínimo–máximo), para que o leitor aplique outra margem.
- **Leitura de H1.** O tratamento coincide em parte com o que a rubrica mede (ver `RUBRIC.md`, seção 4); por isso o resultado de interesse é a magnitude, o perfil por critério, a fidelidade (C6), o custo e a medida de pontos de atenção do artefato sem relatório estruturado (seção 21, Q06=B), e não a mera existência de diferença.
- **Tipo de estudo (Q03=A).** Benchmarking no sentido de Baltes et al. (2025), com avaliação por humano (o autor) e **sem LLM avaliador**; mapeamento dos itens exigidos na seção 22.

Classificação (PLAN.md): pesquisa aplicada, explicativa, abordagem mista, experimento controlado com artefatos de software; unidade de análise = execução independente do agente em uma tarefa e condição.

## 3. Variáveis

| Tipo | Variável | Operacionalização |
| --- | --- | --- |
| Independente | `condition` | `controle` ou `explicacao`; difere somente pela exigência do relatório (seção 5) |
| Dependente principal | `auditability_total` | soma de C1..C7 (0–14), `RUBRIC.md` |
| Secundária complementar | `ap_*` (seção 21) | pontos de atenção verificáveis do artefato sem relatório estruturado; não compõem `auditability_total` |
| Secundárias | `hidden_tests_passed/total` | testes ocultos aprovados, executados pelo harness em cópia do workspace |
| | `duration_s` | segundos entre início e fim da sessão do agente |
| | `output_words` | palavras (`\w+`) da mensagem final, função `protocol.records.count_words` |
| Controle | modelo, `codex_version`, parâmetros, ambiente, `baseline_hash`, timeout, contexto inicial | constantes; registrados em `config/execution_config.json` |
| Estratificação | `task_id` | T1 baixa (7 req.), T2 média (8 req.), T3 alta (7 req.) |
| Não controlada | não determinismo do agente | fonte de variabilidade reconhecida; repetições (Baltes et al., 2025, seção 5.5, p. 37–38) |

## 4. Tarefas

`t1_shipping` (corrigir frete), `t2_order_pricing` (refatorar preços), `t3_inventory_reservation` (reserva de estoque). Enunciados em `tasks/*/REQUIREMENTS.md`. Workspace do agente = baseline + `REQUIREMENTS.md` + `tests/` (testes públicos). Oráculos, soluções de referência e `RISKS.md` nunca entram no workspace (detector de vazamento do harness).

## 5. Condições e prompts

Arquivos: `prompts/controle.md` e `prompts/explicacao.md`. O prompt é **único para as três tarefas** (o conteúdo específico está em `REQUIREMENTS.md`) e é enviado byte a byte, sem substituição de variáveis; `prompt_hash` = SHA-256 desses bytes.

- `explicacao` = `controle` + um bloco final "Relatório final obrigatório" (resumo; premissas; riscos, limitações e pontos não verificados; justificativa técnica e alternativas; tabela requisito → arquivo/símbolo → teste; comandos e resultados).
- A implementação, os testes, as restrições, o tempo e o formato da entrega são idênticos. O teste `test_explicacao_is_controle_plus_report_block` garante que `explicacao` começa exatamente com o texto de `controle`.
- Os prompts não mencionam testes ocultos, não pedem cadeia de pensamento ("passo a passo", "raciocínio", "pense") e pedem apenas conteúdo verificável. Testes automáticos conferem isso.

## 6. Ordem de execução

- Manifesto: `manifest.draft.json`, gerado por `python3 -m protocol.cli manifest`. Semente **20261002**; `random.Random(semente)` com Fisher-Yates sobre `rng.random()` (sequência estável entre versões do Python).
- 18 execuções = 3 tarefas × 2 condições × 3 repetições, em **aleatorização restrita por blocos**: bloco A (R01–R12: repetições 1 e 2 de todas as células, embaralhadas) e bloco B (R13–R18: repetição 3, embaralhadas). O número da repetição segue a ordem cronológica dentro da célula.
- **Fallback de 12:** bloco A inteiro (R01–R12), 2 repetições por célula, mesmos `run_id`. Como o bloco A vem primeiro, parar após R12 já é balanceado. A decisão de seguir para o bloco B é tomada **depois de R12 e antes de ver qualquer pontuação**, só pelo tempo restante. A restrição por blocos é uma escolha deste protocolo, **confirmada pelo autor (Q04=A)**; a especificação diz apenas "ordem aleatorizada com semente", e o desvio fica declarado.
- **Limitação declarada (Q04=A).** Como a repetição 3 vem sempre por último (R13–R18), o número da repetição fica confundido com o tempo: não é possível separar um efeito de "repetição" de deriva do ambiente (por exemplo, atualização do modelo ou do serviço no meio do dia ou entre dias). A ordem dentro de cada bloco é aleatória, então tarefa e condição não ficam confundidas com o tempo dentro do bloco; o confundimento é restrito à repetição. **Como será reportada:** (i) a ordem de execução e `started_at` de cada execução entram na tabela de resultados; (ii) os resultados são apresentados por repetição (1, 2, 3), além do agregado, de forma descritiva e sem teste de tendência; (iii) o resultado do bloco A (12 execuções, o fallback) é mostrado separado do conjunto de 18, para o leitor ver se a repetição 3 muda o quadro; (iv) qualquer diferença da repetição 3 é descrita como "repetição ou deriva, indistinguíveis neste desenho"; (v) a regra de desvio da seção 8 (mudança de versão do modelo) continua valendo.
- Execução sequencial na ordem do manifesto, sem reordenar nem pular.
- Cada execução: workspace novo (`python3 -m harness.cli prepare`), sessão nova do Codex, sem memória, histórico ou conversa compartilhados, sem intervenção humana, mesma configuração, timeout de **12 minutos (720 s)**. Avaliação dos testes públicos e ocultos pelo harness (`harness.cli evaluate`) logo após a sessão. A pontuação pela rubrica só começa depois que todas as execuções terminam.
- Pilotos (um por condição) ocorrem em TCC-040, com identificadores `P1` e `P2`, fora da amostra.
- **Cronograma da avaliação (Q12.2=B).** (1) Dia 1 (sprint): execuções definitivas (TCC-050), depois pontuação da **passagem 1** de todas as execuções concluídas, com data/hora de cada pontuação (TCC-060). (2) A partir de 24 h depois da **última** pontuação da passagem 1, de preferência no dia seguinte e **fora do sprint de um dia**, a **passagem 2** dos 6 artefatos, com novas datas/horas. (3) A consolidação (TCC-070) produz a análise principal (H1, H2, perfis) a partir da passagem 1, que é a nota válida; a tabela de reavaliação é acrescentada quando a passagem 2 existir, e o texto final (TCC-080) só afirma confiabilidade intra-avaliador depois dela. Ajuste de `TASKS.md`/`PLAN.md` ao cronograma é do coordenador (pendência na seção 16).

## 7. Tratamento de falhas e timeout

| `exit_status` | Definição | Tratamento |
| --- | --- | --- |
| `completed` | o agente encerrou a sessão antes de 720 s | resultado válido |
| `timeout` | a sessão foi interrompida em 720 s | **resultado válido**; avaliar o workspace e a mensagem existentes no momento da interrupção; sem mensagem final, os critérios dependentes recebem 0; não repetir |
| `agent_error` | o agente terminou por recusa, erro próprio ou desistência, sem causa externa | resultado válido; não repetir |
| `infra_failure` | causa externa ao agente: indisponibilidade ou erro de autenticação/cota do serviço, queda do Codex antes da primeira ação do agente, defeito do harness, falta de disco, queda de energia | **excluir a tentativa e repetir** no mesmo `run_id`, com workspace novo e o mesmo prompt |

Regras:

- A classificação como `infra_failure` exige evidência no log (mensagem de erro do serviço ou da ferramenta) e é decidida **antes** de examinar a qualidade do que a tentativa produziu. Sem evidência, vale `agent_error` ou `timeout`.
- Cada tentativa excluída gera uma linha em `runs/exclusions.jsonl`: `run_id`, `attempt`, `detected_at`, `classification`, `evidence_path`, `justification`. O log completo da tentativa é preservado.
- No máximo 2 repetições por `run_id`; esgotadas, registrar como bloqueio e reportar, sem substituir a execução por outra.
- Lentidão do serviço que cause `timeout` não é distinguível de lentidão do agente e permanece como `timeout` (limitação).

## 8. Critérios de exclusão da análise

Excluídos, com registro e preservação dos logs: (a) pilotos; (b) tentativas `infra_failure`; (c) execuções com violação do protocolo detectada: `prompt_hash` ou `baseline_hash` diferente do congelado, vazamento apontado pelo detector, intervenção humana durante a sessão, configuração diferente da congelada. Violação atribuível ao operador ou à infraestrutura gera repetição justificada; mudança de versão do modelo no meio do estudo interrompe a coleta e é reportada como desvio.

**Não** são motivos de exclusão: baixa qualidade, falha em testes ocultos, timeout, ausência do relatório na condição `explicacao` (registrar `nao_conformidade_prompt` em `notes`; a rubrica avalia o artefato como entregue).

## 9. Itens de relato exigidos por Baltes et al. (2025, v8)

| Item (seção da fonte) | Onde fica registrado |
| --- | --- |
| Papel do LLM, nome e versão exata do modelo, versão do Codex (5.1, 5.2; p. 18–22) | `config/execution_config.json` (`model`, `agent`); colunas `model`, `codex_version` e `codex_interface` (CLI ou API; seção 19) |
| Parâmetros de geração e valores padrão, data de execução (5.2; p. 21–22) | `generation_parameters`; `execution.date_*`; coluna `started_at`. Parâmetro não exposto: `nao_exposto` e limitação declarada |
| Prompts completos, histórico de revisão, estratégia (5.3; p. 25–28) | `prompts/*.md` (zero-shot, texto integral), `prompts.prompt_development_history`; hashes em `FREEZE.json` |
| Configuração do agente (ferramentas, sandbox, arquivos de contexto) (5.3; p. 28) | `agent.*` e `agent_config_hash` |
| Logs de interação e rastro de execução, formato aberto e versão da ferramenta (5.4; p. 32–34) | `runs/<run_id>/` (seção 10) |
| Métricas justificadas, repetição, estatística descritiva (5.5; p. 37–38) | seções 3, 6 e 13 |
| Validação humana com regras de decisão (5.7; p. 49–50) | `RUBRIC.md`, seções 1 e 5 |
| Ausência de modelo aberto como linha de base e demais ameaças (5.6, 5.8; p. 44–45, 54–56) | seção 14 |

O enquadramento do estudo no tipo Benchmarking e o mapeamento da matriz de Baltes et al. (Tabela 3) estão na seção 22; esta tabela detalha apenas os itens de relato.

## 10. Esquema dos dados e dos logs

- Registro consolidado: `schema/run_record.schema.json` (JSON Schema) e `schema/results_header.csv`. Colunas: `run_id, task_id, condition, replicate, model, codex_version, codex_interface, prompt_hash, baseline_hash, started_at, duration_s, exit_status, hidden_tests_passed, hidden_tests_total, output_words, trace_code, trace_tests, assumptions, risks, rationale, fidelity, reproducibility, auditability_total, err_*, claims_checked, claimdiv_*, rp_*, ap_decisions, ap_risks, ap_links, ap_confirmed, ap_from_summary, notes` (ordem exata em `schema/results_header.csv` e no esquema; `err_*`, `claimdiv_*`, `rp_*` e `ap_*` são definidos nas seções 17, 18 e 21). A coluna `started_at` consta de `EXPERIMENT.md`; foi mantida.
- Reavaliação: `schema/reevaluation_header.csv` (`blind_id, run_id, pass, scored_at`, sete itens, total, `notes`).
- Validação: `python3 -m protocol.cli validate results/results.csv` (stdlib; esquema + soma dos itens + testes ocultos ≤ total + balanceamento 3×6 ou 2×6 + consistência com o manifesto + um `prompt_hash` por condição e um `baseline_hash` por tarefa).
- Por execução, `runs/<run_id>/` deve conter: `prompt.txt` (bytes enviados), `agent_events.jsonl` (log nativo do Codex, com a versão da ferramenta), `final_message.md`, `workspace.diff`, `prepare.json`, `evaluation.json` (harness) e `run_meta.json`. `protocol.records.check_run_dir` lista ausências. Hoje o harness **não** invoca o Codex; o executor da sessão, que gera `agent_events.jsonl` e `run_meta.json`, é pendência (seção 16).

## 11. Execução da avaliação

Testes ocultos aplicados uniformemente pelo harness; o avaliador não corrige código. Rubrica aplicada pela passagem 1 sobre as 18 (ou 12) execuções em ordem aleatória e identificadores neutros (seção 12).

## 12. Avaliação cega e reavaliação

- Identificadores neutros `S01..S24`, sorteados com `random.Random(semente + 1)` (`python3 -m protocol.cli blind`). Nenhum codifica tarefa, condição, repetição ou ordem de execução. A chave `blind_id → run_id` fica fora do alcance do avaliador até o fim da pontuação.
- Passagem 1: todas as execuções concluídas, em ordem sorteada.
- Passagem 2: 6 artefatos, **um por célula**, escolhidos por sorteio entre as concluídas, com **novos** `blind_id`, em ordem sorteada, **no mínimo 24 h depois** da pontuação do mesmo artefato na passagem 1 (Q12.2=B; `manifest.MIN_REEVAL_INTERVAL_H`) e sem acesso às notas da passagem 1. O intervalo é de decisão do autor, escolhido para reduzir o efeito de memória; como os artefatos não mudam entre passagens, o argumento contra intervalos longos não se aplica (Laenen et al., 2006, resumo e introdução, p. 1–2, que descrevem o dilema sem prescrever valor). O valor de 24 h é decisão do autor, sem apoio numérico localizado nas fontes inspecionadas (seção 23, item L8).
- **Registro das duas passagens.** Cada linha de `schema/reevaluation_header.csv` leva `pass` (1 ou 2) e `scored_at` em ISO 8601 com data, hora e fuso (`Z` ou ±hh:mm) da pontuação daquele artefato naquela passagem. O validador (`records.validate_reevaluation`, `python3 -m protocol.cli reeval ARQUIVO.csv`) recusa: `scored_at` sem hora ou sem fuso, `blind_id` repetido (a passagem 2 usa novos), reavaliação sem a passagem 1 correspondente, **intervalo inferior a 24 h** por artefato, notas fora de 0–2, total diferente da soma, e passagem 2 que não tenha exatamente um artefato por célula.
- **Entre as passagens.** Vale a regra 6 de `RUBRIC.md` (resultados dos testes ocultos nunca são usados na rubrica) e o avaliador não consulta as notas da passagem 1. Como a passagem 2 vem depois de ele ter visto os resultados ocultos e classificado erros (seção 17), isso é uma limitação adicional de contaminação, declarada na seção 14.
- Os artefatos entregues ao avaliador removem metadados (tarefa, condição, repetição, `run_id`, horários); o gerador desses pacotes é pendência.
- **Limite do cegamento:** a presença da estrutura de relatório revela a condição; o cegamento é parcial e protege apenas contra viés por rótulo e por ordem. O avaliador é o próprio pesquisador.
- Medidas (`descriptive.reevaluation_summary`): **distribuição das notas 0/1/2 por critério em cada passagem** e matriz passagem 1 × passagem 2 (Baltes et al., 2025, p. 38: relatar a distribuição por item, porque a agregação esconde discordância), além do percentual de concordância exata por critério, da diferença absoluta média por critério e da diferença absoluta média do total; intervalo em horas por artefato. Todas serão relatadas, também as desfavoráveis. Nenhuma estatística de concordância ordinal com n = 6. Vale a nota da passagem 1.
- **Avaliador único (Q10=A).** O autor é o único avaliador e o declara como limitação: sem avaliador externo, sem estatística de concordância inter-avaliador (o suplemento IRR/IRA da ACM admite avaliador único com justificativa; justificativa: praticidade e ausência de avaliador técnico disponível) e com cegamento parcial, porque o avaliador conhece a hipótese e a presença do relatório revela a condição. Mitigações: identificadores neutros, ordem aleatória, regra de decisão conservadora e a reavaliação intra-avaliador de 6 artefatos.

## 13. Análise (TCC-070)

Mediana, mínimo e máximo por tarefa, condição e conjunto; diferenças entre condições; perfil por critério; resultados por repetição e bloco A separado do conjunto (limitação da seção 6); medida de pontos de atenção do artefato por condição, com e sem o resumo livre (seção 21). Sem testes de significância, o que difere da recomendação de Baltes et al. (2025, p. 37–38) de usar testes inferenciais com tamanhos de efeito; a justificativa é a amostra de 3 por célula e ela é declarada como limitação.

## 14. Limitações e ameaças declaradas

Um único agente e uma única configuração; sem modelo aberto como linha de base (Baltes et al., 2025, seção 5.6); tarefas artificiais e amostra pequena; sem generalização estatística; avaliação pelo próprio pesquisador, sem avaliador externo e com cegamento parcial; oráculos e referências escritos pelo mesmo agente que construiu as tarefas (handoff TCC-030); explicações pós-hoc possivelmente não fiéis ao processo interno; evolução do serviço e do modelo ao longo do tempo; rubrica com efeito de piso na condição `controle` (C1–C7 e `rp_*` favorecem `explicacao` por construção; a medida `ap_*` da seção 21 reduz, mas não elimina, esse efeito); repetição 3 sempre por último, confundindo repetição e deriva do ambiente (seção 6); reavaliação intra-avaliador apenas, em 6 artefatos, com o avaliador já conhecedor dos resultados ocultos na passagem 2 (o intervalo de 24 h reduz o efeito de memória sem eliminá-lo); avaliador único, **sem avaliador externo**, e **cegamento parcial** (Q10=A, seção 12); limiares da rubrica e do protocolo sem apoio nas fontes inspecionadas (seção 23); a rubrica de qualidade de código (por exemplo, refatoração em T2) não é verificável automaticamente. Ameaças organizadas conforme Baltes et al. (2025, seção 5.8, p. 54–56): externa, interna, de construto, confiabilidade. O uso do checklist de experimentos da ACM SIGSOFT é apenas por analogia, porque o padrão exige participantes humanos (fichamento TCC-010, seção 4).

## 15. Congelamento

Comando documentado e implementado, **não executado neste rascunho**:

```
python3 -m protocol.cli freeze --release-ref PATH_DO_RELATORIO_DE_LIBERACAO --confirm-oracles-released [--version v1.0.0]
python3 -m protocol.cli freeze --dry-run     # apenas lista precondições; não calcula hashes
python3 -m protocol.cli verify-freeze        # confere arquivos contra FREEZE.json
```

Precondições: relatório de liberação existente; confirmação explícita; `config/execution_config.json` sem `null` e com os campos de interface do Codex preenchidos e válidos (seção 19); manifesto válido (18 e fallback 12); ausência prévia de `FREEZE.json`. Efeito: `FREEZE.json` (versão, data, semente, SHA-256 de PROTOCOL, RUBRIC, `taxonomy.py`, prompts, esquema e configuração, e `baseline_hash` de cada tarefa via `harness.workspace.baseline_hash`) e `manifest.json` com os hashes de prompt. Mudança posterior em qualquer arquivo listado reabre TCC-020.

## 16. Pendências para congelar

1. Liberação dos oráculos pelo revisor independente (TCC-030-review).
2. Preencher `config/execution_config.json` (modelo, versão e interface do Codex, flags, parâmetros, comando de invocação, diretório de trabalho, sandbox, aprovação, rede, data), com o que a própria execução reportar.
3. Construir o executor da sessão do Codex no harness (TCC-040/050): captura de `agent_events.jsonl`, tempo, timeout, `run_meta.json`. Não existe hoje; não se afirma formato de log nem flags da ferramenta.
4. Construir o gerador de pacotes anonimizados e o consolidador CSV (TCC-060/070).
5. Confirmar: ~~limiar de H2, restrição por blocos, intervalo de 60 min, limiares numéricos da rubrica~~ (decididos: restrição por blocos em Q04=A; H2 e limiares em Q12.1=A, seção 23; intervalo ≥ 24 h em Q12.2=B), taxonomia e mapa padrão de erros (seção 17) a contagem operacional de pontos de atenção (seção 18) e a do artefato sem relatório (seção 21); calibrar a rubrica com relatórios sintéticos. Limiares da Q05 (75%, 50%, 5 alegações, 2 premissas/riscos): inalterados, declarados como decisão do autor na seção 23; o plano de busca (`handoffs/Q05-plano-de-busca.md`) **não foi executado**.
7. Gerador de pacotes anonimizados deve produzir a visão do artefato sem relatório estruturado (seção 21) e o consolidador deve gravar as colunas `ap_*`.
8. Itens do mapeamento da seção 22 marcados como lacuna.
9. Copiar `author_choices` (Q11) para `model.name` e `generation_parameters.reasoning_effort` ao criar `execution_config.json`, preencher o restante com o que a execução reportar e só então congelar (seção 19).
10. Atualizar `TASKS.md`/`PLAN.md` ao cronograma de duas passagens (seção 6); pendência do coordenador, não alterada aqui.
11. Registro de revisão de IA: a declaração do autor cobre o repositório até onde ela foi feita; alterações posteriores ao commit `f934ab8` exigem nova confirmação (seção 20).
12. Conferir o DOI publicado de Baltes et al. antes da entrega final (seção 24).
6. Resolver lacuna North et al. (2024): texto integral não inspecionado, `[CITAÇÃO NECESSÁRIA]` para qualquer apoio além do resumo.

## 17. Tipos de erro (P1, pedido do professor)

Pergunta qualitativa adicional: **o tipo de erro muda quando o agente explica?** Análise exclusivamente descritiva (seção 13); sem teste de significância e sem hipótese confirmatória. Origem: revisão do professor (`handoffs/PROFESSOR-REVIEW.md`, P1).

**Status das decisões.** A taxonomia, o mapa padrão e as regras abaixo são **decisões do autor, sem fonte externa, pendentes de aprovação antes do congelamento.** Não se atribui a elas apoio em Baltes et al. nem em Nauta et al.; se o autor desejar apoio bibliográfico, ele deve ser buscado nos fichamentos e citado depois (`[CITAÇÃO NECESSÁRIA]` até lá). A taxonomia foi derivada a priori, sem execuções, dos requisitos R# de `tasks/*/REQUIREMENTS.md` e dos defeitos listados em `evaluation/*/RISKS.md`.

| Tipo (valor) | Definição | Requisitos de origem |
| --- | --- | --- |
| `validacao_entrada` | entrada inválida aceita, rejeitada com exceção errada ou rejeitada tarde demais | T1 R1–R3; T2 R1; T3 R1 |
| `regra_negocio` | regra de cálculo, limite, precedência ou normalização aplicada incorretamente | T1 R4–R5; T2 R2–R5 |
| `arredondamento_numerico` | arredondamento, tipo numérico (ponto flutuante, `round` bancário, `ceil`) ou precisão | T1 R6 (e `ceil` em R4); T2 R6 |
| `atomicidade_estado` | efeito parcial, mutação de entradas, compartilhamento de referência, estado interno exposto | T2 R7; T3 R2, R6 (cópia), R7 |
| `idempotencia_conflito` | repetição de chave (replay) ou conflito de chave tratados incorretamente | T3 R4–R5 |
| `contrato_api` | assinatura, chaves, formato ou tipo do retorno e nomes públicos | T1 R7; T2 R8; T3 R3 |
| `outros` | nenhum dos anteriores serve; exige justificativa textual | n/a |
| `relato_verificacao` | **só alegações:** divergência sobre arquivo, teste, comando, contagem ou resultado, que não trata do comportamento de um requisito | n/a |

Concorrência e threads não são requisito de nenhuma tarefa (`RISKS.md` de T3, item 7), por isso não há tipo próprio. Um tipo `idempotencia_conflito` cobre o que o enunciado de T3 chama de idempotência e conflito de chave.

**Regras de classificação de cada teste oculto reprovado.**

1. Universo: todo teste oculto que não passou, inclusive os **não executados** (`hidden_not_run_tests`), isto é, `hidden_tests_total - hidden_tests_passed`. Cada um recebe **exatamente um** tipo; a soma das colunas `err_*` deve igualar esse número (o validador recusa a divergência).
2. Tipo padrão: `protocol/taxonomy.py` (`default_error_type`), função do nome `test_rN_...` e da tarefa: o tipo do requisito RN, com exceções por teste quando o mecanismo difere (por exemplo, `test_r4_fractional_weights_round_up` é `arredondamento_numerico`). O mapa é fixado **antes** das execuções e entra nos arquivos congelados.
3. Substituição: o avaliador pode trocar o tipo padrão só com justificativa de uma frase em `error_classification.json` (campo `override_reason`). Teste sem mapa (nome fora do padrão `test_rN_`) é classificado manualmente com justificativa. `outros` exige justificativa.
4. Um teste, um tipo: se dois tipos parecem aplicar-se, vale o do requisito violado; a dúvida vai em `notes`.
5. Momento: os resultados dos testes ocultos só são vistos depois de fechada a pontuação da passagem 1 (`RUBRIC.md`, regra 6). A classificação dos testes reprovados é feita **depois**, sabendo a condição, pois não retroalimenta a rubrica.

**Regras de classificação das alegações do relatório que divergem do código (somente condição `explicacao`).**

1. Universo: as alegações verificáveis já extraídas em C6 (até 10; `claims_checked`). Conta apenas **divergência material** conforme `RUBRIC.md` (C6); divergência menor não é classificada.
2. Tipo: o mecanismo que a alegação atribui incorretamente ao código (por exemplo, afirmar arredondamento meio para cima onde há `round` bancário: `arredondamento_numerico`); empate decidido pelo tipo padrão do requisito citado. Alegação sobre arquivo, símbolo, teste, comando, contagem ou resultado inexistente ou incorreto: `relato_verificacao`.
3. Na condição `controle` as colunas `claims_checked` e `claimdiv_*` valem **0 por regra** (não há relatório obrigatório); isso significa "não aplicável", não "sem divergência". O validador recusa valores diferentes de 0 no controle.
4. Registro por execução em `runs/<run_id>/error_classification.json` (um item por teste reprovado e por alegação divergente: identificador, tipo, tipo padrão, `override_reason`).

**Análise descritiva (`protocol/descriptive.py`, `python3 -m protocol.cli profile ARQUIVO.csv`).** Por condição e por tipo: número de testes reprovados, número de execuções com ao menos uma falha do tipo e participação do tipo no total de reprovações da condição. Alegações divergentes por tipo, apenas em `explicacao`. Leitura: comparar o **perfil** (participações), não os totais, porque o número de testes por tipo no oráculo não é uniforme. Descrever também, em texto, exemplos concretos de cada tipo observado. Resposta à pergunta qualitativa: relatar se a distribuição por tipo difere entre condições e quais tipos aparecem ou desaparecem, sem inferência causal; com 3 repetições por célula, uma diferença pode ser acaso. Limitação: classificação por um único avaliador, que conhece a condição na etapa dos testes ocultos.

## 18. Facilidade de revisão: medida contável (P2)

Medida **secundária e complementar**; não substitui nem duplica C1–C7. A rubrica avalia a **qualidade** de cada propriedade em escala 0–2; esta medida conta **quantos pontos de atenção** o relatório entrega a um revisor e **quantos conferem**. Operacionalização e limiares são decisões do autor, sem fonte externa, pendentes de aprovação.

**Ponto de atenção verificável** (contado uma vez, sem repetição de conteúdo): item do relatório que (i) enuncia uma decisão, um risco ou uma ligação específica **e** (ii) aponta um objeto conferível no workspace final, nos testes públicos ou no log (arquivo e símbolo, requisito RN, nome de teste, entrada ou comando). Frases genéricas ("pode haver bugs") não contam. Três subcontagens:

| Campo | O que se conta |
| --- | --- |
| `rp_assumptions` | premissas distintas (decisão diante de omissão ou ambiguidade) |
| `rp_risks` | riscos, limitações ou pontos não verificados distintos |
| `rp_traces` | ligações requisito → código/teste distintas, uma por requisito citado (linha da tabela de rastreabilidade ou equivalente) |

`rp_confirmed` = quantos desses pontos **conferem** com o código final, os testes públicos e `agent_events.jsonl` (mesmos meios da rubrica; resultados dos testes ocultos nunca são usados). Um ponto que não confere ou não pode ser conferido não entra em `rp_confirmed`. Registro por execução em `runs/<run_id>/review_points.json` (um item por ponto, com tipo, objeto apontado e veredito).

**Derivados (não gravados; `protocol/descriptive.py`).** Pontos = `rp_assumptions + rp_risks + rp_traces`. Fração = `rp_confirmed / pontos`, **indefinida** quando pontos = 0.

**Condição controle.** Pode não haver relatório. Então `rp_*` e `rp_confirmed` valem **0 explícito** (nunca vazio). A fração fica **indefinida e não é imputada como 0**: é omitida da mediana, que considera apenas execuções com ao menos um ponto, e o número dessas execuções é sempre relatado. Se o controle produzir pontos espontaneamente (comentários, docstring, mensagem final), eles contam pelas mesmas regras. A medida `rp_*` conta o que está na mensagem final; a medida `ap_*` da seção 21 olha o código e o resumo livre. Os dois conjuntos se sobrepõem no resumo e **não devem ser somados**.

**Efeito de piso e de construção.** Como o prompt de `explicacao` exige exatamente as seções que geram esses pontos, a contagem em `explicacao` é em parte mecânica (por exemplo, `rp_traces` tende ao número de requisitos) e a de `controle` tende a 0. Por isso a leitura de interesse é a fração que **confere** e a contagem de premissas e riscos específicos, relatadas por subcampo, e não a comparação bruta do total. É uma ameaça de construto declarada, análoga à da seção 4 de `RUBRIC.md`. Com a decisão Q06=B, a comparação que **não depende do pedido do prompt** é a da seção 21 (pontos do artefato, contados com as mesmas regras nas duas condições); `rp_*` permanece como medida do relatório e mantém o efeito de construção descrito. Não há reavaliação desta medida na passagem 2 (limitação).

## 19. Interface e versão do Codex (P3, replicabilidade)

`config/execution_config.template.json` prevê, e `freeze` **exige preenchidos**: `model.name`, `model.version_or_snapshot`, `agent.codex_version`, `agent.interface` (`cli` ou `api`), `agent.invocation_command`, `agent.flags` (lista; vazia significa nenhuma flag), `agent.sandbox_mode`, `agent.approval_policy`, `execution.working_directory`, `execution.date_first_run`. O validador (`freeze.check_codex_interface_fields`) recusa ausência, `null`, vazio e `nao_exposto` nesses campos, e interface fora de `cli`/`api`. Cada registro consolidado repete `model`, `codex_version` e `codex_interface`. **Modelo e esforço (Q11, escolhidos pelo autor).** Modelo `gpt-5.5` e esforço de raciocínio `medium`, escolhidos pelo autor em 2026-10-02 (não herdados do `~/.codex/config.toml`). Existência do modelo com esforço `medium` foi conferida no `models_cache` do Codex local, **sem execução**. Esses dois valores estão em `author_choices` do template e **devem ser copiados** para `model.name` e `generation_parameters.reasoning_effort` ao criar `execution_config.json`; `freeze` (`check_author_choices`) recusa se divergirem. Os campos `agent.*` continuam nulos no template. **Snapshot, versão do modelo e demais campos não são presumidos:** `model.version_or_snapshot` e a data de execução continuam sendo o que a própria execução reportar (Q11 pede fixar a data e o snapshot reportados na saída JSON, sem valor de memória). O modelo e o esforço são os mesmos nas 18 execuções e só mudam com novo congelamento. Aplica-se apenas ao agente avaliado; nenhum LLM avalia.

**Nenhum outro valor é presumido neste rascunho:** devem ser os reportados pela própria execução (TCC-040) e transcritos no método do TCC (`TCC-080`). A data de cada execução fica em `started_at` e `run_meta.json`; a data da última execução saiu do arquivo congelado, porque não existe no momento do congelamento.

## 20. Uso de IA e revisão humana (P4)

Origem: revisão do professor (P4). Esta seção define o registro; **nenhuma revisão foi feita ainda e nenhuma declaração final está escrita.**

- **Quem avalia.** O autor (pesquisador) é o único avaliador da rubrica (seção 12), da classificação de erros (seção 17) e da contagem de pontos de atenção (seções 18 e 21). Isso é limitação declarada.
- **Escopo da declaração.** (a) Saídas do Codex nas execuções são **material de pesquisa analisado**, não texto do TCC. (b) Este protocolo, o harness e os oráculos foram redigidos com agentes de IA coordenados pelo autor (fluxo em `AGENT-WORKFLOW.md`); a declaração deve dizê-lo. (c) Qualquer trecho gerado por IA que seja **reutilizado** no TCC (código, trecho de relatório, texto, tabela) exige revisão humana integral antes de entrar no documento.
- **Registro de revisão.** Um registro por trecho reutilizado, com campos fixos em `records.AI_REVIEW_FIELDS` e `schema/ai_review_log_header.csv`: `item_id`, `origem` (ferramenta e versão), `run_id` (se vier de uma execução), `destino_no_texto`, `tipo_uso` (reutilizado, adaptado, apenas analisado), `revisor`, `data_revisao`, `como_foi_verificado` (leitura linha a linha, execução, conferência de fontes), `decisao` (aceito, alterado, descartado), `observacoes`. O arquivo preenchido é mantido pelo autor/integrador no repositório do TCC (`TCC-080`/`TCC-090`), fora de `protocol/`: `.specs/tcc-auditabilidade/AI-REVIEW-LOG.csv`.
- **Declaração do autor (Q08, 2026-10-02).** O autor declarou: "Já revisei todos os códigos gerados no repositório usp-mba-eng-sftw-tcc-code" (https://github.com/rafaelportomoura/usp-mba-eng-sftw-tcc-code). Foi registrada uma entrada em `AI-REVIEW-LOG.csv` com revisor = autor e `como_foi_verificado` = "declaração do autor; método não detalhado". Nenhuma data de revisão, método ou escopo foi inventado. **Alterações posteriores ao commit `f934ab8`** (executor, medida `ap_*`, decisões Q03 a Q12) exigem nova confirmação de revisão; até lá a declaração não as cobre.
- **Texto do TCC e declaração final.** O autor informou que o texto do TCC será escrito por ele; a URL do repositório experimental será citada no texto; e a declaração de uso de IA mencionará o uso de agentes de IA na construção do experimento (protocolo, harness, oráculos, executor e rascunhos documentais). Os trechos de código do Codex só entram no texto como material analisado, ou, se reutilizados, com revisão integral e registro. A redação final fica com o autor/`TCC-080`.
- **Texto da declaração** (a ser redigido por `TCC-080`/`TCC-090` com base nesse registro): deve afirmar revisão integral somente para o que constar do registro como revisado, e distinguir o que foi reutilizado do que foi só analisado. Não afirmar revisão que não ocorreu.

## 21. Auditabilidade do controle sobre o que ele produz (Q06=B)

Decisão do autor (Q06=B): acrescentar uma medida que não dependa de a condição ter recebido o pedido de relatório. **Complementa** C1–C7 e a medida `rp_*` (seção 18) e **não as substitui**; não entra em `auditability_total`. Contagem operacional e regras são decisões do autor, sem fonte externa, pendentes de aprovação e de calibração. Os **prompts não mudam**: `controle` e `explicacao` continuam diferindo apenas pelo bloco "Relatório final obrigatório" (teste `test_prompts_differ_only_by_report_block`).

**Pergunta descritiva.** Quantos pontos de atenção um revisor consegue verificar nos artefatos de cada condição **sem recorrer a um relatório estruturado**, e quantos deles conferem? O interesse é saber o quanto o controle já oferece por conta própria e o quanto o pedido de relatório acrescenta sobre isso. Sem teste de significância (seção 13).

**Visão do artefato (a mesma regra nas duas condições).** O avaliador conta apenas sobre:

- **F1, código e testes:** linhas adicionadas ou alteradas em `workspace.diff` (comentários, docstrings, mensagens de exceção e de asserção, nomes e docstrings de testes, constantes nomeadas). Texto do baseline, de `REQUIREMENTS.md` e dos testes públicos originais fica de fora, assim como texto copiado literalmente do enunciado.
- **F2, resumo final livre:** no `controle`, toda a `final_message.md`; na `explicacao`, **somente a seção 1** ("Resumo da solução"), que é o equivalente funcional do resumo livre do controle. As seções 2 a 6 existem por exigência do prompt e ficam fora desta medida (são medidas por C1–C7 e `rp_*`). Se a seção 1 não for identificável, vale o primeiro bloco de texto até o primeiro título ou tabela.
- O log (`agent_events.jsonl`) serve apenas para **conferir**, não como fonte de pontos.

**Ponto de atenção do artefato.** Unidade contada uma única vez por par (tipo, objeto apontado), ainda que apareça em F1 e F2. Para contar, precisa (i) ser de um dos três tipos abaixo, (ii) apontar objeto conferível (arquivo e símbolo, requisito RN, nome de teste, entrada ou valor concreto, comando) e (iii) poder ser conferido por um revisor com o código final, os testes públicos e o log.

| Campo | Tipo | O que conta | O que não conta |
| --- | --- | --- | --- |
| `ap_decisions` | decisão | comentário, docstring ou resumo que declara uma escolha diante de omissão ou ambiguidade, ou o critério de uma regra, apontando o ponto do código ("centavos inteiros em vez de `round`, por causa do arredondamento bancário", em `calculate_shipping`) | comentário que apenas descreve a linha ("incrementa o contador"); docstring genérica sem objeto ("calcula o frete") |
| `ap_risks` | risco | nota de limitação, `TODO` específico ou declaração do que não foi testado ou verificado, apontando entrada, símbolo ou requisito ("R7 sem teste", "peso 1.0000001 depende de `ceil`") | "pode haver bugs"; "não testei tudo"; afirmação de ausência de riscos |
| `ap_links` | ligação | associação explícita de um requisito RN a código ou teste: comentário `# R5` junto ao ramo, docstring "implementa R4", nome de teste ou mensagem de asserção que cite RN, resumo que diga "R5 em `calculate_shipping`". Um teste novo cujo nome identifica o requisito e que o exercita conta como **uma ligação por requisito** | nome de função que por acaso lembre o requisito, sem citá-lo; ligação a objeto inexistente (conta como ponto, mas não confere) |

`ap_confirmed` = pontos que **conferem** (o objeto existe e faz o que o ponto diz; o teste citado exercita o requisito; o risco ou a limitação se mostra real ou o não verificado de fato não foi coberto). Ponto que não confere ou não pode ser conferido não entra. Resultados dos testes ocultos nunca são usados. `ap_from_summary` = pontos cuja **única** ocorrência é o resumo livre (F2); os demais têm ao menos uma ocorrência em F1. Registro por execução em `runs/<run_id>/artifact_attention.json` (um item por ponto: tipo, objeto, fonte F1/F2, veredito).

**Regras iguais nas duas condições (para não favorecer por construção).** (1) O prompt não pede nenhum dos três tipos em nenhuma condição; (2) a visão exclui o relatório estruturado, que só existe em `explicacao`; (3) o validador aplica as mesmas checagens às duas condições, sem ramo por condição (`ap_confirmed` e `ap_from_summary` não excedem a soma dos três tipos); (4) o controle pode ter 0 pontos, registrado como **0 explícito**, e a fração que confere fica **indefinida, nunca imputada como 0**; (5) o gerador de pacotes (TCC-060) deve entregar a visão já sem as seções 2–6 da `explicacao`.

**Derivados (`protocol/descriptive.py`, `python3 -m protocol.cli profile ARQUIVO.csv`).** Pontos = `ap_decisions + ap_risks + ap_links`; fração = `ap_confirmed / pontos`, indefinida se pontos = 0. Por condição: medianas de pontos (inclui zeros), por tipo, de confirmados, de pontos vindos só do resumo e de pontos **sem** o resumo; fração mediana e agregada entre execuções com ao menos um ponto, com o número dessas execuções sempre informado; diferença `explicacao − controle` nas medianas, sem inferência.

**Efeito de piso, discussão reescrita.**

- *O que muda.* Em C1–C7 e em `rp_*`, a vantagem de `explicacao` é em parte mecânica, porque o prompt pede exatamente aquelas seções. Na medida `ap_*` o prompt não pede nada em nenhuma condição, e a visão exclui o relatório; assim, o piso do controle deixa de ser **por construção** e passa a ser **uma questão empírica**: se o Codex, sem pedido, deixar comentários, docstrings, testes que citam requisitos ou um resumo com decisões e riscos, o controle terá pontos; se não deixar, a ausência será o resultado observado.
- *O que não muda.* O piso de C1–C7 e de `rp_*` permanece e continua declarado (`RUBRIC.md`, seção 4). H1 segue em parte mecânica; a medida `ap_*` é o contraponto, não uma correção.
- *Vieses residuais declarados.* (a) A seção 1 da `explicacao` é pedida pelo prompt ("o que foi alterado e onde"), enquanto o controle não é instruído sobre o conteúdo do resumo: pode haver vantagem residual para `explicacao` em F2; por isso se reporta a contagem **com e sem** o resumo. (b) O pedido de relatório pode **deslocar** esforço dos comentários para o relatório (efeito de substituição) ou **incentivá-los** (efeito de contágio); ambos são efeitos do tratamento, e não do instrumento, e o desenho não os separa. (c) O avaliador sabe ou infere a condição pelo resumo, de modo que o cegamento é parcial. (d) A contagem é de um único avaliador, sem reavaliação na passagem 2, e as regras não foram calibradas. (e) Medir mais pontos não significa que o revisor audita mais rápido: a medida é de **conteúdo verificável disponível**, não de esforço de revisão.

## 22. Tipo de estudo e enquadramento normativo (Q03=A)

Decisão do autor (Q03=A): o estudo é do tipo **Benchmarking** (Baltes et al., 2025, seção 4, p. 13), com avaliação por humano (o autor) e **sem LLM avaliador**; portanto o tipo "Judges" não se aplica e nenhum LLM atua como avaliador, o que deve ser dito no método. Enquadramento normativo: Padrão Geral, Benchmarking e suplemento IRR/IRA da ACM SIGSOFT; o padrão *Experiments (with Human Participants)* só por **analogia**, porque o agente de IA não é participante humano (fichamento TCC-010, seção 4). A coluna "Conferido" abaixo é **Sim** apenas quando o item consta da transcrição da Tabela 3 (Apêndice A, p. 61) no fichamento TCC-010, seção 1; essa transcrição foi lida pelo `literature_core` em imagem renderizada e **não foi reconferida contra o PDF neste ciclo**.

| Item de Baltes et al. (seção) | Benchmarking na Tabela 3 | Conferido | Onde o protocolo cumpre | Lacuna |
| --- | --- | --- | --- | --- |
| Declarar uso e papel do LLM (5.1) | obrigatório | Sim | seções 1, 3 e 9; seção 20 (uso de IA) | texto do método (`TCC-080`); dizer que o Codex é o sistema avaliado e que nenhum LLM avalia |
| Versão e configuração do modelo (5.2) | obrigatório | Sim | seção 9; seção 19; `config/execution_config.template.json`; colunas `model`, `codex_version`, `codex_interface`, `started_at` | valores não preenchidos (vêm da execução, `TCC-040`); parâmetros não expostos serão declarados |
| Sistema e desenho de prompts (5.3) | obrigatório | Sim | seções 5 e 9; `prompts/*.md`; hashes no congelamento | congelamento não feito; configuração do agente depende do executor |
| Rastros de sessão (5.4) | recomendado | Sim | seção 10 (`runs/<run_id>/`) | executor inexistente; `agent_events.jsonl` e `run_meta.json` não são gerados hoje |
| Benchmarks e métricas (5.5) | obrigatório | Sim | seções 3, 4, 13, 17, 18 e 21; `RUBRIC.md`; testes ocultos como proxy de correção | proxy depende da liberação dos oráculos (B1–B4 de `TCC-030-review`); limiares da Q05 pendentes; rubrica não calibrada; sem testes inferenciais nem tamanhos de efeito (desvio declarado na seção 13) |
| LLM aberto como linha de base (5.6) | recomendado | Sim | não cumprido; declarado como limitação na seção 14 | ausência de modelo aberto; o fichamento registra que a fonte admite exceções, mas a justificativa da exceção precisa ser redigida |
| Validação humana (5.7) | recomendado | Sim | seção 12 e `RUBRIC.md` seções 1 e 5 (reavaliação cega de 6 artefatos) | avaliador único; sem estatística de concordância; avaliador único declarado como limitação (Q10=A, seção 12); sem estatística de concordância inter-avaliador |
| Limitações e mitigações (5.8) | obrigatório | Sim | seção 14 (inclui a limitação da seção 6 e o piso da seção 21) | texto final (`TCC-080`) |

Itens de outras colunas da Tabela 3 (Annotators, Judges, Synthesis, Subjects, Usage, Tools) e de qualquer apêndice além do transcrito **não foram consultados** neste ciclo.

**Padrões ACM (conforme fichamento TCC-010, seção 4).**

| Exigência | Padrão | Onde | Lacuna |
| --- | --- | --- | --- |
| Justificar a carga de trabalho, a qualidade medida, as métricas e o método de medição | Benchmarking | seções 3, 4, 17, 18 e 21; `RUBRIC.md` | justificativa textual das tarefas como amostra de trabalho (`TCC-080`) |
| Descrever o ambiente com detalhe para replicação | Benchmarking | seções 9, 15 e 19; `config/` | ambiente real (versões, sistema operacional) ainda não registrado |
| Avaliar a estabilidade com repetições suficientes | Benchmarking | 3 repetições por célula (seção 6) | três repetições é poder limitado; declarado, sem tese de suficiência |
| Discutir a validade de construto | Benchmarking, Geral | seções 14 e 21; `RUBRIC.md` seção 4 | texto final |
| Relatar problemas ocorridos nas execuções; publicar scripts e dados (desejável) | Benchmarking | seção 7 (`runs/exclusions.jsonl`); repositório experimental | dados reais inexistentes |
| Limitações, conclusões ligadas à evidência; plano antes dos resultados (desejável) | Geral | seções 14 e 15 (congelamento) | congelamento pendente |
| Declarar o que se avalia e quantos avaliadores; justificar avaliador único; regras de decisão como material suplementar; estatística de concordância | IRR/IRA | seção 12; `RUBRIC.md` seções 1 e 5; seção 20 | um único avaliador sem estatística de concordância inter-avaliador; justificado por praticidade e declarado (Q10=A) |
| Hipóteses, variáveis, controle, randomização, validades | Experiments (por analogia) | seções 2, 3, 5, 6 e 14 | o padrão exige participantes humanos; usado só como referência e declarado |

**Lacunas consolidadas deste mapeamento:** (1) preenchimento da configuração e executor da sessão; (2) liberação dos oráculos; (3) limiares da Q05; (4) calibração da rubrica; (5) redação final da justificativa do avaliador único (decidido em Q10=A); (6) justificativa da ausência de LLM aberto; (7) redação do método, da declaração de IA e das limitações; (8) reconferência da Tabela 3 contra o PDF antes de citá-la no TCC.

## 23. Limiares sem apoio nas fontes inspecionadas (Q12.1=A)

Decisão do autor (Q12.1=A): os limiares abaixo são **decisões metodológicas do autor**. Para cada um, **não foi localizado apoio nas fontes inspecionadas** (levantamento em `handoffs/Q05-limiares-literatura.md`). O plano de busca (`handoffs/Q05-plano-de-busca.md`) **não foi executado**; por isso não se afirma ausência de respaldo na literatura, apenas o que foi (e o que não foi) localizado nas fontes inspecionadas. Se o plano for executado depois, a redação pode ser revista antes do congelamento. Os valores não mudam por esta seção; nenhum foi alterado.

| # | Limiar | Onde | Situação | Apoio apenas de princípio (quando houver) | Tratamento |
| --- | --- | --- | --- | --- | --- |
| L1 | C2 nota 2: ≥ 75% dos requisitos com referência válida e restantes declarados sem teste | `RUBRIC.md` C2 | decisão do autor; apoio ao valor não localizado | critério de completude da saída: Nauta et al. (2023, seção 6.2, p. 21) | sensibilidade com 70% e 80% |
| L2 | C2 nota 1: ≥ 50%; C1 nota 1: "pelo menos metade" | `RUBRIC.md` C1, C2 | idem | idem | sensibilidade de C2 com 40% e 60% |
| L3 | C6: ≥ 5 alegações verificáveis (nota 2), ≥ 3 (nota 1), teto de 10 extraídas | `RUBRIC.md` C6 | idem | correção/fidelidade como propriedade: Nauta et al. (2023, seção 6.1, p. 15–21); o Padrão Geral da ACM trata como crítica inválida impor mínimos arbitrários sem análise de poder ou saturação (seção "Invalid Criticisms"), o que exige declarar a escolha, não a justifica | declarar como mínimo operacional; relatar `claims_checked`; sensibilidade com 4 e 6 (nota 2) e 2 e 4 (nota 1) |
| L4 | C6: no máximo 1 divergência menor (nota 1); ≥ 2 menores = 0 | `RUBRIC.md` C6 | idem | documentar regras de decisão: Baltes et al. (2025, seção 5.7, p. 49–50) | decisão do autor; regra conservadora registrada em `notes` |
| L5 | C3, C4, C5: "duas ou mais" premissas, riscos ou decisões (nota 2) | `RUBRIC.md` C3–C5 | idem | completude como dimensão: Nauta et al. (2023, p. 10–11) | decisão do autor; calibrar com relatórios sintéticos (pendente) |
| L6 | escala ordinal 0–2 com âncoras e 7 critérios | `RUBRIC.md` | parcial | definir o construto e compartilhar o instrumento: Baltes et al. (2025, seção 5.7.2, p. 49); avaliar várias propriedades: Nauta et al. (2023, seção 7, p. 28) | rubrica compartilhada no apêndice; escala declarada como escolha de projeto |
| L7 | H2: margem de 0,10 na mediana da proporção de testes ocultos | seção 2 | valor sem apoio localizado; princípio parcial | margem pré-especificada e justificada, sem regra universal: EMA/CHMP (2005, seção 1, p. 3; seção 2, p. 4–5), **domínio clínico, apenas analogia**; tamanhos de efeito: Baltes et al. (2025, p. 38) | margem definida pelo autor como a menor queda considerada relevante; relatar diferença observada e intervalo (mín–máx); se a diferença cair entre 0,05 e 0,15, dizer que a conclusão depende da margem |
| L8 | intervalo mínimo da reavaliação: 24 h (antes 60 min) | seção 12 | valor sem apoio localizado; princípio parcial | dilema entre efeito de memória e mudança do objeto: Laenen et al. (2006, resumo e introdução, p. 1–2), relatório técnico (literatura cinzenta) | decisão do autor; sem análise de sensibilidade possível (uma só reavaliação); limitação |
| L9 | timeout de 12 min (720 s) por execução | seções 6 e 7 | valor sem apoio localizado | relatar latência quando afetar resultados: Baltes et al. (2025, p. 36 e 38) | calibrar com os pilotos P1/P2, registrar a regra de escolha antes do congelamento; relatar a proporção de `timeout` por condição |
| L10 | 3 repetições por célula (fallback de 2) | seções 2 e 6 | número sem apoio localizado; princípio parcial | repetir por não determinismo e justificar o número: Baltes et al. (2025, seção 5.5, p. 36 e 38–39); várias execuções e análise de poder: Bjarnason, Silva e Monperrus (2026, resumo p. 1; seção 3.2 e Tabela 2, p. 9), variância medida em 500 tarefas, não transponível diretamente a células de 1 tarefa | declarar limite por tempo e custo, não por análise de poder; pilotos como estimativa descritiva de variabilidade; ausência de inferência como limitação |
| L11 | reavaliação de 6 artefatos (um por célula) | seção 12 | parcial | avaliador único aceitável com justificativa; declarar quantos avaliadores: suplemento IRR/IRA da ACM ("Are multiple independent raters needed?", "Essential Attributes"); procedimento iterativo e α sustentado: Baltes et al. (2025, seção 5.7.2, p. 49–50) | confiabilidade intra-avaliador de ordem de grandeza modesta; não calcular α com n = 6 |
| L12 | medidas da reavaliação | seção 12 | parcial | percentual de concordância como medida rara e antipadrão de relatar só a favorável: suplemento IRR/IRA (Notas, nota 5); distribuição por item: Baltes et al. (2025, p. 38) | relatar distribuição, matriz 3×3, concordância exata e diferença absoluta média |
| L13 | α de Krippendorff: < 0,667 descartar; 0,667–0,8 provisório; ≥ 0,8 confiável | `RUBRIC.md` seção 5 | **apoiado** (citado em fonte consultada) | Baltes et al. (2025, seção 5.7.2, p. 50), que atribui os limiares a Krippendorff (2018) | citar Baltes; `[CITAÇÃO NECESSÁRIA]` para Krippendorff (2018) diretamente, fonte não aberta; α não será calculado (n = 6) |
| L14 | máximo de 2 repetições por `run_id` em `infra_failure` | seção 7 | sem apoio localizado | relatar problemas de execução com transparência: padrão ACM Benchmarking (sem limite fixado) | decisão operacional; todas as tentativas em `runs/exclusions.jsonl` |

Parâmetros de aleatorização (semente 20261002, blocos A/B, `S01..S24`) não são limiares de julgamento; só exigem registro.

**Análise de sensibilidade pré-especificada.** Declarada antes das execuções e implementada em `protocol/sensitivity.py` (arquivo congelado). **Não altera nenhuma nota oficial**; a nota válida é a obtida com os cortes originais.

1. *C2 e C6.* O avaliador registra, por execução, `runs/<run_id>/sensitivity_inputs.json` com `n_requirements`, `c2_valid_refs`, `c2_rest_declared`, `c6_claims`, `c6_material` e `c6_minor`. Recalcula-se o total com C2 sob 70%/80% (nota 2) e 40%/60% (nota 1), e C6 sob mínimo de 4/6 alegações (nota 2) e 2/4 (nota 1), uma variação por vez (`sensitivity.VARIANTS`). Reporta-se, por variante, a mediana por condição, a diferença `explicacao − controle` e se a **direção de H1 muda** em relação à variante oficial (`conclusion_changes`). Antes disso, `consistency_errors` confere se as notas oficiais de C2 e C6 coincidem com a recomputação sob os cortes oficiais; divergência é investigada e registrada, não corrigida em silêncio.
2. *H2.* Reportar a diferença observada de medianas, o intervalo mín–máx por condição e a conclusão sob 0,05 e 0,15, além de 0,10.
3. *Timeout.* Reportar a proporção de `timeout` por condição.
4. *Reavaliação.* Sem sensibilidade (uma só reavaliação), só limitação.

## 24. Decisões Q09 e demais notas de 2026-10-02

- **Baltes et al. (Q09=A).** Cita-se a versão 8 do arXiv (18/09/2026; DOI 10.48550/arXiv.2508.15503). Crossref, arXiv e OpenAlex não traziam DOI nem paginação da versão publicada em *Empirical Software Engineering*. **Pendência:** conferir o DOI e a paginação publicados **antes da entrega final**; se a versão publicada divergir da v8, reconferir as páginas dos localizadores do ledger (`SOURCES.md`).
- **Q10=A, Q11, Q12.** Ver seções 12 e 14 (avaliador único), 19 (modelo e esforço) e 23 e 12 (limiares e reavaliação).
- **Q08.** Ver seção 20 (registro de revisão e declaração).
