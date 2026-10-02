# Registro de verificação (comandos e resultados)
_Log da sessão, sanitizado. Saídas acima de 2000 caracteres foram truncadas aqui; o `.jsonl` guarda a íntegra._

## 1. Mensagem do agente

Vou inspecionar os requisitos, o módulo e os testes existentes; depois implemento as correções, acrescento cobertura onde necessário e executo exatamente a suíte solicitada.

## 2. Comando (saída 0)

```
/usr/bin/zsh -lc "pwd && rg --files -g 'REQUIREMENTS.md' -g '*.py' -g 'tests/**' -g '"'!__pycache__'"' | sort"
```

```text
<WORKSPACE>
REQUIREMENTS.md
shipping.py
tests/__init__.py
tests/test_public.py

```

## 3. Comando (saída 0)

```
/usr/bin/zsh -lc "sed -n '1,240p' REQUIREMENTS.md && printf '\\n--- shipping.py ---\\n' && sed -n '1,320p' shipping.py && printf '\\n--- tests/test_public.py ---\\n' && sed -n '1,360p' tests/test_public.py"
```

```text
# T1 — Correção do cálculo de frete

O módulo `shipping.py` expõe `calculate_shipping(weight_kg, destination, subtotal_cents, express=False)`,
que retorna o frete em centavos (`int`). A implementação atual contém defeitos.
Corrija-a para atender aos requisitos abaixo, sem alterar a assinatura.

- **R1 (peso):** `weight_kg` deve ser `int` ou `float` (nunca `bool`), finito, maior que 0 e no máximo 30.
  Caso contrário, lançar `ValueError`.
- **R2 (destino):** `destination` deve ser `str` e, após `strip()` e conversão para minúsculas, ser
  `"local"`, `"regional"` ou `"national"`. Caso contrário, lançar `ValueError`.
- **R3 (valores e flag):** `subtotal_cents` deve ser `int` (nunca `bool`) maior ou igual a 0 e `express`
  deve ser `bool`. Caso contrário, lançar `ValueError`.
- **R4 (frete padrão):** tarifa base por destino: local 850, regional 1550, national 2490 (centavos).
  Acrescentar 200 centavos por cada kg iniciado além do primeiro, isto é, `(ceil(weight_kg) - 1) * 200`.
- **R5 (gratuidade):** se `subtotal_cents >= 20000`, o frete padrão é zerado (limite inclusivo).
- **R6 (taxa expressa):** se `express` for verdadeiro, somar uma taxa de 25% do frete padrão
  (calculado conforme R4, antes da gratuidade), arredondada para centavos com meio para cima,
  com mínimo de 1000 centavos. A taxa expressa permanece devida mesmo quando o frete padrão é gratuito.
- **R7 (retorno):** o retorno é `int` em centavos: frete padrão (ou 0 se gratuito) mais a taxa expressa.

Os testes públicos em `tests/` cobrem apenas parte dos requisitos. Execute-os com:

```
python -m unittest discover -s tests -t .
```

--- shipping.py ---
"""Cálculo de frete (baseline com defeitos)."""


def calculate_shipping(weight_kg, destination, subtotal_cents, express=False):
    base = {"local": 850, "regional": 1550}.get(destination, 2490)
    extra = int(weight_kg) - 1 if weight_kg > 1 else 0
    fee = base + extra * 200
    if subtotal_cents > 20000:
        fee = 0
    if express:
        fee += fee
[... truncado, 873 caracteres]
```

## 4. Mensagem do agente

Os defeitos principais são: destino desconhecido caía silenciosamente em `national`, o peso usava truncamento em vez de `ceil`, o limite de gratuidade era exclusivo, a taxa expressa não aplicava arredondamento “meio para cima” nem permanecia após gratuidade, e não havia validação de entradas. Vou corrigir tudo preservando a API.

## 5. Alteração de arquivos

<WORKSPACE>/shipping.py, <WORKSPACE>/tests/test_public.py

## 6. Comando (saída 0)

```
/usr/bin/zsh -lc 'python -m unittest discover -s tests -t .'
```

```text
...........
----------------------------------------------------------------------
Ran 11 tests in 0.001s

OK

```

