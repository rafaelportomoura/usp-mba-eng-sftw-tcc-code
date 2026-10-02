# Registro de verificação (comandos e resultados)
_Log da sessão, sanitizado. Saídas acima de 2000 caracteres foram truncadas aqui; o `.jsonl` guarda a íntegra._

## 1. Mensagem do agente

Vou ler os requisitos, inspecionar o módulo e os testes existentes, implementar a solução e rodar a suíte solicitada até ficar verde.

## 2. Comando (saída 0)

```
/usr/bin/zsh -lc "pwd && rg --files -g 'REQUIREMENTS.md' -g '*.py' -g '"'!__pycache__/**'"' | sort && sed -n '1,240p' REQUIREMENTS.md"
```

```text
<WORKSPACE>
REQUIREMENTS.md
shipping.py
tests/__init__.py
tests/test_public.py
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

```

## 3. Comando (saída 128)

```
/usr/bin/zsh -lc "sed -n '1,260p' shipping.py && printf '\\n--- tests/test_public.py ---\\n' && sed -n '1,320p' tests/test_public.py && printf '\\n--- git status ---\\n' && git status --short"
```

```text
"""Cálculo de frete (baseline com defeitos)."""


def calculate_shipping(weight_kg, destination, subtotal_cents, express=False):
    base = {"local": 850, "regional": 1550}.get(destination, 2490)
    extra = int(weight_kg) - 1 if weight_kg > 1 else 0
    fee = base + extra * 200
    if subtotal_cents > 20000:
        fee = 0
    if express:
        fee += fee * 25 // 100
    return fee

--- tests/test_public.py ---
import unittest

from shipping import calculate_shipping


class PublicShippingTests(unittest.TestCase):
    def test_r4_local_one_kg(self):
        self.assertEqual(calculate_shipping(1, "local", 5000), 850)

    def test_r4_regional_started_kg(self):
        # 2.5 kg = 3 kg iniciados => 2 kg adicionais
        self.assertEqual(calculate_shipping(2.5, "regional", 5000), 1550 + 400)

    def test_r5_free_above_threshold(self):
        self.assertEqual(calculate_shipping(1, "national", 30000), 0)

    def test_r2_invalid_destination(self):
        with self.assertRaises(ValueError):
            calculate_shipping(1, "mars", 5000)

    def test_r6_express_minimum(self):
        self.assertEqual(calculate_shipping(1, "local", 5000, express=True), 850 + 1000)


if __name__ == "__main__":
    unittest.main()

--- git status ---
fatal: not a git repository (or any parent up to mount point /)
Stopping at filesystem boundary (GIT_DISCOVERY_ACROSS_FILESYSTEM not set).

```

## 4. Mensagem do agente

Os defeitos identificados são: validações ausentes, normalização do destino, arredondamento por kg iniciado, limite de gratuidade inclusivo e taxa expressa calculada sobre o frete antes da gratuidade com mínimo. Vou corrigir esses pontos e ampliar os testes públicos para cobrir as bordas dos requisitos.

## 5. Alteração de arquivos

<WORKSPACE>/shipping.py, <WORKSPACE>/tests/test_public.py

## 6. Comando (saída 1)

```
/usr/bin/zsh -lc 'python -m unittest discover -s tests -t .'
```

```text
...........F
======================================================================
FAIL: test_r6_rounding_and_free_standard_shipping (tests.test_public.PublicShippingTests.test_r6_rounding_and_free_standard_shipping)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "<WORKSPACE>/tests/test_public.py", line 55, in test_r6_rounding_and_free_standard_shipping
    self.assertEqual(calculate_shipping(1, "national", 5000, express=True), 2490 + 623)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 3490 != 3113

----------------------------------------------------------------------
Ran 12 tests in 0.001s

FAILED (failures=1)

```

## 7. Mensagem do agente

A suíte encontrou apenas um erro no teste que escrevi: o caso nacional de 1 kg ainda está sujeito ao mínimo de 1000 centavos, então ele não isolava o arredondamento. Ajustarei o caso para 9 kg, em que a taxa calculada (1022,5) supera o mínimo e evidencia o meio-para-cima.

## 8. Alteração de arquivos

<WORKSPACE>/tests/test_public.py

## 9. Comando (saída 1)

```
/usr/bin/zsh -lc 'python -m unittest discover -s tests -t . && python -m py_compile shipping.py tests/test_public.py'
```

```text
...........F
======================================================================
FAIL: test_r6_rounding_and_free_standard_shipping (tests.test_public.PublicShippingTests.test_r6_rounding_and_free_standard_shipping)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "<WORKSPACE>/tests/test_public.py", line 57, in test_r6_rounding_and_free_standard_shipping
    self.assertEqual(calculate_shipping(1, "national", 20000, express=True), 623)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 1000 != 623

----------------------------------------------------------------------
Ran 12 tests in 0.001s

FAILED (failures=1)

```

## 10. Alteração de arquivos

<WORKSPACE>/tests/test_public.py

## 11. Comando (saída 0)

```
/usr/bin/zsh -lc 'python -m unittest discover -s tests -t . && python -m py_compile shipping.py tests/test_public.py && git diff -- shipping.py tests/test_public.py 2>/dev/null || true'
```

