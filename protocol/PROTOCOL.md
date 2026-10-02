# Protocolo do experimento de auditabilidade (RASCUNHO TCC-020)

_Status: **RASCUNHO, NÃO CONGELADO.** Sem versão, sem hashes finais, sem `FREEZE.json`. O congelamento só ocorre depois da liberação dos oráculos pelo revisor independente (`handoffs/TCC-030-review.md`) e do preenchimento de `config/execution_config.json`. Fontes metodológicas: fichamentos de TCC-010. Especificação-mãe: `EXPERIMENT.md` e `PLAN.md` do repositório do TCC._

## 1. Pergunta de pesquisa

Em tarefas de desenvolvimento de complexidade crescente, a exigência de explicações estruturadas no prompt aumenta a auditabilidade documental dos artefatos produzidos pelo Codex, sem reduzir sua correção funcional?

"Explicação" é a justificativa externa e verificável contida no relatório final; não se alega acesso ao raciocínio interno do modelo, e nenhum prompt solicita cadeia de pensamento.

## 2. Hipóteses

Delineamento descritivo, sem testes de significância (3 repetições por célula; ver seção 13).

- **H1 (auditabilidade).** Em cada tarefa e no conjunto, a mediana do escore de auditabilidade (0–14) na condição `explicacao` é maior que na condição `controle`.
- **H2 (correção funcional).** A mediana da proporção de testes ocultos aprovados em `explicacao` não é inferior à de `controle` em mais de 0,10. O limiar 0,10 é **proposto**, sem fonte externa, e deve ser confirmado antes do congelamento.
- **Leitura de H1.** O tratamento coincide em parte com o que a rubrica mede (ver `RUBRIC.md`, seção 4); por isso o resultado de interesse é a magnitude, o perfil por critério, a fidelidade (C6) e o custo, e não a mera existência de diferença.

Classificação (PLAN.md): pesquisa aplicada, explicativa, abordagem mista, experimento controlado com artefatos de software; unidade de análise = execução independente do agente em uma tarefa e condição.

## 3. Variáveis

| Tipo | Variável | Operacionalização |
| --- | --- | --- |
| Independente | `condition` | `controle` ou `explicacao`; difere somente pela exigência do relatório (seção 5) |
| Dependente principal | `auditability_total` | soma de C1..C7 (0–14), `RUBRIC.md` |
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
- **Fallback de 12:** bloco A inteiro (R01–R12), 2 repetições por célula, mesmos `run_id`. Como o bloco A vem primeiro, parar após R12 já é balanceado. A decisão de seguir para o bloco B é tomada **depois de R12 e antes de ver qualquer pontuação**, só pelo tempo restante. A restrição por blocos é uma decisão deste rascunho (a especificação diz apenas "ordem aleatorizada com semente"); ela deve ser confirmada pela coordenação.
- Execução sequencial na ordem do manifesto, sem reordenar nem pular.
- Cada execução: workspace novo (`python3 -m harness.cli prepare`), sessão nova do Codex, sem memória, histórico ou conversa compartilhados, sem intervenção humana, mesma configuração, timeout de **12 minutos (720 s)**. Avaliação dos testes públicos e ocultos pelo harness (`harness.cli evaluate`) logo após a sessão. A pontuação pela rubrica só começa depois que todas as execuções terminam.
- Pilotos (um por condição) ocorrem em TCC-040, com identificadores `P1` e `P2`, fora da amostra.

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

## 10. Esquema dos dados e dos logs

