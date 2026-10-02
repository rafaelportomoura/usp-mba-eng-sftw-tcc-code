# Registro de verificação (comandos e resultados)
_Log da sessão, sanitizado. Saídas acima de 2000 caracteres foram truncadas aqui; o `.jsonl` guarda a íntegra._

## 1. Mensagem do agente

Vou ler os requisitos, inspecionar o módulo e os testes existentes, implementar as correções e executar a suíte completa conforme solicitado.

## 2. Comando (saída 0)

```
/usr/bin/zsh -lc "pwd && rg --files -g 'REQUIREMENTS.md' -g '*.py' -g '"'!__pycache__/**'"' | sort && sed -n '1,240p' REQUIREMENTS.md"
```

```text
<WORKSPACE>
REQUIREMENTS.md
pricing.py
tests/__init__.py
tests/test_public.py
# T2 — Refatoração do cálculo de pedido

O módulo `pricing.py` expõe `calculate_order(items, customer, coupon=None)`. A função atual é
monolítica e apresenta falhas de cálculo. Refatore-a em unidades menores e legíveis e corrija o
comportamento conforme os requisitos, **preservando a API pública** (nome, assinatura, chaves do
dicionário retornado).

Entradas: `items` é lista/tupla de dicionários `{"sku": str, "unit_price_cents": int, "quantity": int}`;
`customer` é dicionário com a chave opcional `"vip"` (`bool`, padrão `False`); `coupon` é `None` ou `str`.

Retorno: dicionário com as chaves inteiras `subtotal_cents`, `vip_discount_cents`,
`coupon_discount_cents`, `taxable_cents`, `tax_cents`, `total_cents`.

- **R1 (validação):** `items` não vazio; cada item com `sku` `str` não vazia, `unit_price_cents` `int >= 0`
  e `quantity` `int > 0` (nunca `bool`); `customer` deve ser `dict` e `vip`, se presente, `bool`.
  Violações lançam `ValueError`.
- **R2 (subtotal):** soma de `unit_price_cents * quantity`.
- **R3 (VIP):** cliente VIP recebe 10% de desconto sobre o subtotal.
- **R4 (cupom):** aplicado depois do desconto VIP, sobre o valor restante. Cupons (após `strip()` e
  maiúsculas): `SAVE10` (10% do valor restante) e `FIXED500` (500 centavos, limitado ao valor restante).
  Cupom desconhecido ou não `str` lança `ValueError`. `None` significa sem cupom.
- **R5 (tributação):** `taxable_cents = subtotal - vip - cupom`; imposto de 10% sobre `taxable_cents`
  (somente após todos os descontos). `total_cents = taxable_cents + tax_cents`.
- **R6 (arredondamento):** todos os percentuais são calculados em centavos inteiros, sem ponto flutuante,
  arredondando meio para cima, individualmente em cada componente (VIP, cupom, imposto).
- **R7 (sem efeitos colaterais):** não modificar `items`, seus dicionários nem `customer`.
- **R8 (API):** manter `calculate_order(items, customer, coupon=None)` e as seis
[... truncado, 155 caracteres]
```

## 3. Comando (saída 128)

```
/usr/bin/zsh -lc "sed -n '1,260p' pricing.py && printf '\\n--- tests ---\\n' && sed -n '1,320p' tests/test_public.py && printf '\\n--- git status ---\\n' && git status --short"
```

```text
"""Cálculo de pedido (baseline monolítico com defeitos)."""


def calculate_order(items, customer, coupon=None):
    items.sort(key=lambda i: i["sku"])
    subtotal = 0
    for it in items:
        subtotal += it["unit_price_cents"] * it["quantity"]
    vip = 0
    if customer.get("vip"):
        vip = subtotal * 0.10
    rest = subtotal - vip
    disc = 0
    if coupon == "SAVE10":
        disc = rest * 0.10
    elif coupon == "FIXED500":
        disc = 500
    taxable = rest
    tax = taxable * 0.10
    total = taxable - disc + tax
    return {
        "subtotal_cents": int(subtotal),
        "vip_discount_cents": int(round(vip)),
        "coupon_discount_cents": int(round(disc)),
        "taxable_cents": int(round(taxable)),
        "tax_cents": int(round(tax)),
        "total_cents": int(round(total)),
    }

--- tests ---
import unittest

from pricing import calculate_order


def item(sku, price, qty):
    return {"sku": sku, "unit_price_cents": price, "quantity": qty}


class PublicPricingTests(unittest.TestCase):
    def test_r8_result_keys(self):
        result = calculate_order([item("a", 1000, 1)], {})
        self.assertEqual(
            set(result),
            {"subtotal_cents", "vip_discount_cents", "coupon_discount_cents",
             "taxable_cents", "tax_cents", "total_cents"},
        )

    def test_r2_r5_plain_order(self):
        result = calculate_order([item("a", 1000, 2), item("b", 500, 1)], {})
        self.assertEqual(result["subtotal_cents"], 2500)
        self.assertEqual(result["tax_cents"], 250)
        self.assertEqual(result["total_cents"], 2750)

    def test_r3_vip_discount(self):
        result = calculate_order([item("a", 10000, 1)], {"vip": True})
        self.assertEqual(result["vip_discount_cents"], 1000)
        self.assertEqual(result["taxable_cents"], 9000)

    def test_r4_save10_discount_amount(self):
        result = calculate_order([item("a", 10000, 1)], {}, "SAVE10")
        self.assertEqual(result["coupon_discount_ce
[... truncado, 221 caracteres]
```