```text
............
----------------------------------------------------------------------
Ran 12 tests in 0.001s

OK
diff --git a/shipping.py b/tests/test_public.py
index d4c8955..206b9d4 100644
--- a/shipping.py
+++ b/tests/test_public.py
@@ -1,40 +1,61 @@
-"""Cálculo de frete."""
-
-import math
-
-
-def calculate_shipping(weight_kg, destination, subtotal_cents, express=False):
-    if (
-        isinstance(weight_kg, bool)
-        or not isinstance(weight_kg, (int, float))
-        or not math.isfinite(weight_kg)
-        or weight_kg <= 0
-        or weight_kg > 30
-    ):
-        raise ValueError("weight_kg must be finite and between 0 and 30")
-
-    if not isinstance(destination, str):
-        raise ValueError("destination must be a supported string")
-    destination = destination.strip().lower()
-    bases = {"local": 850, "regional": 1550, "national": 2490}
-    if destination not in bases:
-        raise ValueError("destination must be local, regional, or national")
-
-    if (
-        isinstance(subtotal_cents, bool)
-        or not isinstance(subtotal_cents, int)
-        or subtotal_cents < 0
-        or not isinstance(express, bool)
-    ):
-        raise ValueError("invalid subtotal_cents or express")
-
-    standard_fee = bases[destination] + (math.ceil(weight_kg) - 1) * 200
-    express_fee = 0
-    if express:
-        # Round 25% to cents using half-up rounding, with integer arithmetic.
-        express_fee = max(1000, (standard_fee * 25 + 50) // 100)
-
-    if subtotal_cents >= 20000:
-        standard_fee = 0
-
-    return standard_fee + express_fee
+import unittest
+
+from shipping import calculate_shipping
+
+
+class PublicShippingTests(unittest.TestCase):
+    def test_r4_local_one_kg(self):
+        self.assertEqual(calculate_shipping(1, "local", 5000), 850)
+
+    def test_r4_regional_started_kg(self):
+        # 2.5 kg = 3 kg iniciados => 2 kg adicionais
+        self.assertEqual(calculate_shipping(2.5, "regional", 5000), 1550 + 400)
+
+    
[... truncado, 2184 caracteres]
```

## 12. Mensagem do agente

A suíte agora passa (12 testes). Durante a revisão de bordas, identifiquei que um inteiro arbitrariamente grande poderia causar `OverflowError` dentro de `math.isfinite` antes de ser rejeitado pelo limite de 30 kg; vou tornar essa validação robusta para que todo valor inválido resulte em `ValueError`, conforme R1.

## 13. Alteração de arquivos

<WORKSPACE>/shipping.py

## 14. Comando (saída 0)

```
/usr/bin/zsh -lc "python -m unittest discover -s tests -t . && python -m py_compile shipping.py tests/test_public.py && python - <<'PY'
from shipping import calculate_shipping
try:
    calculate_shipping(10**400, 'local', 0)
except ValueError:
    print('large integer validation: ValueError')
else:
    raise AssertionError('large integer was not rejected')
PY
sed -n '1,220p' shipping.py && sed -n '1,220p' tests/test_public.py"
```

```text
............
----------------------------------------------------------------------
Ran 12 tests in 0.001s

OK
large integer validation: ValueError
"""Cálculo de frete."""

import math


def calculate_shipping(weight_kg, destination, subtotal_cents, express=False):
    if isinstance(weight_kg, bool) or not isinstance(weight_kg, (int, float)):
        raise ValueError("weight_kg must be finite and between 0 and 30")
    if weight_kg <= 0 or weight_kg > 30 or not math.isfinite(weight_kg):
        raise ValueError("weight_kg must be finite and between 0 and 30")

    if not isinstance(destination, str):
        raise ValueError("destination must be a supported string")
    destination = destination.strip().lower()
    bases = {"local": 850, "regional": 1550, "national": 2490}
    if destination not in bases:
        raise ValueError("destination must be local, regional, or national")

    if (
        isinstance(subtotal_cents, bool)
        or not isinstance(subtotal_cents, int)
        or subtotal_cents < 0
        or not isinstance(express, bool)
    ):
        raise ValueError("invalid subtotal_cents or express")

    standard_fee = bases[destination] + (math.ceil(weight_kg) - 1) * 200
    express_fee = 0
    if express:
        # Round 25% to cents using half-up rounding, with integer arithmetic.
        express_fee = max(1000, (standard_fee * 25 + 50) // 100)

    if subtotal_cents >= 20000:
        standard_fee = 0

    return standard_fee + express_fee
import unittest

from shipping import calculate_shipping


class PublicShippingTests(unittest.TestCase):
    def test_r4_local_one_kg(self):
        self.assertEqual(calculate_shipping(1, "local", 5000), 850)

    def test_r4_regional_started_kg(self):
        # 2.5 kg = 3 kg iniciados => 2 kg adicionais
        self.assertEqual(calculate_shipping(2.5, "regional", 5000), 1550 + 400)

    def test_r5_free_above_threshold(self):
        self.assertEqual(calculate_shipping(1, "national", 30000), 0)

    def test_r2_
[... truncado, 2010 caracteres]
```

## 15. Mensagem do agente

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
