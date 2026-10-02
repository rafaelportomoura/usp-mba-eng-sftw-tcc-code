# Registro de verificação (comandos e resultados)
_Log da sessão, sanitizado. Saídas acima de 2000 caracteres foram truncadas aqui; o `.jsonl` guarda a íntegra._

## 1. Mensagem do agente

Vou ler os requisitos, inspecionar o módulo e os testes existentes, implementar o comportamento esperado e rodar a suíte completa até ficar verde.

## 2. Comando (saída 0)

```
/usr/bin/zsh -lc "pwd && rg --files -g 'REQUIREMENTS.md' -g '*.py' -g '"'!__pycache__'"' | sort && sed -n '1,240p' REQUIREMENTS.md"
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

## 3. Comando (saída 0)

```
/usr/bin/zsh -lc "sed -n '1,260p' pricing.py && printf '\\n--- tests ---\\n' && sed -n '1,320p' tests/test_public.py"
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
[... truncado, 62 caracteres]
```

## 4. Mensagem do agente

Identifiquei os defeitos principais: ordenação mutava a lista, havia ponto flutuante, o cupom era aplicado fora da base tributável e faltava validação. Vou substituir isso por validação explícita e aritmética inteira com arredondamento “meio para cima”.

## 5. Alteração de arquivos

<WORKSPACE>/pricing.py

## 6. Comando (saída 0)

```
/usr/bin/zsh -lc 'python -m unittest discover -s tests -t .'
```

```text
....
----------------------------------------------------------------------
Ran 4 tests in 0.000s

OK

```

## 7. Mensagem do agente

A suíte pública já passa. Vou acrescentar testes locais para os casos que estavam ausentes — validação, normalização/limite de cupons, ordem dos descontos, arredondamento e ausência de mutação — e então executar novamente.

## 8. Alteração de arquivos

<WORKSPACE>/tests/test_public.py

## 9. Comando (saída 1)

```
/usr/bin/zsh -lc 'python -m unittest discover -s tests -t . && git diff -- pricing.py tests/test_public.py'
```

```text
........
----------------------------------------------------------------------
Ran 8 tests in 0.000s

OK
diff --git a/pricing.py b/tests/test_public.py
index f22b057..b684425 100644
--- a/pricing.py
+++ b/tests/test_public.py
@@ -1,66 +1,77 @@
-"""Cálculo de preços de um pedido, usando somente aritmética inteira."""
+import unittest
+from copy import deepcopy
 
+from pricing import calculate_order
 
-def _round_percentage(value, percentage):
-    """Calcula uma percentagem e arredonda meios para cima."""
-    numerator = value * percentage
-    denominator = 100
-    return (numerator * 2 + denominator) // (2 * denominator)
 
+def item(sku, price, qty):
+    return {"sku": sku, "unit_price_cents": price, "quantity": qty}
 
-def _validate_items(items):
-    if not isinstance(items, (list, tuple)) or not items:
-        raise ValueError("items deve ser uma lista ou tupla não vazia")
-    for item in items:
-        if not isinstance(item, dict):
-            raise ValueError("cada item deve ser um dicionário")
-        if not isinstance(item.get("sku"), str) or not item["sku"]:
-            raise ValueError("sku deve ser uma string não vazia")
-        price = item.get("unit_price_cents")
-        if isinstance(price, bool) or not isinstance(price, int) or price < 0:
-            raise ValueError("unit_price_cents deve ser um inteiro não negativo")
-        quantity = item.get("quantity")
-        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
-            raise ValueError("quantity deve ser um inteiro positivo")
 
+class PublicPricingTests(unittest.TestCase):
+    def test_r8_result_keys(self):
+        result = calculate_order([item("a", 1000, 1)], {})
+        self.assertEqual(
+            set(result),
+            {"subtotal_cents", "vip_discount_cents", "coupon_discount_cents",
+             "taxable_cents", "tax_cents", "total_cents"},
+        )
 
-def _validate_customer(customer):
-    if not isinstance(customer, dict):
-   
[... truncado, 3882 caracteres]
```

## 10. Comando (saída 128)

```
/usr/bin/zsh -lc 'git status --short && git diff --stat && git diff --no-renames -- pricing.py && git diff --no-renames -- tests/test_public.py && ls -l pricing.py tests/test_public.py'
```

```text
fatal: not a git repository (or any parent up to mount point /)
Stopping at filesystem boundary (GIT_DISCOVERY_ACROSS_FILESYSTEM not set).

```

## 11. Mensagem do agente

Implementação concluída em `pricing.py`:

- Validação completa das entradas.
- Cálculos em centavos, sem ponto flutuante.
- Arredondamento meio para cima.
- Descontos VIP e cupons aplicados na ordem correta.
- Nenhuma mutação de `items` ou `customer`.
- Testes adicionais para validação, cupons, arredondamento e efeitos colaterais.

Suíte executada com sucesso:

```text
Ran 8 tests
OK
```
