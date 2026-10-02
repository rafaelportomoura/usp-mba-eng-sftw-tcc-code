# Registro de verificação (comandos e resultados)
_Log da sessão, sanitizado. Saídas acima de 2000 caracteres foram truncadas aqui; o `.jsonl` guarda a íntegra._

## 1. Mensagem do agente

Vou ler os requisitos, inspecionar o módulo e os testes existentes, implementar o comportamento solicitado e rodar a suíte completa até ficar verde.

## 2. Comando (saída 0)

```
/usr/bin/zsh -lc "pwd && rg --files -g 'REQUIREMENTS.md' -g '*.py' -g 'tests/**' | sort && sed -n '1,240p' REQUIREMENTS.md"
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

Os defeitos centrais estão no armazenamento por referência, na falta de validação, na atomicidade e na ausência de controle de idempotência/conflitos. Vou manter a API pública e usar cópias rasas adequadas aos dicionários especificados.

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

A suíte pública já passa. Encontrei e corrigi um detalhe importante durante a implementação: como `events` deve ser uma cópia, o registro interno precisa usar a coleção privada. Agora vou acrescentar testes para os requisitos que os testes públicos não cobrem e executar tudo novamente.

## 9. Alteração de arquivos

<WORKSPACE>/tests/test_public.py

## 10. Comando (saída 1)

```
/usr/bin/zsh -lc "python -m unittest discover -s tests -t . && sed -n '1,260p' inventory.py && git diff -- inventory.py tests/test_public.py"
```

```text
.........
----------------------------------------------------------------------
Ran 9 tests in 0.001s

OK
"""Reserva de estoque."""


class InvalidRequestError(ValueError):
    pass


class InsufficientStockError(Exception):
    pass


class KeyConflictError(Exception):
    pass


class InventoryService:
    def __init__(self, stock):
        if not isinstance(stock, dict):
            raise InvalidRequestError("stock must be a dict")
        for sku, quantity in stock.items():
            if not isinstance(sku, str) or not isinstance(quantity, int) or isinstance(quantity, bool):
                raise InvalidRequestError("stock must contain str keys and non-negative int quantities")
            if quantity < 0:
                raise InvalidRequestError("stock quantities must be non-negative")
        self._stock = dict(stock)
        self._reservations = {}
        self._events = []

    @property
    def events(self):
        return [
            {
                "type": event["type"],
                "reservation_key": event["reservation_key"],
                "items": dict(event["items"]),
            }
            for event in self._events
        ]

    def available(self, sku):
        if not isinstance(sku, str) or sku not in self._stock:
            raise InvalidRequestError("unknown sku")
        return self._stock[sku]

    def reserve(self, reservation_key, items):
        key = self._validate_request(reservation_key, items)
        normalized_items = dict(items)
        existing = self._reservations.get(key)
        if existing is not None:
            if existing != normalized_items:
                raise KeyConflictError(key)
            return {"reservation_key": key, "items": dict(existing), "replayed": True}

        # Check all items before changing any stock, preserving atomicity.
        for sku, qty in normalized_items.items():
            if self._stock[sku] < qty:
                raise InsufficientStockError(sku)
        for sku, qty in norm
[... truncado, 7709 caracteres]
```

## 11. Comando (saída 128)

```
/usr/bin/zsh -lc "git status --short && git diff --stat && git diff --no-ext-diff -- inventory.py | sed -n '1,220p' && git diff --no-ext-diff -- tests/test_public.py | sed -n '1,220p'"
```

```text
fatal: not a git repository (or any parent up to mount point /)
Stopping at filesystem boundary (GIT_DISCOVERY_ACROSS_FILESYSTEM not set).

```

## 12. Mensagem do agente

Os 9 testes passam, incluindo isolamento de entradas/eventos, normalização de chave, conflito, validação de `bool` e atomicidade de reservas com múltiplos itens. Vou fazer uma última execução exatamente no comando solicitado e uma checagem de sintaxe.

## 13. Comando (saída 0)

```
/usr/bin/zsh -lc 'python -m unittest discover -s tests -t . && python -m py_compile inventory.py tests/test_public.py'
```

```text
.........
----------------------------------------------------------------------
Ran 9 tests in 0.000s

OK

```

## 14. Mensagem do agente

Implementação concluída em `inventory.py`, com testes ampliados em `tests/test_public.py`.

Incluído:

- Validação completa de estoque, reservas e SKUs.
- Reservas atômicas.
- Idempotência e conflitos de chave.
- Normalização via `strip()`.
- Eventos protegidos contra mutação externa.
- Isolamento dos dicionários recebidos.

Verificação final:

```text
Ran 9 tests
OK
```
