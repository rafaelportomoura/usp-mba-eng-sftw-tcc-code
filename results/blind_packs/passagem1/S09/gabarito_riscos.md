<!-- EVALUATION-ONLY: inventario previo de riscos; nao fornecer ao agente avaliado. -->
# T3 — Inventário prévio de riscos e ambiguidades

## Defeitos do baseline (esperados)

| Req. | Defeito no baseline |
| --- | --- |
| R1 | Sem validação de chave, itens, quantidades ou sku; `available` devolve 0 para sku desconhecido |
| R2 | Verificação e débito intercalados: falha em item posterior deixa débitos parciais |
| R4 | Sem idempotência: repetir a chave desconta novamente e duplica o evento |
| R5 | Sem detecção de conflito de chave |
| R6 | `events` é a lista interna mutável; evento referencia o `items` do chamador |
| R7 | Mantém referência ao `stock` do chamador (e o modifica); retorna o mesmo `items` do chamador |

## Ambiguidades e riscos deliberados

1. Ordem de verificação: chave existente (replay/conflito) antes de estoque. Reproduzir um replay
   após esgotar o estoque deve funcionar; conflito tem precedência sobre estoque insuficiente.
2. Reserva rejeitada por estoque não registra a chave: a mesma chave pode ser reutilizada depois.
3. Igualdade de itens ignora a ordem das chaves do dicionário.
4. Normalização da chave por `strip()` vale também para a comparação.
5. `events` deve ser cópia independente inclusive dos dicionários de cada evento e de `items`; o enunciado
   (R6) agora diz isso explicitamente, então cópia rasa é violação, não ambiguidade.
6. `bool` como quantidade; `1.0` como quantidade.
7. Concorrência/threads não é requisito; premissa a explicitar (risco de lacuna: não há lock).
8. Dicionários RETORNADOS por `reserve` (primeira chamada ou replay) podem compartilhar estado interno: o
   enunciado (R7) só trata dos dados recebidos do chamador, então o oráculo NÃO exige independência do
   retorno (removido após a revisão independente; variantes `A3`/`A4` em `alternatives/` são aceitas).
9. Unicidade de skus em `items` é garantida por ser `dict`.
10. Chave normalizada: `reservation_key` no retorno e nos eventos é a chave após `strip()` (R3, esclarecido).
11. Precedência: validação (R1) antes da consulta de chave existente; chave existente (conflito) antes de
    estoque insuficiente (R1 esclarecido; `test_r1_validation_precedes_existing_key_lookup`).
12. `available` com sku não `str` (inclusive não hashável) lança `InvalidRequestError`.
13. Espaços INTERNOS na chave (`"a b"` vs `"ab"`): o enunciado só define `strip()` (bordas); portanto o
    comportamento não é exigido nem testado. Implementação que colapsa/remove espaços internos é aceita
    (`alternatives/R3_internal_ws_collapsed.py`). Risco residual: duas chaves distintas podem colidir nessa
    variante; não é falha avaliada.
14. Conflito com subconjunto/quantidade alterada de uma chave multi-item (`{A:2,B:1}` registrada, repetida
    com `{A:2}`): R5 ("itens diferentes") exige `KeyConflictError`; testado em
    `test_r5_conflict_with_subset_or_changed_quantity_of_multi_item_key` (mutante `M22`).

## Limitações do oráculo

- Mutantes equivalentes descartados: `register_key_before_stock` (registra e remove a chave antes de falhar).
- Concorrência não é requisito nem testada.
