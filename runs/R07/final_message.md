## 1. Resumo da solução

Atualizado `pricing.py` para:

- Validar entradas conforme R1.
- Calcular descontos e impostos apenas com aritmética inteira.
- Aplicar corretamente VIP, cupons e tributação.
- Evitar efeitos colaterais nos argumentos.
- Preservar a API pública.

Adicionados testes em `tests/test_public.py`.

## 2. Premissas adotadas

- `sku` contendo apenas espaços ainda é considerado não vazio.
- Subclasses de `dict` são aceitas como dicionários.
- Inteiros são aceitos, exceto `bool`.
- Percentuais são arredondados com `(valor + 50) // 100`.

## 3. Riscos, limitações e pontos não verificados

- Testes ocultos não estão disponíveis.
- A checagem via Git não pôde ser executada porque o diretório não é um repositório Git.
- Não foram usadas bibliotecas externas.

## 4. Justificativa técnica e alternativas relevantes

A implementação foi dividida em funções privadas de validação, cálculo de subtotal, arredondamento e cupom. Isso reduz a complexidade da função pública e evita ponto flutuante.

Como alternativa, seria possível usar `decimal.Decimal`, mas a aritmética inteira é mais simples e atende diretamente ao requisito de cálculo em centavos.

## 5. Rastreabilidade

| Requisito | Arquivo e símbolo | Teste |
|---|---|---|
| R1 | `pricing.py:_validate_items`, `_validate_customer` | `test_r1_rejects_invalid_inputs` |
| R2 | `pricing.py:calculate_order` | `test_r2_r5_plain_order` |
| R3 | `pricing.py:calculate_order` | `test_r3_vip_discount` |
| R4 | `pricing.py:_coupon_discount` | `test_r4_save10_discount_amount`, `test_r4_coupon_is_normalized_and_applied_after_vip`, `test_r4_fixed_coupon_is_capped` |
| R5 | `pricing.py:calculate_order` | `test_r2_r5_plain_order`, `test_r4_coupon_is_normalized_and_applied_after_vip` |
| R6 | `pricing.py:_round_percent` | `test_r6_rounds_each_percentage_without_floating_point` |
| R7 | `pricing.py:calculate_order` | `test_r7_does_not_mutate_inputs` |
| R8 | `pricing.py:calculate_order` | `test_r8_result_keys` |

## 6. Comandos executados e resultados

- `python -m unittest discover -s tests -t .`  
  Resultado: `Ran 9 tests ... OK`

- `python -m py_compile pricing.py tests/test_public.py`  
  Resultado: código compilado com sucesso (`exit=0`).

- `git diff --check`  
  Resultado: não executado com sucesso porque o diretório não contém um repositório Git.