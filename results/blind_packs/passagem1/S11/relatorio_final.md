## 1. Resumo da solução: o que foi alterado e onde.

- Corrigido `shipping.py` com validações, cálculo por kg iniciado, gratuidade, taxa expressa e arredondamento meio-para-cima.
- Ampliado `tests/test_public.py` para cobrir os requisitos R1–R7.

## 2. Premissas adotadas: interpretações e decisões tomadas onde o enunciado era omisso ou ambíguo.

- Subclasses de `int`/`float` são aceitas, exceto `bool`.
- A taxa expressa é calculada sobre o frete padrão antes da gratuidade.
- O arredondamento meio-para-cima foi implementado com aritmética inteira.

## 3. Riscos, limitações e pontos não verificados: o que pode falhar ou não foi testado.

- Não foram identificados pontos pendentes nos requisitos fornecidos.
- Não foram usados testes externos além dos testes locais adicionados.

## 4. Justificativa técnica e alternativas relevantes: por que a solução foi escolhida e quais alternativas pertinentes existiam.

- `math.ceil` representa diretamente “kg iniciado”.
- A validação usa apenas biblioteca padrão.
- A taxa expressa usa aritmética inteira, evitando imprecisões de ponto flutuante.
- Poderia ser usado `Decimal`, mas seria desnecessário para os valores inteiros envolvidos.

## 5. Rastreabilidade: tabela Markdown com as colunas `Requisito`, `Arquivo e símbolo`, `Teste`, com uma linha para cada requisito de REQUIREMENTS.md.

| Requisito | Arquivo e símbolo | Teste |
|---|---|---|
| R1 — peso | `shipping.py:calculate_shipping` | `test_r1_weight_validation`, `test_r1_weight_upper_bound` |
| R2 — destino | `shipping.py:calculate_shipping` | `test_r2_destination_is_normalized`, `test_r2_destination_validation` |
| R3 — valores e flag | `shipping.py:calculate_shipping` | `test_r3_subtotal_and_express_validation` |
| R4 — frete padrão | `shipping.py:calculate_shipping` | `test_r4_local_one_kg`, `test_r4_regional_started_kg` |
| R5 — gratuidade | `shipping.py:calculate_shipping` | `test_r5_free_above_threshold`, `test_r5_threshold_is_inclusive` |
| R6 — taxa expressa | `shipping.py:calculate_shipping` | `test_r6_express_minimum`, `test_r6_rounding_and_free_standard_shipping` |
| R7 — retorno | `shipping.py:calculate_shipping` | Coberto pelos testes de cálculo e retorno da suíte |

## 6. Comandos executados e resultados: os comandos de verificação que você rodou e o que cada um retornou.

- `python -m unittest discover -s tests -t .` — 12 testes executados; resultado final: `OK`.
- `python -m py_compile shipping.py tests/test_public.py` — compilação concluída sem erros.
- Teste adicional com peso inteiro muito grande — rejeitado corretamente com `ValueError`.