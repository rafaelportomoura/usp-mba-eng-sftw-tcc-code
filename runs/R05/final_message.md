## 1. Resumo da solução: o que foi alterado e onde.

- Corrigido [`shipping.py`](/home/rafaelportomoura/.cache/tcc-scratch/R05/workspace/shipping.py).
- Adicionadas validações completas para peso, destino, subtotal e `express`.
- Implementados cálculo por quilograma iniciado, gratuidade, taxa expressa com arredondamento meio para cima e mínimo.
- Ampliados os testes em [`tests/test_public.py`](/home/rafaelportomoura/.cache/tcc-scratch/R05/workspace/tests/test_public.py).

## 2. Premissas adotadas: interpretações e decisões tomadas onde o enunciado era omisso ou ambíguo.

- Tipos derivados de `int`, `float` e `str` são aceitos, exceto `bool`, conforme as restrições explícitas.
- A taxa expressa é calculada sobre o frete padrão antes da gratuidade.
- O arredondamento “meio para cima” foi implementado exclusivamente com aritmética inteira.

## 3. Riscos, limitações e pontos não verificados: o que pode falhar ou não foi testado.

- Não há testes privados disponíveis; apenas os requisitos e a suíte pública foram verificados.
- Não foram testados ambientes Python diferentes do ambiente atual.

## 4. Justificativa técnica e alternativas relevantes: por que a solução foi escolhida e quais alternativas pertinentes existiam.

- `math.ceil` representa diretamente a regra de quilogramas iniciados.
- A aritmética inteira evita imprecisões de ponto flutuante no arredondamento.
- A validação ocorre antes do cálculo, incluindo valores especiais como `NaN`, infinito e `bool`.

## 5. Rastreabilidade: tabela Markdown com as colunas `Requisito`, `Arquivo e símbolo`, `Teste`

| Requisito | Arquivo e símbolo | Teste |
|---|---|---|
| R1 — validação e limite do peso | `shipping.py: calculate_shipping` | `test_r1_weight_validation_and_started_kg_boundaries` |
| R2 — normalização e validação do destino | `shipping.py: calculate_shipping` | `test_r2_invalid_destination`; `test_r2_destination_is_normalized_and_validated` |
| R3 — subtotal e `express` | `shipping.py: calculate_shipping` | `test_r3_values_and_flag_are_validated` |
| R4 — tarifa base e quilogramas iniciados | `shipping.py: calculate_shipping` | `test_r4_local_one_kg`; `test_r4_regional_started_kg`; `test_r1_weight_validation_and_started_kg_boundaries` |
| R5 — gratuidade a partir de 20000 centavos | `shipping.py: calculate_shipping` | `test_r5_free_above_threshold`; `test_r5_threshold_is_inclusive` |
| R6 — taxa expressa, arredondamento e mínimo | `shipping.py: calculate_shipping` | `test_r6_express_minimum`; `test_r6_express_uses_original_fee_and_rounds_half_up` |
| R7 — retorno inteiro em centavos | `shipping.py: calculate_shipping` | Coberto pelos testes de cálculo e validação da suíte |

## 6. Comandos executados e resultados: os comandos de verificação que você rodou e o que cada um retornou.

- `python -m unittest discover -s tests -t .`  
  Resultado: `Ran 10 tests ... OK`.

- `python -m py_compile shipping.py tests/test_public.py`  
  Resultado: compilação concluída sem erros.

- Verificação da assinatura com `inspect.signature`  
  Resultado: `(weight_kg, destination, subtotal_cents, express=False)`.