## 7. Mensagem do agente

A suíte pública passou (11 testes). Antes de finalizar, encontrei um caso de robustez relevante para entradas extremamente grandes: `math.isfinite()` pode levantar `OverflowError` para um inteiro gigante, embora o requisito exija `ValueError`; vou ajustar a ordem da validação e testar esse caso também.

## 8. Alteração de arquivos

<WORKSPACE>/shipping.py, <WORKSPACE>/tests/test_public.py

## 9. Comando (saída 1)

```
/usr/bin/zsh -lc 'git diff -- shipping.py tests/test_public.py'
```

```text
diff --git a/shipping.py b/tests/test_public.py
index 233f2fe..7e27923 100644
--- a/shipping.py
+++ b/tests/test_public.py
@@ -1,35 +1,53 @@
-"""Cálculo de frete."""
+import unittest
 
-import math
+from shipping import calculate_shipping
 
 
-def calculate_shipping(weight_kg, destination, subtotal_cents, express=False):
-    if (isinstance(weight_kg, bool) or not isinstance(weight_kg, (int, float))):
-        raise ValueError("weight_kg must be a finite number between 0 and 30")
-    # Check the bounds before converting an arbitrary-size int to float.
-    if weight_kg <= 0 or weight_kg > 30 or not math.isfinite(weight_kg):
-        raise ValueError("weight_kg must be a finite number between 0 and 30")
+class PublicShippingTests(unittest.TestCase):
+    def test_r4_local_one_kg(self):
+        self.assertEqual(calculate_shipping(1, "local", 5000), 850)
 
-    if not isinstance(destination, str):
-        raise ValueError("destination must be a supported string")
-    destination = destination.strip().lower()
-    rates = {"local": 850, "regional": 1550, "national": 2490}
-    if destination not in rates:
-        raise ValueError("destination must be local, regional, or national")
+    def test_r4_regional_started_kg(self):
+        # 2.5 kg = 3 kg iniciados => 2 kg adicionais
+        self.assertEqual(calculate_shipping(2.5, "regional", 5000), 1550 + 400)
 
-    if (isinstance(subtotal_cents, bool)
-            or not isinstance(subtotal_cents, int)
-            or subtotal_cents < 0):
-        raise ValueError("subtotal_cents must be a non-negative integer")
-    if not isinstance(express, bool):
-        raise ValueError("express must be a boolean")
+    def test_r5_free_above_threshold(self):
+        self.assertEqual(calculate_shipping(1, "national", 30000), 0)
 
-    standard_fee = rates[destination] + (math.ceil(weight_kg) - 1) * 200
-    standard_shipping = 0 if subtotal_cents >= 20000 else standard_fee
+    def test_r2_invalid_destination(self):
+        w
[... truncado, 1629 caracteres]
```

## 10. Comando (saída 0)

```
/usr/bin/zsh -lc 'python -m unittest discover -s tests -t .'
```

```text
...........
----------------------------------------------------------------------
Ran 11 tests in 0.000s

OK

```

## 11. Mensagem do agente

A execução continua verde. Também corrigi a própria asserção de arredondamento para que ela realmente verifique o empate de `.5` (sem ser mascarada pelo mínimo de 1000 centavos).

## 12. Alteração de arquivos

<WORKSPACE>/tests/test_public.py

## 13. Comando (saída 128)

```
/usr/bin/zsh -lc "python -m unittest discover -s tests -t . && git status --short && nl -ba shipping.py | sed -n '1,180p'"
```

```text
...........
----------------------------------------------------------------------
Ran 11 tests in 0.001s

OK
fatal: not a git repository (or any parent up to mount point /)
Stopping at filesystem boundary (GIT_DISCOVERY_ACROSS_FILESYSTEM not set).

```

## 14. Mensagem do agente

Implementação concluída em:

- [shipping.py](<WORKSPACE>/shipping.py)
- [tests/test_public.py](<WORKSPACE>/tests/test_public.py)

Foram corrigidas validações, arredondamento, peso fracionado, gratuidade e taxa expressa.

Suíte executada com sucesso:

```text
Ran 11 tests
OK
```
