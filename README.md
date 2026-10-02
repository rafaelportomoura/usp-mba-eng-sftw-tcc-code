# Repositório experimental — auditabilidade de código gerado por agentes

Artefatos reproduzíveis do experimento do TCC. Especificação canônica em
`/home/rafaelportomoura/Projects/personal/usp-mba-eng-sftw-tcc/.specs/tcc-auditabilidade/`.
Somente biblioteca-padrão e `unittest`. Python fixado em `.python-version`/`pyproject.toml` (3.14.7; o harness exige a mesma série).

## Estrutura

- `tasks/<tarefa>/`: `REQUIREMENTS.md` (enunciado R1..Rn), `baseline/`, `public_tests/`
- `evaluation/<tarefa>/`: `oracle/` (testes ocultos), `reference/` (solução), `alternatives/` (soluções
  corretas que devem passar 100%), `mutants/` (mutantes que devem ser reprovados), `RISKS.md`,
  `baseline_expectations.json`. **Nunca vai para o workspace do agente.** Todo arquivo traz o marcador `EVALUATION-ONLY`.
- `harness/`: geração de workspace isolado, execução de testes, detecção de vazamento, metadados
- `harness/tests/`: testes do harness e validação das referências/baselines
- `protocol/`: reservado para TCC-020 (prompts e protocolo congelado; nada congelado aqui)
- `runs/`, `results/`, `analysis/`: esqueletos para TCC-040 em diante

## Tarefas

| Id | Complexidade | Módulo | Resumo |
| --- | --- | --- | --- |
| `t1_shipping` | baixa | `shipping.py` | corrigir frete (7 requisitos) |
| `t2_order_pricing` | média | `pricing.py` | refatorar pedido preservando API (8 requisitos) |
| `t3_inventory_reservation` | alta | `inventory.py` | reserva atômica, idempotente (7 requisitos) |

## Comandos

```
python3 -m unittest discover -s harness/tests -t .      # testes do harness, referências 100%, baselines, mutação
python3 -m harness.cli verify                           # relatório JSON (referência, baseline, alternativas, mutantes)
python3 -m harness.cli prepare  --task t1_shipping --run-id RUN --out /tmp/ws
python3 -m harness.cli evaluate --task t1_shipping --run-id RUN --workspace /tmp/ws
```

No workspace, o agente roda: `python -m unittest discover -s tests -t .`.
Metadados (`prepare.json`, `evaluation.json`) ficam em `runs/<run_id>/`, fora do workspace.

## Garantias do harness

- Denominador fixo: `*_tests_total` vem da enumeração estática (`ast`) da suíte oficial, independente de erro de sintaxe, crash ou timeout.
- Status: `ok`, `failed`, `import_error`, `timeout`, `runner_error`. Testes pulados/`expectedFailure` não contam como aprovados.
- Resultado por arquivo com nonce; coletor encerra com `os._exit`; timeout mata o grupo de processos.
- Testes públicos e ocultos rodam em cópia; os públicos são os oficiais (`tests/` do agente é sobrescrito na cópia e sinalizado em `agent_modified_public_tests`).
- `prepare` recusa destino dentro de qualquer repositório git.
- `prepare.json`/`evaluation.json` registram hashes de baseline, REQUIREMENTS.md, testes públicos, oráculo e harness, Python e commit git. `evaluation_bundle_hash` (todo `evaluation/`) e `task_evaluation_hash` (`evaluation/<tarefa>/`) cobrem também referências, alternativas, mutantes, `RISKS.md` e `baseline_expectations.json`, sem expor conteúdo.
- Dois timeouts distintos: (1) `test_timeout_s` (padrão 120 s, `runner.DEFAULT_TIMEOUT_S`) limita CADA execução de suíte (pública e oculta, separadamente) feita pelo harness e é registrado em `evaluation.json`; (2) o timeout da SESSÃO do agente (ex.: 12 min no relatório do agente, definido em TCC-020/protocolo) é externo ao harness, que não o impõe nem o registra. Não confundir: um `timeout` de teste vira `hidden_status`/`public_status = "timeout"`; estourar a sessão do agente é registrado no protocolo, não aqui.
- Limite conhecido: o código do agente roda como o usuário, sem sandbox de SO/rede; o isolamento de `evaluation/` durante a sessão do agente depende da configuração do Codex (TCC-020).

## Executor do Codex (`executor/`, preparação de TCC-040)

Executa `codex exec` (codex-cli 0.154.0, decisão Q02) por `run_id`, com `CODEX_HOME` e `HOME` descartáveis fora dos
repositórios, `--ignore-user-config --ignore-rules`, sandbox `workspace-write`, timeout de 720 s com kill do grupo,
captura completa em `runs/<run_id>/` e avaliação pelo harness. Modelo e esforço vêm só do `execution_config.json`
(escolhidos pelo autor em Q11: `gpt-5.5`, esforço `medium`, em `author_choices` do template; snapshot e versão vêm da execução). Credenciais: `--auth-file` explícito, copiado para o `CODEX_HOME` e apagado; nunca versionadas.

```
python3 -m unittest discover -s executor/tests -t .      # usa um `codex` falso; não consome cota
python3 -m executor.cli flags                            # valores para agent.flags / agent.invocation_command
python3 -m executor.cli dry-run --config CFG --task t1_shipping --condition controle
python3 -m executor.cli run --config CFG --task T --condition C --run-id P1 --auth-file AUTH --scratch-dir DIR
python3 -m executor.cli run-all --config CFG --manifest protocol/manifest.json --auth-file AUTH --scratch-dir DIR
```

Execuções reais exigem `protocol/FREEZE.json` íntegro (`--allow-unfrozen` só para ensaios, registrado em `run_meta.json`).