## 4. Mensagem do agente

Os defeitos principais são a ordenação mutável de `items`, uso de ponto flutuante, desconto de cupom fora da base correta, ausência de validação e arredondamento incompatível. Vou separar validação, arredondamento e cálculo em funções privadas, preservando exatamente a função pública e as seis chaves.

## 5. Alteração de arquivos

<WORKSPACE>/pricing.py, <WORKSPACE>/tests/test_public.py

## 6. Comando (saída 0)

```
/usr/bin/zsh -lc 'python -m unittest discover -s tests -t .'
```

```text
..........
----------------------------------------------------------------------
Ran 10 tests in 0.000s

OK

```

## 7. Mensagem do agente

A implementação foi aplicada e a suíte pública ampliada; os 10 testes estão passando. Vou fazer uma verificação final de casos-limite (incluindo arredondamento do imposto e entrada tupla), compilação e revisar os arquivos para preparar a rastreabilidade exigida.

## 8. Alteração de arquivos

<WORKSPACE>/tests/test_public.py

## 9. Comando (saída 0)

```
/usr/bin/zsh -lc "nl -ba pricing.py | sed -n '1,220p' && printf '\\n--- tests with line numbers ---\\n' && nl -ba tests/test_public.py | sed -n '1,260p'"
```

```text
     1	"""Cálculo de pedido com descontos e tributação em centavos inteiros."""
     2	
     3	
     4	def _round_percent(value, percent):
     5	    """Calcula uma percentagem arredondando meio para cima."""
     6	    return (value * percent + 50) // 100
     7	
     8	
     9	def _validate_items(items):
    10	    if not isinstance(items, (list, tuple)) or not items:
    11	        raise ValueError("items deve ser uma lista ou tupla não vazia")
    12	    for item in items:
    13	        if not isinstance(item, dict):
    14	            raise ValueError("cada item deve ser um dicionário")
    15	        sku = item.get("sku")
    16	        price = item.get("unit_price_cents")
    17	        quantity = item.get("quantity")
    18	        if not isinstance(sku, str) or not sku:
    19	            raise ValueError("sku inválido")
    20	        if isinstance(price, bool) or not isinstance(price, int) or price < 0:
    21	            raise ValueError("unit_price_cents inválido")
    22	        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
    23	            raise ValueError("quantity inválida")
    24	
    25	
    26	def _validate_customer(customer):
    27	    if not isinstance(customer, dict):
    28	        raise ValueError("customer deve ser um dicionário")
    29	    if "vip" in customer and not isinstance(customer["vip"], bool):
    30	        raise ValueError("vip deve ser bool")
    31	
    32	
    33	def _validate_coupon(coupon):
    34	    if coupon is None:
    35	        return None
    36	    if not isinstance(coupon, str):
    37	        raise ValueError("coupon deve ser uma string ou None")
    38	    coupon = coupon.strip().upper()
    39	    if coupon not in {"SAVE10", "FIXED500"}:
    40	        raise ValueError("cupom desconhecido")
    41	    return coupon
    42	
    43	
    44	def _calculate_coupon_discount(coupon, remaining):
    45	    if coupon is None:
    46	        return 0
    47	    if coupon == "SAVE1
[... truncado, 5157 caracteres]
```

## 10. Comando (saída 0)

```
/usr/bin/zsh -lc 'python -m unittest discover -s tests -t .'
```

```text
..........
----------------------------------------------------------------------
Ran 10 tests in 0.001s

OK

```

## 11. Comando (saída 0)

```
/usr/bin/zsh -lc 'python -m py_compile pricing.py tests/test_public.py'
```

```text

```

## 12. Mensagem do agente

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
