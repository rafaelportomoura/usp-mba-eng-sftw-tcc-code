## 1. Resumo da solução: o que foi alterado e onde.

- Implementei todos os requisitos em `inventory.py`.
- Adicionei validações, cópia defensiva, idempotência, conflitos, atomicidade e eventos isolados.
- Ampliei `tests/test_public.py` com testes de validação, isolamento, atomicidade, normalização e ordem independente.

## 2. Premissas adotadas: interpretações e decisões tomadas onde o enunciado era omisso ou ambíguo.

- Chaves de estoque também devem ser `str`, conforme `dict[str, int]`.
- `bool` é rejeitado como quantidade, apesar de ser subtipo de `int`.
- Resultados de `reserve()` também retornam cópias independentes dos itens internos.

## 3. Riscos, limitações e pontos não verificados: o que pode falhar ou não foi testado.

- Não foram executados testes externos além da suíte local.
- Não há persistência entre instâncias; reservas existem apenas durante a vida do serviço.

## 4. Justificativa técnica e alternativas relevantes: por que a solução foi escolhida e quais alternativas pertinentes existiam.

- O estado interno usa cópias (`dict`) para impedir mutações externas.
- A validação completa ocorre antes da consulta de idempotência e antes de qualquer alteração.
- A disponibilidade é verificada para todos os itens antes de qualquer desconto, garantindo atomicidade.
- A propriedade `events` cria cópias dos eventos e dos respectivos itens.

## 5. Rastreabilidade: tabela Markdown com as colunas `Requisito`, `Arquivo e símbolo`, `Teste`, com uma linha para cada requisito de REQUIREMENTS.md.

| Requisito | Arquivo e símbolo | Teste |
|---|---|---|
| R1 — validação | `inventory.py: InventoryService.__init__`, `available`, `reserve` | `test_validation_is_strict_and_precedes_replay`, `test_constructor_rejects_invalid_stock`, `test_r1_unknown_sku` |
| R2 — atomicidade | `inventory.py: InventoryService.reserve` | `test_r2_insufficient_stock_raises`, `test_atomicity_and_isolation` |
| R3 — reserva | `inventory.py: InventoryService.reserve` | `test_r3_reserve_deducts_and_returns` |
| R4 — idempotência | `inventory.py: InventoryService._reservations`, `reserve` | `test_r4_idempotent_replay`, `test_r4_replay_ignores_item_order` |
| R5 — conflito de chave | `inventory.py: InventoryService.reserve` | `test_key_conflict_and_normalization` |
| R6 — eventos | `inventory.py: InventoryService.events`, `reserve` | `test_r6_event_recorded`, `test_atomicity_and_isolation` |
| R7 — isolamento de dados | `inventory.py: InventoryService.__init__`, `events`, `reserve` | `test_atomicity_and_isolation` |

## 6. Comandos executados e resultados: os comandos de verificação que você rodou e o que cada um retornou.

- `python -m unittest discover -s tests -t .`  
  Resultado: `Ran 10 tests ... OK`.

- `python -m py_compile inventory.py tests/test_public.py`  
  Resultado: conclusão com código de saída `0`.