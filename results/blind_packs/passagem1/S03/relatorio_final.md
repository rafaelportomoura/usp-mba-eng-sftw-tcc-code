## 1. Resumo da solução: o que foi alterado e onde.

- Implementei validações, atomicidade, idempotência, conflitos e normalização em `inventory.py`.
- Adicionei cópias defensivas para estoque, itens, resultados e eventos.
- Ampliei `tests/test_public.py` de 5 para 12 testes.

## 2. Premissas adotadas: interpretações e decisões tomadas onde o enunciado era omisso ou ambíguo.

- Chaves do `stock` também devem ser `str`.
- `bool` não é aceito como quantidade, apesar de ser subclasse de `int`.
- `events` é uma propriedade somente leitura que retorna cópias independentes.
- Resultados de `reserve` também são cópias independentes.

## 3. Riscos, limitações e pontos não verificados: o que pode falhar ou não foi testado.

- Não foram executados testes externos além da suíte local.
- Não foram testados subclasses personalizadas de `dict` ou comportamentos concorrentes.

## 4. Justificativa técnica e alternativas relevantes: por que a solução foi escolhida e quais alternativas pertinentes existiam.

A implementação valida todos os dados antes de consultar reservas ou alterar estado. O estoque é verificado integralmente antes de qualquer desconto, garantindo atomicidade. Reservas e eventos são armazenados em cópias, evitando alterações externas.

Uma alternativa seria usar `copy.deepcopy`, mas os dados aceitos são dicionários com strings e inteiros; cópias rasas dos dicionários são suficientes e mais simples.

## 5. Rastreabilidade: tabela Markdown com as colunas `Requisito`, `Arquivo e símbolo`, `Teste`, com uma linha para cada requisito de REQUIREMENTS.md.

| Requisito | Arquivo e símbolo | Teste |
|---|---|---|
| R1 — validação | `inventory.py`: `InventoryService.__init__`, `available`, `reserve` | `test_validation_rejects_invalid_values_and_unknown_available`, `test_constructor_validates_and_copies_stock`, `test_invalid_repeated_key_is_validated_before_idempotency` |
| R2 — atomicidade | `inventory.py`: `InventoryService.reserve` | `test_insufficient_reservation_is_atomic` |
| R3 — reserva | `inventory.py`: `InventoryService.reserve` | `test_r3_reserve_deducts_and_returns` |
| R4 — idempotência | `inventory.py`: `_reservations`, `reserve` | `test_r4_idempotent_replay`, `test_reservation_normalizes_key_and_items_are_order_independent` |
| R5 — conflito de chave | `inventory.py`: `reserve` | `test_conflicting_key_does_not_change_state` |
| R6 — eventos | `inventory.py`: `events`, `_event_log` | `test_r6_event_recorded`, `test_returned_data_and_input_items_are_isolated` |
| R7 — isolamento de dados | `inventory.py`: cópias de `stock`, `items` e eventos | `test_constructor_validates_and_copies_stock`, `test_returned_data_and_input_items_are_isolated` |

## 6. Comandos executados e resultados: os comandos de verificação que você rodou e o que cada um retornou.

- `python -m unittest discover -s tests -t .` — inicialmente: 5 testes, OK.
- `python -m unittest discover -s tests -t .` — após os ajustes: 12 testes, OK.
- `python -m py_compile inventory.py tests/test_public.py` — compilação concluída sem erros.