# Registro de verificação (comandos e resultados)
_Log da sessão, sanitizado. Saídas acima de 2000 caracteres foram truncadas aqui; o `.jsonl` guarda a íntegra._

## 1. Mensagem do agente

Vou ler os requisitos, inspecionar o módulo e os testes existentes, implementar o necessário e executar a suíte completa solicitada. Ao final, deixarei o relatório rastreável com base apenas no que foi verificado.

## 2. Comando (saída 0)

```
/usr/bin/zsh -lc "pwd && rg --files -g 'REQUIREMENTS.md' -g '*.py' -g 'tests/**' | sort && sed -n '1,240p' REQUIREMENTS.md"
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
/usr/bin/zsh -lc "sed -n '1,260p' shipping.py && printf '\\n--- tests ---\\n' && sed -n '1,320p' tests/test_public.py && printf '\\n--- git ---\\n' && git status --short"
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

--- tests ---
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

--- git ---
fatal: not a git repository (or any parent up to mount point /)
Stopping at filesystem boundary (GIT_DISCOVERY_ACROSS_FILESYSTEM not set).

```

## 4. Mensagem do agente

Os defeitos confirmados incluem destino desconhecido aceito como nacional, validações ausentes, limite de gratuidade exclusivo, peso fracionário truncado e cálculo express sem mínimo/sem preservar a taxa quando há gratuidade. Vou corrigir esses pontos e ampliar os testes para cobrir cada requisito.

## 5. Alteração de arquivos

<WORKSPACE>/shipping.py, <WORKSPACE>/tests/test_public.py

## 6. Comando (saída 0)

```
/usr/bin/zsh -lc 'python -m unittest discover -s tests -t .'
```

```text
............
----------------------------------------------------------------------
Ran 12 tests in 0.000s

OK

```

## 7. Mensagem do agente

A suíte pública ampliada passou (12 testes). Durante a revisão de bordas, identifiquei que um `int` enorme poderia fazer `math.isfinite` levantar `OverflowError` antes da validação; vou tornar esse caso explicitamente um `ValueError`, conforme R1, e então repetir os comandos de verificação.

## 8. Alteração de arquivos

<WORKSPACE>/shipping.py, <WORKSPACE>/tests/test_public.py

## 9. Comando (saída 0)

```
/usr/bin/zsh -lc 'python -m unittest discover -s tests -t . && python -m py_compile shipping.py tests/test_public.py && git diff -- shipping.py tests/test_public.py 2>/dev/null || true'
```

```text
............
----------------------------------------------------------------------
Ran 12 tests in 0.001s

OK
diff --git a/shipping.py b/tests/test_public.py
index e596f12..931630d 100644
--- a/shipping.py
+++ b/tests/test_public.py
@@ -1,40 +1,59 @@
-"""Cálculo de frete."""
-
-import math
-
-
-def calculate_shipping(weight_kg, destination, subtotal_cents, express=False):
-    valid_weight = False
-    if not isinstance(weight_kg, bool) and isinstance(weight_kg, (int, float)):
-        try:
-            valid_weight = math.isfinite(weight_kg) and 0 < weight_kg <= 30
-        except (OverflowError, TypeError):
-            valid_weight = False
-    if not valid_weight:
-        raise ValueError("weight_kg must be finite and between 0 and 30")
-
-    if not isinstance(destination, str):
-        raise ValueError("destination must be a supported string")
-    destination = destination.strip().lower()
-    base_by_destination = {"local": 850, "regional": 1550, "national": 2490}
-    if destination not in base_by_destination:
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
-    standard_fee = base_by_destination[destination] + (math.ceil(weight_kg) - 1) * 200
-    express_fee = 0
-    if express:
-        # Round 25% to the nearest cent, with ties rounded upward.
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
+        # 
[... truncado, 2088 caracteres]
```

## 10. Mensagem do agente

A implementação e os testes agora passam. Também confirmei a compilação dos arquivos; farei uma última verificação de limites (30 kg, inteiro enorme inválido e tipos booleanos) para fechar os casos de validação antes do relatório.

## 11. Comando (saída 0)

```
/usr/bin/zsh -lc "python - <<'PY'
from shipping import calculate_shipping

assert calculate_shipping(30, \"national\", 0) == 2490 + 29 * 200
for value in (10 ** 1000, True, False):
    try:
        calculate_shipping(value, \"local\", 0)
    except ValueError:
        pass
    else:
        raise AssertionError(value)
print(\"boundary checks: OK\")
PY
python -m unittest discover -s tests -t ."
```

```text
boundary checks: OK
............
----------------------------------------------------------------------
Ran 12 tests in 0.000s

OK

```

## 12. Mensagem do agente

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
