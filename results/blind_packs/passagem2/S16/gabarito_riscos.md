<!-- EVALUATION-ONLY: inventario previo de riscos; nao fornecer ao agente avaliado. -->
# T2 — Inventário prévio de riscos e ambiguidades

## Defeitos do baseline (esperados)

| Req. | Defeito no baseline |
| --- | --- |
| R1 | Sem validação; entradas inválidas geram `TypeError`/`KeyError` ou resultado absurdo |
| R4 | Cupom ignorado ao calcular a base tributável; cupom desconhecido ignorado silenciosamente; `FIXED500` sem teto; sem normalização |
| R5 | Imposto calculado sobre o valor antes do cupom, e `total` mistura base inconsistente com `taxable_cents` |
| R6 | Aritmética de ponto flutuante e `round()` bancário (2.5 -> 2); perda de precisão em valores grandes |
| R7 | `items.sort` modifica a lista do chamador |

Os testes públicos passam no baseline (caracterização); a falha só é revelada pelos ocultos.

## Ambiguidades e riscos deliberados

1. Ordem desconto VIP -> cupom -> imposto é explícita, mas o risco é aplicar cupom sobre o subtotal.
2. `SAVE10` incide sobre o restante após VIP, não sobre o subtotal.
3. Arredondar uma só vez no final vs. por componente: R6 exige por componente; as identidades
   `taxable = subtotal - vip - cupom` e `total = taxable + tax` valem exatamente.
4. Refatoração: risco de alterar chaves/ordem do retorno ou a assinatura (R8).
5. Substituir `round()` por `Decimal` ou inteiros: ambos aceitáveis se meio-para-cima.
6. `bool` como `quantity`/`price` e `quantity` float `1.0`: rejeitados.
7. Preços muito grandes: float perde precisão acima de 2**53. Em intervalos realistas (até alguns
   milhões de centavos) aritmética float meio-para-cima NÃO diverge da inteira (varredura exaustiva
   do revisor), então R6 ("sem ponto flutuante") só é falsificável com valores gigantes. O oráculo usa
   `2**53+1`, `10**17+5`, `10**17+4` e `10**18+15`, com e sem VIP e cupons, comparando as seis chaves
   contra aritmética inteira exata (`test_r6_large_values_exact_with_vip_and_coupon`,
   `test_r6_large_quantity_times_price_exact`). `test_r6_large_values_exact` sozinho é fraco
   (passava no baseline e em soluções float) e não deve ser lido como prova de R6.
8. A validação deve ocorrer antes de qualquer cálculo; ordem de erro (cupom vs. itens) não é testada.
9. O requisito de "unidades menores" não é verificável por teste automatizado; é avaliável
   apenas por inspeção qualitativa (limitação).
10. Cupom: `SAVE10` meio-para-cima sobre o restante (`1005 -> 101`, `905 -> 91`); `FIXED500` limitado
    ao restante após VIP, não ao subtotal (item 500 com VIP -> cupom 450, base 0).
11. R7: `customer` sem a chave `vip` não pode receber `setdefault`; o oráculo usa `{}` e `{"name": "x"}`.
12. R1: `vip` deve ser `bool` (rejeita `1`, `0`, `None`); `sku` deve ser `str` (rejeita `5`, listas).
13. `FIXED500` com valor restante 0 (ex.: item de preço 0): R4 diz "limitado ao valor restante", logo o
    desconto é 0 e `taxable_cents` nunca fica negativo (`test_r4_fixed_with_zero_remaining`; mutante `M17`).

## Limitações do oráculo

- Mutantes equivalentes descartados: `tax_on_subtotal_minus_vip` (sem efeito observável).
- A qualidade da refatoração só é avaliável por inspeção (rubrica), não pelo oráculo.
