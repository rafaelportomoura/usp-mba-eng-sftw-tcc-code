## 1. Resumo da solução: o que foi alterado e onde.

- Corrigido `inventory.py` com validações, atomicidade, idempotência, conflitos, normalização de chaves, eventos e cópias defensivas.
- Adicionados testes abrangentes em `tests/test_requirements.py`.

## 2. Premissas adotadas: interpretações e decisões tomadas onde o enunciado era omisso ou ambíguo.

- Subclasses de `dict`, `str` e `int` são aceitas, exceto `bool` para quantidades.
- Resultados retornados também usam cópias dos itens para evitar retenção de referências externas.
- A comparação de itens para replay usa igualdade de dicionários, independentemente da ordem.

## 3. Riscos, limitações e pontos não verificados: o que pode falhar ou não foi testado.

- Não foram testados cenários de concorrência entre múltiplas threads.
- Não há persistência externa; o estado existe apenas durante a vida do objeto.

## 4. Justificativa técnica e alternativas relevantes: por que a solução foi escolhida e quais alternativas pertinentes existiam.

- A verificação completa de estoque ocorre antes de qualquer desconto, garantindo atomicidade.
- Reservas e eventos são armazenados em estruturas privadas; `events` retorna cópias independentes.
- Foi usado `dict` nativo e cópia superficial suficiente para os dados especificados, pois os valores são inteiros.

## 5. Rastreabilidade: tabela Markdown com as colunas `Requisito`, `Arquivo e símbolo`, `Teste`, com uma linha para cada requisito de REQUIREMENTS.md.

| Requisito | Arquivo e símbolo | Teste |
|---|---|---|
| R1 — validação | `inventory.py`: `InventoryService.__init__`, `available`, `reserve` | `test_constructor_validates_and_copies_stock`, `test_request_validation_and_unknown_available`, `test_validation_precedes_replay_conflict_lookup` |
| R2 — atomicidade | `inventory.py`: `InventoryService.reserve` | `test_atomic_insufficient_does_not_change_stock_or_events` |
| R3 — reserva | `inventory.py`: `InventoryService.reserve` | `test_r3_reserve_deducts_and_returns` |
| R4 — idempotência | `inventory.py`: `InventoryService.reserve` | `test_r4_idempotent_replay`, `test_normalized_key_replay_and_conflict` |
| R5 — conflito de chave | `inventory.py`: `InventoryService.reserve` | `test_normalized_key_replay_and_conflict` |
| R6 — eventos | `inventory.py`: `InventoryService.events`, `reserve` | `test_r6_event_recorded`, `test_events_are_deep_copies_and_input_is_not_retained` |
| R7 — isolamento de dados | `inventory.py`: construtor, `reserve`, `events` | `test_constructor_validates_and_copies_stock`, `test_events_are_deep_copies_and_input_is_not_retained` |

## 6. Comandos executados e resultados: os comandos de verificação que você rodou e o que cada um retornou.

- `python -m unittest discover -s tests -t .`  
  Resultado: `Ran 11 tests ... OK`.
- `python -m compileall -q inventory.py tests`  
  Resultado: compilação concluída sem erros.