- Registro consolidado: `schema/run_record.schema.json` (JSON Schema) e `schema/results_header.csv`. Colunas: `run_id, task_id, condition, replicate, model, codex_version, codex_interface, prompt_hash, baseline_hash, started_at, duration_s, exit_status, hidden_tests_passed, hidden_tests_total, output_words, trace_code, trace_tests, assumptions, risks, rationale, fidelity, reproducibility, auditability_total, notes`. A coluna `started_at` consta de `EXPERIMENT.md`; foi mantida.
- Reavaliação: `schema/reevaluation_header.csv` (`blind_id, run_id, pass, scored_at`, sete itens, total, `notes`).
- Validação: `python3 -m protocol.cli validate results/results.csv` (stdlib; esquema + soma dos itens + testes ocultos ≤ total + balanceamento 3×6 ou 2×6 + consistência com o manifesto + um `prompt_hash` por condição e um `baseline_hash` por tarefa).
- Por execução, `runs/<run_id>/` deve conter: `prompt.txt` (bytes enviados), `agent_events.jsonl` (log nativo do Codex, com a versão da ferramenta), `final_message.md`, `workspace.diff`, `prepare.json`, `evaluation.json` (harness) e `run_meta.json`. `protocol.records.check_run_dir` lista ausências. Hoje o harness **não** invoca o Codex; o executor da sessão, que gera `agent_events.jsonl` e `run_meta.json`, é pendência (seção 16).

## 11. Execução da avaliação

Testes ocultos aplicados uniformemente pelo harness; o avaliador não corrige código. Rubrica aplicada pela passagem 1 sobre as 18 (ou 12) execuções em ordem aleatória e identificadores neutros (seção 12).

## 12. Avaliação cega e reavaliação

- Identificadores neutros `S01..S24`, sorteados com `random.Random(semente + 1)` (`python3 -m protocol.cli blind`). Nenhum codifica tarefa, condição, repetição ou ordem de execução. A chave `blind_id → run_id` fica fora do alcance do avaliador até o fim da pontuação.
- Passagem 1: todas as execuções concluídas, em ordem sorteada.
- Passagem 2: 6 artefatos, **um por célula**, escolhidos por sorteio entre as concluídas, com **novos** `blind_id`, em ordem sorteada, após intervalo mínimo de 60 minutos (valor proposto, ver limitações) e sem acesso às notas da passagem 1.
- Os artefatos entregues ao avaliador removem metadados (tarefa, condição, repetição, `run_id`, horários); o gerador desses pacotes é pendência.
- **Limite do cegamento:** a presença da estrutura de relatório revela a condição; o cegamento é parcial e protege apenas contra viés por rótulo e por ordem. O avaliador é o próprio pesquisador.
- Medidas: percentual de concordância exata por critério e diferença absoluta média do total. Vale a nota da passagem 1.

## 13. Análise (TCC-070)

Mediana, mínimo e máximo por tarefa, condição e conjunto; diferenças entre condições; perfil por critério. Sem testes de significância, o que difere da recomendação de Baltes et al. (2025, p. 37–38) de usar testes inferenciais com tamanhos de efeito; a justificativa é a amostra de 3 por célula e ela é declarada como limitação.

## 14. Limitações e ameaças declaradas

Um único agente e uma única configuração; sem modelo aberto como linha de base (Baltes et al., 2025, seção 5.6); tarefas artificiais e amostra pequena; sem generalização estatística; avaliação pelo próprio pesquisador, sem avaliador externo e com cegamento parcial; oráculos e referências escritos pelo mesmo agente que construiu as tarefas (handoff TCC-030); explicações pós-hoc possivelmente não fiéis ao processo interno; evolução do serviço e do modelo ao longo do tempo; rubrica com efeito de piso na condição `controle`; intervalo curto na reavaliação; a rubrica de qualidade de código (por exemplo, refatoração em T2) não é verificável automaticamente. Ameaças organizadas conforme Baltes et al. (2025, seção 5.8, p. 54–56): externa, interna, de construto, confiabilidade. O uso do checklist de experimentos da ACM SIGSOFT é apenas por analogia, porque o padrão exige participantes humanos (fichamento TCC-010, seção 4).

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
5. Confirmar: limiar de H2, restrição por blocos, intervalo de 60 min, limiares numéricos da rubrica, taxonomia e mapa padrão de erros (seção 17) e a contagem operacional de pontos de atenção (seção 18); calibrar a rubrica com relatórios sintéticos.
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

