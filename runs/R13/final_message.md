## 1. Resumo da solução: o que foi alterado e onde.

- Corrigido `shipping.py`:
  - validação completa de peso, destino, subtotal e `express`;
  - cálculo por quilogramas iniciados;
  - gratuidade no limite inclusivo de 20.000 centavos;
  - taxa expressa mínima de 1.000 centavos e arredondamento meio para cima;
  - taxa expressa mantida quando o frete padrão é gratuito.
- Ampliados os testes em `tests/test_public.py`, totalizando 12 testes.

## 2. Premissas adotadas: interpretações e decisões tomadas onde o enunciado era omisso ou ambíguo.

- Tipos inválidos sempre resultam em `ValueError`.
- Destinos são normalizados com `strip()` e `lower()`.
- A taxa expressa é calculada sobre o frete padrão antes da gratuidade.
- O arredondamento de 25% foi implementado com aritmética inteira para garantir “meio para cima”.

## 3. Riscos, limitações e pontos não verificados: o que pode falhar ou não foi testado.

- Não foram identificadas limitações funcionais nos requisitos descritos.
- A verificação foi feita apenas com a suíte local e casos de limite relacionados ao módulo.

## 4. Justificativa técnica e alternativas relevantes: por que a solução foi escolhida e quais alternativas pertinentes existiam.

- `math.ceil()` implementa diretamente o conceito de quilogramas iniciados.
- `math.isfinite()` valida valores numéricos finitos.
- A taxa expressa usa `(valor * 25 + 50) // 100`, evitando dependência de ponto flutuante.
- Não foram usadas bibliotecas externas.

## 5. Rastreabilidade: tabela Markdown com as colunas `Requisito`, `Arquivo e símbolo`, `Teste`, com uma linha para cada requisito de REQUIREMENTS.md.

| Requisito | Arquivo e símbolo | Teste |
|---|---|---|
| R1 — validação do peso | `shipping.py: calculate_shipping` | `test_r1_invalid_weights`; verificação de 30 kg e inteiro enorme |
| R2 — validação e normalização do destino | `shipping.py: calculate_shipping` | `test_r2_invalid_destination`; `test_r2_normalizes_destination`; `test_r2_invalid_destination_types` |
| R3 — subtotal e flag expressa | `shipping.py: calculate_shipping` | `test_r3_invalid_subtotal_and_express` |
| R4 — frete padrão | `shipping.py: calculate_shipping` | `test_r4_local_one_kg`; `test_r4_regional_started_kg` |
| R5 — gratuidade inclusiva | `shipping.py: calculate_shipping` | `test_r5_free_above_threshold`; `test_r5_free_at_threshold` |
| R6 — taxa expressa | `shipping.py: calculate_shipping` | `test_r6_express_minimum`; `test_r6_express_is_due_when_standard_shipping_is_free`; `test_r6_express_rounds_half_up` |
| R7 — retorno inteiro | `shipping.py: calculate_shipping` | Verificado pelos 12 testes da suíte |

## 6. Comandos executados e resultados: os comandos de verificação que você rodou e o que cada um retornou.

- `python -m unittest discover -s tests -t .`
  - Resultado: `Ran 12 tests ... OK`
- `python -m py_compile shipping.py tests/test_public.py`
  - Resultado: execução concluída sem erros.
- Verificação manual de limites com `python`
  - Resultado: `boundary checks: OK`
- Suíte final:
  - Resultado: `Ran 12 tests ... OK`