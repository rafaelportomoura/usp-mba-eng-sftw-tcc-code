## 1. Resumo da solução: o que foi alterado e onde.

- Refatorado `pricing.py` em funções de validação, cálculo de subtotal e arredondamento.
- Corrigidos descontos VIP, cupons, tributação e arredondamento sem ponto flutuante.
- Garantida ausência de efeitos colaterais.
- Ampliados os testes em `tests/test_public.py`.

## 2. Premissas adotadas: interpretações e decisões tomadas onde o enunciado era omisso ou ambíguo.

- `bool` é rejeitado nos campos inteiros, apesar de ser subtipo de `int` em Python.
- Cupons são normalizados com `strip().upper()`.
- `sku` deve ser não vazio, mas espaços são aceitos como conteúdo.
- Subclasses de `dict`, `list`, `tuple` e `str` são aceitas.

## 3. Riscos, limitações e pontos não verificados: o que pode falhar ou não foi testado.

- Não foram executados testes externos ou ocultos.
- Não há validação de limites máximos para preços, quantidades ou subtotal.

## 4. Justificativa técnica e alternativas relevantes: por que a solução foi escolhida e quais alternativas pertinentes existiam.

- O arredondamento foi implementado com aritmética inteira: `(valor * percentual + 50) // 100`, garantindo arredondamento de meio para cima.
- A validação foi separada do cálculo para tornar o fluxo legível e evitar `TypeError` em entradas inválidas.
- Não foi usada `decimal`, pois os requisitos pedem cálculo em centavos inteiros e somente biblioteca padrão.

## 5. Rastreabilidade: tabela Markdown com as colunas `Requisito`, `Arquivo e símbolo`, `Teste`, com uma linha para cada requisito de REQUIREMENTS.md.

| Requisito | Arquivo e símbolo | Teste |
|---|---|---|
| R1 | `pricing.py`: `_validate_items`, `_validate_customer`, `_validate_coupon` | `test_validation_rejects_invalid_values`, `test_invalid_containers_raise_value_error` |
| R2 | `pricing.py`: `_subtotal`, `calculate_order` | `test_r2_r5_plain_order` |
| R3 | `pricing.py`: `calculate_order` | `test_r3_vip_discount`, `test_percentages_round_half_up_individually_and_coupon_is_after_vip` |
| R4 | `pricing.py`: `_validate_coupon`, `calculate_order` | `test_r4_save10_discount_amount`, `test_fixed_coupon_is_capped` |
| R5 | `pricing.py`: `calculate_order` | `test_r2_r5_plain_order`, `test_percentages_round_half_up_individually_and_coupon_is_after_vip` |
| R6 | `pricing.py`: `_round_percent` | `test_percentages_round_half_up_individually_and_coupon_is_after_vip` |
| R7 | `pricing.py`: `calculate_order` | `test_does_not_mutate_inputs` |
| R8 | `pricing.py`: `calculate_order` | `test_r8_result_keys` |

## 6. Comandos executados e resultados: os comandos de verificação que você rodou e o que cada um retornou.

- `python -m unittest discover -s tests -t .`  
  Resultado: `Ran 9 tests ... OK`

- `python -m py_compile pricing.py tests/test_public.py`  
  Resultado: `py_compile: OK`

- `git diff --check`  
  Resultado: o diretório não é um repositório Git; a verificação não pôde ser executada.