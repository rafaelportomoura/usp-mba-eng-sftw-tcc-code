# Registro de verificação (comandos e resultados)
_Log da sessão, sanitizado. Saídas acima de 2000 caracteres foram truncadas aqui; o `.jsonl` guarda a íntegra._

## 1. Mensagem do agente

Vou ler os requisitos, inspecionar o módulo e os testes existentes, implementar o necessário e validar com a suíte completa indicada.

## 2. Comando (saída 0)

```
/usr/bin/zsh -lc "pwd && rg --files -g 'REQUIREMENTS.md' -g '*.py' -g 'tests/**' -g '"'!__pycache__'"' | sort && sed -n '1,240p' REQUIREMENTS.md"
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
/usr/bin/zsh -lc "sed -n '1,240p' shipping.py && printf '\\n--- tests ---\\n' && sed -n '1,300p' tests/test_public.py && printf '\\n--- status ---\\n' && git status --short"
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

--- status ---
fatal: not a git repository (or any parent up to mount point /)
Stopping at filesystem boundary (GIT_DISCOVERY_ACROSS_FILESYSTEM not set).

```

## 4. Mensagem do agente

Os defeitos confirmados são: destino desconhecido caía silenciosamente em `national`, o limite de gratuidade era exclusivo, o peso não usava quilogramas iniciados, faltavam validações e a taxa expressa não preservava a base antes da gratuidade nem o mínimo exigido. Vou corrigir isso com aritmética inteira para o arredondamento “meio para cima”.

## 5. Alteração de arquivos

<WORKSPACE>/shipping.py, <WORKSPACE>/tests/test_public.py

## 6. Comando (saída 0)

```
/usr/bin/zsh -lc 'python -m unittest discover -s tests -t .'
```

```text
..........
----------------------------------------------------------------------
Ran 10 tests in 0.001s

OK

```

## 7. Mensagem do agente

A implementação foi atualizada e a suíte agora passa com 10 testes. Também acrescentei cobertura para normalização do destino, validações de tipos/faixas, limite inclusivo de gratuidade e taxa expressa calculada sobre o frete anterior ao desconto.

## 8. Mensagem do agente

Implementação concluída em:

- [shipping.py](<WORKSPACE>/shipping.py)
- [tests/test_public.py](<WORKSPACE>/tests/test_public.py)

Validação executada:

```text
Ran 10 tests ... OK
```
