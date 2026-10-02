# protocol/

RASCUNHO da tarefa TCC-020. **Nada está congelado** (sem `FREEZE.json`, sem hashes finais, sem versão).

- `PROTOCOL.md`: pergunta, hipóteses, variáveis, exclusões, falhas, ordem, itens de Baltes, avaliação cega
- `RUBRIC.md`: rubrica operacional (7 critérios, 0-2)
- `prompts/controle.md`, `prompts/explicacao.md`: prompts das duas condições
- `schema/`: JSON Schema do registro e cabeçalhos CSV
- `config/execution_config.template.json`: modelo do manifesto de execução (preencher em TCC-040)
- `manifest.draft.json`: 18 execuções, semente 20261002 (`python3 -m protocol.cli manifest`)
- `taxonomy.py`, `descriptive.py`: tipos de erro (P1) e resumos descritivos (P1, P2)
- `manifest.py`, `records.py`, `freeze.py`, `cli.py`, `tests/`

Testes: `python3 -m unittest discover -s protocol/tests -t .`
Congelar (somente após a liberação dos oráculos): `python3 -m protocol.cli freeze --release-ref ... --confirm-oracles-released`
