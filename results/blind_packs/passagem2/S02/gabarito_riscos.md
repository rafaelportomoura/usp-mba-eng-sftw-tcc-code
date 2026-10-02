<!-- EVALUATION-ONLY: inventario previo de riscos; nao fornecer ao agente avaliado. -->
# T1 — Inventário prévio de riscos e ambiguidades

Registrado antes de qualquer execução do agente. Serve de gabarito para avaliar se premissas e
riscos declarados pelo agente são pertinentes.

## Defeitos do baseline (esperados)

| Req. | Defeito no baseline |
| --- | --- |
| R1-R3 | Nenhuma validação; entradas inválidas geram valores ou erros não tratados (`TypeError`) |
| R2 | Destino desconhecido cai silenciosamente em `national`; sem normalização de caixa/espaços |
| R4 | `int(weight_kg)` trunca em vez de arredondar para cima o kg iniciado |
| R5 | Comparação `>` torna o limite exclusivo |
| R6 | Taxa expressa calculada sobre o frete já zerado, sem mínimo, com truncamento em vez de meio para cima |

## Ambiguidades e riscos deliberados

1. Armadilha deliberada (NÃO é ambiguidade): R6 define a taxa expressa sobre o frete padrão antes da
   gratuidade. Calculá-la sobre o valor cobrado contradiz o enunciado e produz 0 quando gratuito;
   o oráculo (`test_r6_express_due_when_free`) pune essa leitura. Não avaliar como "premissa a explicitar".
2. Peso fracionário: "kg iniciado" implica `ceil` sem arredondar o peso antes; risco com valores como 1.0000001
   (verificado por `test_r4_tiny_excess_still_started_kg`; mutante `M08` arredonda a 4 casas).
3. `bool` é subclasse de `int`: exige tratamento explícito em R1 e R3.
4. Mínimo de 1000 vs. 25%: ambos os ramos são exercidos pelos testes ocultos.
5. Meio para cima com inteiros: `round()` do Python usa arredondamento bancário e erra 212.5/387.5.
6. Limite de gratuidade: inclusivo, não coberto integralmente pelos testes públicos.
7. Peso exatamente 30 aceito; 30.01 rejeitado.
8. Retorno deve ser `int`, não `float`.

## Limitações do oráculo (revisão independente)

- Pesos absurdos (`10**400`) não são testados: uma solução que converta para `float` e lance
  `OverflowError` seria tecnicamente não conforme a R1, mas penalizá-la seria injusto para o objetivo do estudo.
  A referência foi corrigida para lançar `ValueError` (comparação direta, sem `math.isfinite`).
- Mutantes equivalentes (sem diferença de comportamento) descartados: `min_always`, `nan_allowed`/`isfinite`.