**Condição controle.** Pode não haver relatório. Então `rp_*` e `rp_confirmed` valem **0 explícito** (nunca vazio). A fração fica **indefinida e não é imputada como 0**: é omitida da mediana, que considera apenas execuções com ao menos um ponto, e o número dessas execuções é sempre relatado. Se o controle produzir pontos espontaneamente (comentários, docstring, mensagem final), eles contam pelas mesmas regras.

**Efeito de piso e de construção.** Como o prompt de `explicacao` exige exatamente as seções que geram esses pontos, a contagem em `explicacao` é em parte mecânica (por exemplo, `rp_traces` tende ao número de requisitos) e a de `controle` tende a 0. Por isso a leitura de interesse é a fração que **confere** e a contagem de premissas e riscos específicos, relatadas por subcampo, e não a comparação bruta do total. É uma ameaça de construto declarada, análoga à da seção 4 de `RUBRIC.md`. Não há reavaliação desta medida na passagem 2 (limitação).

## 19. Interface e versão do Codex (P3, replicabilidade)

`config/execution_config.template.json` prevê, e `freeze` **exige preenchidos**: `model.name`, `model.version_or_snapshot`, `agent.codex_version`, `agent.interface` (`cli` ou `api`), `agent.invocation_command`, `agent.flags` (lista; vazia significa nenhuma flag), `agent.sandbox_mode`, `agent.approval_policy`, `execution.working_directory`, `execution.date_first_run`. O validador (`freeze.check_codex_interface_fields`) recusa ausência, `null`, vazio e `nao_exposto` nesses campos, e interface fora de `cli`/`api`. Cada registro consolidado repete `model`, `codex_version` e `codex_interface`. **Nenhum valor é presumido neste rascunho:** devem ser os reportados pela própria execução (TCC-040) e transcritos no método do TCC (`TCC-080`). A data de cada execução fica em `started_at` e `run_meta.json`; a data da última execução saiu do arquivo congelado, porque não existe no momento do congelamento.

## 20. Uso de IA e revisão humana (P4)

Origem: revisão do professor (P4). Esta seção define o registro; **nenhuma revisão foi feita ainda e nenhuma declaração final está escrita.**

- **Quem avalia.** O autor (pesquisador) é o único avaliador da rubrica (seção 12), da classificação de erros (seção 17) e da contagem de pontos de atenção (seção 18). Isso é limitação declarada.
- **Escopo da declaração.** (a) Saídas do Codex nas execuções são **material de pesquisa analisado**, não texto do TCC. (b) Este protocolo, o harness e os oráculos foram redigidos com agentes de IA coordenados pelo autor (fluxo em `AGENT-WORKFLOW.md`); a declaração deve dizê-lo. (c) Qualquer trecho gerado por IA que seja **reutilizado** no TCC (código, trecho de relatório, texto, tabela) exige revisão humana integral antes de entrar no documento.
- **Registro de revisão.** Um registro por trecho reutilizado, com campos fixos em `records.AI_REVIEW_FIELDS` e `schema/ai_review_log_header.csv`: `item_id`, `origem` (ferramenta e versão), `run_id` (se vier de uma execução), `destino_no_texto`, `tipo_uso` (reutilizado, adaptado, apenas analisado), `revisor`, `data_revisao`, `como_foi_verificado` (leitura linha a linha, execução, conferência de fontes), `decisao` (aceito, alterado, descartado), `observacoes`. O arquivo preenchido é mantido pelo autor/integrador no repositório do TCC (`TCC-080`/`TCC-090`), fora de `protocol/`.
- **Texto da declaração** (a ser redigido por `TCC-080`/`TCC-090` com base nesse registro): deve afirmar revisão integral somente para o que constar do registro como revisado, e distinguir o que foi reutilizado do que foi só analisado. Não afirmar revisão que não ocorreu.
