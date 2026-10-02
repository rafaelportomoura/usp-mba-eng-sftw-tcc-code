# Instruções para agentes do experimento

_Regras do repositório reproduzível associado ao TCC de auditabilidade._

---

## 📍 Fonte de verdade

A especificação canônica está em:

`/home/rafaelportomoura/Projects/personal/usp-mba-eng-sftw-tcc/.specs/tcc-auditabilidade/`

Ler `PLAN.md`, `TASKS.md`, `EXPERIMENT.md` e `AGENT-WORKFLOW.md` antes de implementar ou executar qualquer parte do experimento.

## 🏠 Escopo deste repositório

Este repositório contém somente artefatos reproduzíveis do experimento:

- tarefas e baselines
- prompts e protocolo congelado
- harness de execução
- testes públicos e avaliação oculta
- logs, diffs e metadados
- resultados consolidados
- scripts de análise

O texto acadêmico permanece no repositório `usp-mba-eng-sftw-tcc`. Não editar o TCC a partir deste repositório.

## 🧪 Regras experimentais

- preservar três tarefas, duas condições e três repetições por célula
- manter modelo, versão, configuração, timeout e contexto inicial constantes
- executar cada sessão em workspace isolado
- não expor testes ocultos, soluções de referência ou inventários de risco ao agente avaliado
- não solicitar cadeia de pensamento
- registrar timeout como resultado e repetir apenas falha de infraestrutura
- preservar hashes, timestamps, prompts, respostas, diffs e resultados de testes
- não alterar protocolo ou rubrica após as execuções definitivas começarem

## 📦 Estrutura prevista

- `protocol/`: versão congelada e manifesto de execução
- `tasks/`: baselines e testes públicos
- `harness/`: isolamento, execução e captura
- `evaluation/`: oráculos, testes ocultos e rubrica
- `runs/`: artefatos brutos por execução
- `results/`: dados tabulares consolidados
- `analysis/`: scripts, tabelas e gráficos reproduzíveis

## 🎓 Aprendizados e handoff

Aprendizados são registrados no repositório principal, em `.learns/`, e indexados em `docs/LEARNS.md`. O handoff da tarefa também fica no repositório principal, em `.specs/tcc-auditabilidade/handoffs/TASK-ID.md`.

## ✅ Verificação

Toda alteração de código exige testes. Toda execução exige logs completos. Toda análise deve ser reproduzível por comando documentado e produzir os mesmos valores usados no TCC.

