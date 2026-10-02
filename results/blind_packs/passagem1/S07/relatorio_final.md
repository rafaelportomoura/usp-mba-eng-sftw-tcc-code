## 1. Resumo da solução: o que foi alterado e onde.

- Refatorado `pricing.py` em funções privadas de validação, arredondamento e cálculo.
- Corrigidos descontos VIP, cupons, tributação e arredondamento inteiro.
- Garantida ausência de efeitos colaterais nas entradas.
- Adicionados testes em `tests/test_public.py`.

## 2. Premissas adotadas: interpretações e decisões tomadas onde o enunciado era omisso ou ambíguo.

- `sku` com espaços é aceito, pois é uma string não vazia.
- Subclasses de `dict`, `list` e `tuple` são aceitas via `isinstance`.
- Cupons são normalizados com `strip().upper()` antes da validação.
- O arredondamento “meio para cima” foi implementado exclusivamente com aritmética inteira.

## 3. Riscos, limitações e pontos não verificados: o que pode falhar ou não foi testado.

- Não foram testados requisitos não especificados, como limites máximos de preços, quantidades ou subtotal.
- Não foram adicionadas dependências externas; a implementação usa somente a biblioteca padrão.

## 4. Justificativa técnica e alternativas relevantes: por que a solução foi escolhida e quais alternativas pertinentes existiam.

- O cálculo percentual usa `(valor * percentual + 50) // 100`, evitando ponto flutuante e reproduzindo arredondamento de meio para cima.
- A validação foi separada do cálculo para manter a função pública compatível e tornar cada regra isolada.
- Não foi usada `round()`, pois seu comportamento de empate é arredondamento bancário e poderia divergir do requisito.

## 5. Rastreabilidade: tabela Markdown com as colunas `Requisito`, `Arquivo e símbolo`, `Teste`, com uma linha para cada requisito de REQUIREMENTS.md.

| Requisito | Arquivo e símbolo | Teste |
|---|---|---|
| R1 | `pricing.py:_validate_items`, `_validate_customer`, `_validate_coupon` | `tests/test_public.py:55`, `tests/test_public.py:71` |
| R2 | `pricing.py:calculate_order` | `tests/test_public.py:19` |
| R3 | `pricing.py:calculate_order` | `tests/test_public.py:25`, `tests/test_public.py:39` |
| R4 | `pricing.py:_validate_coupon`, `_calculate_coupon_discount` | `tests/test_public.py:30`, `tests/test_public.py:34`, `tests/test_public.py:39` |
| R5 | `pricing.py:calculate_order` | `tests/test_public.py:19`, `tests/test_public.py:39` |
| R6 | `pricing.py:_round_percent` | `tests/test_public.py:45` |
| R7 | `pricing.py:calculate_order` | `tests/test_public.py:77` |
| R8 | `pricing.py:calculate_order` | `tests/test_public.py:11` |

## 6. Comandos executados e resultados: os comandos de verificação que você rodou e o que cada um retornou.

- `python -m unittest discover -s tests -t .`  
  Resultado: `Ran 10 tests ... OK`

- `python -m py_compile pricing.py tests/test_public.py`  
  Resultado: execução concluída com código de saída `0`.