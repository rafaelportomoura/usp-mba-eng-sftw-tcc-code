# Registro de verificação (comandos e resultados)
_Log da sessão, sanitizado. Saídas acima de 2000 caracteres foram truncadas aqui; o `.jsonl` guarda a íntegra._

## 1. Mensagem do agente

Vou ler os requisitos, inspecionar o módulo e os testes existentes, implementar o comportamento esperado e rodar a suíte completa até ficar verde.

## 2. Comando (saída 0)

```
/usr/bin/zsh -lc "pwd && rg --files -g 'REQUIREMENTS.md' -g '*.py' -g '"'!__pycache__/**'"' | sort && sed -n '1,240p' REQUIREMENTS.md"
```

```text
<WORKSPACE>
REQUIREMENTS.md
inventory.py
tests/__init__.py
tests/test_public.py
# T3 — Reserva de estoque

O módulo `inventory.py` expõe `InventoryService`, as exceções `InvalidRequestError` (subclasse de
`ValueError`), `InsufficientStockError` e `KeyConflictError`. A implementação atual é incompleta.
Complete-a conforme os requisitos, mantendo os nomes públicos.

API: `InventoryService(stock)` com `stock: dict[str, int]`; `reserve(reservation_key, items)` com
`items: dict[str, int]` (sku -> quantidade); `available(sku) -> int`; propriedade `events`.

- **R1 (validação):** `reservation_key` deve ser `str` não vazia após `strip()`; `items` deve ser `dict`
  não vazio; cada `sku` deve ser `str` existente no estoque e cada quantidade `int > 0` (nunca `bool`).
  Violações lançam `InvalidRequestError`. `available` com sku desconhecido (ou que não seja `str`) também
  lança `InvalidRequestError`. A validação precede qualquer consulta a chaves já registradas: uma chamada
  inválida lança `InvalidRequestError` mesmo que a chave já exista.
  O construtor aceita apenas `dict[str, int]` com quantidades `int >= 0`; caso contrário, `InvalidRequestError`.
- **R2 (atomicidade):** se qualquer item não tiver estoque suficiente, lançar `InsufficientStockError`
  sem alterar o estoque de nenhum sku, sem registrar a chave e sem registrar evento.
- **R3 (reserva):** em sucesso, descontar as quantidades e retornar
  `{"reservation_key": key, "items": {sku: qty, ...}, "replayed": False}`, onde `key` é a chave
  normalizada por `strip()` (a mesma usada em R4, R5 e R6).
- **R4 (idempotência):** repetir a mesma chave com os mesmos itens (independente da ordem) não
  desconta novamente, não gera evento novo e retorna o mesmo resultado com `"replayed": True`.
- **R5 (conflito de chave):** repetir a chave com itens diferentes lança `KeyConflictError`, sem
  alterar estoque nem eventos. Chaves são comparadas após `strip()`.
- **R6 (eventos):** cada reserva nova gera exatamente um evento
  `{"typ
[... truncado, 598 caracteres]
```

## 3. Comando (saída 0)

```
/usr/bin/zsh -lc "sed -n '1,300p' inventory.py && printf '\\n--- tests ---\\n' && sed -n '1,360p' tests/test_public.py"
```

```text
"""Reserva de estoque (baseline incompleto)."""


class InvalidRequestError(ValueError):
    pass


class InsufficientStockError(Exception):
    pass


class KeyConflictError(Exception):
    pass


class InventoryService:
    def __init__(self, stock):
        self._stock = stock
        self.events = []

    def available(self, sku):
        return self._stock.get(sku, 0)

    def reserve(self, reservation_key, items):
        for sku, qty in items.items():
            if self._stock.get(sku, 0) < qty:
                raise InsufficientStockError(sku)
            self._stock[sku] -= qty
        self.events.append(
            {"type": "reservation_created", "reservation_key": reservation_key, "items": items}
        )
        return {"reservation_key": reservation_key, "items": items, "replayed": False}

--- tests ---
import unittest

from inventory import (
    InsufficientStockError,
    InvalidRequestError,
    InventoryService,
)


class PublicInventoryTests(unittest.TestCase):
    def setUp(self):
        self.service = InventoryService({"A": 10, "B": 2})

    def test_r3_reserve_deducts_and_returns(self):
        result = self.service.reserve("k1", {"A": 3})
        self.assertEqual(result, {"reservation_key": "k1", "items": {"A": 3}, "replayed": False})
        self.assertEqual(self.service.available("A"), 7)

    def test_r2_insufficient_stock_raises(self):
        with self.assertRaises(InsufficientStockError):
            self.service.reserve("k1", {"B": 5})
        self.assertEqual(self.service.available("B"), 2)

    def test_r1_unknown_sku(self):
        with self.assertRaises(InvalidRequestError):
            self.service.reserve("k1", {"Z": 1})

    def test_r4_idempotent_replay(self):
        self.service.reserve("k1", {"A": 3})
        again = self.service.reserve("k1", {"A": 3})
        self.assertTrue(again["replayed"])
        self.assertEqual(self.service.available("A"), 7)

    def test_r6_event_recorded(self):
        self.service.reserve("k1
[... truncado, 222 caracteres]
```

## 4. Mensagem do agente

Os defeitos centrais são: falta de validação completa, mutação parcial em caso de estoque insuficiente, ausência de idempotência/conflito, referências compartilhadas e `events` exposto diretamente. Vou corrigir isso mantendo a API pública.

## 5. Alteração de arquivos

<WORKSPACE>/inventory.py

## 6. Alteração de arquivos

<WORKSPACE>/inventory.py

## 7. Comando (saída 0)

```
/usr/bin/zsh -lc 'python -m unittest discover -s tests -t .'
```

```text
.....
----------------------------------------------------------------------
Ran 5 tests in 0.000s

OK

```

## 8. Mensagem do agente

A suíte pública já passa. Encontrei e corrigi também um detalhe importante da implementação: como `events` deve ser uma propriedade protegida por cópia, o registro interno precisa usar a lista privada. Agora vou acrescentar testes para os requisitos de isolamento, validação, replay, conflito e atomicidade.

## 9. Alteração de arquivos

<WORKSPACE>/tests/test_public.py

## 10. Comando (saída 1)

```
/usr/bin/zsh -lc "python -m unittest discover -s tests -t . && sed -n '1,260p' inventory.py && git diff -- inventory.py tests/test_public.py"
```

```text
..E........
======================================================================
ERROR: test_input_and_event_results_are_isolated (tests.test_public.PublicInventoryTests.test_input_and_event_results_are_isolated)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "<WORKSPACE>/tests/test_public.py", line 68, in test_input_and_event_results_are_isolated
    events[0]["items"]["A"] = 99
    ~~~~~~^^^
IndexError: list index out of range

----------------------------------------------------------------------
Ran 11 tests in 0.001s

FAILED (errors=1)

```

## 11. Alteração de arquivos

<WORKSPACE>/tests/test_public.py

## 12. Comando (saída 129)

```
/usr/bin/zsh -lc 'python -m unittest discover -s tests -t . && git diff --check && git status --short'
```

```text
...........
----------------------------------------------------------------------
Ran 11 tests in 0.001s

OK
warning: Not a git repository. Use --no-index to compare two paths outside a working tree
usage: git diff --no-index [<options>] <path> <path> [<pathspec>...]

Diff output format options
    -p, --patch           generate patch
    -s, --no-patch        suppress diff output
    -u                    generate patch
    -U, --unified[=<n>]   generate diffs with <n> lines context
    -W, --[no-]function-context
                          generate diffs with <n> lines context
    --raw                 generate the diff in raw format
    --patch-with-raw      synonym for '-p --raw'
    --patch-with-stat     synonym for '-p --stat'
    --numstat             machine friendly --stat
    --shortstat           output only the last line of --stat
    -X, --dirstat[=<param1>,<param2>...]
                          output the distribution of relative amount of changes for each sub-directory
    --cumulative          synonym for --dirstat=cumulative
    --dirstat-by-file[=<param1>,<param2>...]
                          synonym for --dirstat=files,<param1>,<param2>...
    --check               warn if changes introduce conflict markers or whitespace errors
    --summary             condensed summary such as creations, renames and mode changes
    --name-only           show only names of changed files
    --name-status         show only names and status of changed files
    --stat[=<width>[,<name-width>[,<count>]]]
                          generate diffstat
    --stat-width <width>  generate diffstat with a given width
    --stat-name-width <width>
                          generate diffstat with a given name width
    --stat-graph-width <width>
                          generate diffstat with a given graph width
    --stat-count <count>  generate diffstat with limited lines
    --[no-]compact-summary
                          generate compact summary in diffstat
    --binar
[... truncado, 5547 caracteres]
```

## 13. Mensagem do agente

Implementação concluída em `inventory.py` e testes ampliados em `tests/test_public.py`.

Validações, atomicidade, idempotência, conflitos, normalização, eventos e isolamento de dados foram implementados.

Suíte executada com sucesso:

```text
Ran 11 tests ... OK
```
