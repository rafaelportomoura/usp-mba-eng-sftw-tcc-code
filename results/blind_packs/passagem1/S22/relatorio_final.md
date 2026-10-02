## 1. Resumo da solução

- Implementei validação completa, atomicidade, idempotência e conflitos em [inventory.py](<WORKSPACE>/inventory.py).
- Adicionei cópias defensivas para estoque, itens e eventos.
- Ampliei [tests/test_public.py](<WORKSPACE>/tests/test_public.py) para cobrir os requisitos.

## 2. Premissas adotadas

- `bool` foi rejeitado como quantidade, apesar de ser subclasse de `int`.
- Chaves de estoque também precisam ser `str`.
- O estoque pode ser vazio, desde que seja um `dict` válido.

## 3. Riscos, limitações e pontos não verificados

- Não foram testados cenários de concorrência entre chamadas simultâneas.
- Não há persistência externa; todo o estado permanece em memória.

## 4. Justificativa técnica e alternativas relevantes

- A operação verifica todo o estoque antes de qualquer desconto, garantindo atomicidade.
- Reservas são armazenadas por chave normalizada para implementar replay e conflito.
- A propriedade `events` cria cópias dos eventos e de seus itens para impedir mutações externas.
- Foi usada apenas a biblioteca padrão, conforme solicitado.

## 5. Rastreabilidade

| Requisito | Arquivo e símbolo | Teste |
|---|---|---|
| R1 — validação | `inventory.py`: `InventoryService.__init__`, `available`, `_validate_request` | `test_validation_and_available_reject_invalid_values`, `test_invalid_request_is_checked_before_existing_key`, `test_constructor_rejects_invalid_stock` |
| R2 — atomicidade | `inventory.py`: `InventoryService.reserve` | `test_insufficient_stock_is_atomic` |
| R3 — reserva | `inventory.py`: `InventoryService.reserve` | `test_r3_reserve_deducts_and_returns` |
| R4 — idempotência | `inventory.py`: `InventoryService.reserve` | `test_r4_idempotent_replay` |
| R5 — conflito de chave | `inventory.py`: `InventoryService.reserve` | `test_normalized_key_and_conflict_do_not_change_state` |
| R6 — eventos | `inventory.py`: propriedade `events`, `reserve` | `test_r6_event_recorded`, `test_events_are_deep_copied` |
| R7 — isolamento de dados | `inventory.py`: `__init__`, `reserve`, `events` | `test_constructor_and_inputs_are_copied`, `test_events_are_deep_copied` |

## 6. Comandos executados e resultados

- `python -m unittest discover -s tests -t .` — **OK**, 12 testes executados.
- `python -m py_compile inventory.py tests/test_public.py` — **OK**.
- `git diff --check` — executado sem apontar erros; o diretório não é um repositório Git, portanto comandos posteriores de `git diff` não foram aplicáveis.