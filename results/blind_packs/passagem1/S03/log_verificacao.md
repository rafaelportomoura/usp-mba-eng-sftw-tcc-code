# Registro de verificação (comandos e resultados)
_Log da sessão, sanitizado. Saídas acima de 2000 caracteres foram truncadas aqui; o `.jsonl` guarda a íntegra._

## 1. Mensagem do agente

Vou ler os requisitos, inspecionar o módulo e os testes existentes, depois implementarei os ajustes e executarei a suíte solicitada.

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

## 3. Comando (saída 128)

```
/usr/bin/zsh -lc "sed -n '1,300p' inventory.py && printf '\\n--- tests ---\\n' && sed -n '1,360p' tests/test_public.py && printf '\\n--- git diff/status ---\\n' && git status --short"
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
[... truncado, 386 caracteres]
```

## 4. Mensagem do agente

Os defeitos centrais estão em validação, idempotência/conflitos, atomicidade e isolamento de referências. Vou manter `events` como propriedade somente leitura que devolve cópias profundas dos registros, e armazenar internamente apenas cópias normalizadas.

## 5. Alteração de arquivos

<WORKSPACE>/inventory.py

## 6. Comando (saída 0)

```
/usr/bin/zsh -lc 'python -m unittest discover -s tests -t .'
```

```text
.....
----------------------------------------------------------------------
Ran 5 tests in 0.000s

OK

```

## 7. Mensagem do agente

A suíte pública já passa (5 testes). Vou acrescentar testes focados nos casos que ela não cobre: tipos inválidos, normalização de chaves, conflitos, atomicidade, cópias defensivas e isolamento do `stock`/`items`.

## 8. Alteração de arquivos

<WORKSPACE>/tests/test_public.py

## 9. Comando (saída 0)

```
/usr/bin/zsh -lc 'python -m unittest discover -s tests -t . && python -m py_compile inventory.py tests/test_public.py'
```

```text
............
----------------------------------------------------------------------
Ran 12 tests in 0.001s

OK

```

## 10. Mensagem do agente

A implementação e os testes adicionados passam: 12 testes, todos OK, além da compilação dos módulos. Farei uma última inspeção com numeração de linhas para montar a rastreabilidade exigida.

## 11. Comando (saída 0)

```
/usr/bin/zsh -lc "nl -ba inventory.py | sed -n '1,240p'; printf '\\n--- tests ---\\n'; nl -ba tests/test_public.py | sed -n '1,280p'; printf '\\n--- status ---\\n'; find . -maxdepth 2 -type f -not -path './.git/*' -print | sort"
```

```text
     1	"""Reserva de estoque."""
     2	
     3	
     4	class InvalidRequestError(ValueError):
     5	    pass
     6	
     7	
     8	class InsufficientStockError(Exception):
     9	    pass
    10	
    11	
    12	class KeyConflictError(Exception):
    13	    pass
    14	
    15	
    16	class InventoryService:
    17	    def __init__(self, stock):
    18	        if not isinstance(stock, dict):
    19	            raise InvalidRequestError("stock must be a dict")
    20	        if any(
    21	            not isinstance(sku, str)
    22	            or not isinstance(quantity, int)
    23	            or isinstance(quantity, bool)
    24	            or quantity < 0
    25	            for sku, quantity in stock.items()
    26	        ):
    27	            raise InvalidRequestError("stock must contain str keys and non-negative int quantities")
    28	
    29	        self._stock = stock.copy()
    30	        self._reservations = {}
    31	        self._event_log = []
    32	
    33	    @property
    34	    def events(self):
    35	        return [
    36	            {
    37	                "type": event["type"],
    38	                "reservation_key": event["reservation_key"],
    39	                "items": event["items"].copy(),
    40	            }
    41	            for event in self._event_log
    42	        ]
    43	
    44	    def available(self, sku):
    45	        if not isinstance(sku, str) or sku not in self._stock:
    46	            raise InvalidRequestError("unknown sku")
    47	        return self._stock[sku]
    48	
    49	    def reserve(self, reservation_key, items):
    50	        if not isinstance(reservation_key, str) or not reservation_key.strip():
    51	            raise InvalidRequestError("reservation_key must be a non-empty string")
    52	        if not isinstance(items, dict) or not items:
    53	            raise InvalidRequestError("items must be a non-empty dict")
    54	
    55	        key = reservation_key.strip()
    56	        normali
[... truncado, 7005 caracteres]
```

## 12. Mensagem do agente

## 1. Resumo da solução: o que foi alterado e onde.

- Implementei validações, atomicidade, idempotência, conflitos e normalização em `inventory.py`.
- Adicionei cópias defensivas para estoque, itens, resultados e eventos.
- Ampliei `tests/test_public.py` de 5 para 12 testes.

## 2. Premissas adotadas: interpretações e decisões tomadas onde o enunciado era omisso ou ambíguo.

- Chaves do `stock` também devem ser `str`.
- `bool` não é aceito como quantidade, apesar de ser subclasse de `int`.
- `events` é uma propriedade somente leitura que retorna cópias independentes.
- Resultados de `reserve` também são cópias independentes.

## 3. Riscos, limitações e pontos não verificados: o que pode falhar ou não foi testado.

- Não foram executados testes externos além da suíte local.
- Não foram testados subclasses personalizadas de `dict` ou comportamentos concorrentes.

## 4. Justificativa técnica e alternativas relevantes: por que a solução foi escolhida e quais alternativas pertinentes existiam.

A implementação valida todos os dados antes de consultar reservas ou alterar estado. O estoque é verificado integralmente antes de qualquer desconto, garantindo atomicidade. Reservas e eventos são armazenados em cópias, evitando alterações externas.

Uma alternativa seria usar `copy.deepcopy`, mas os dados aceitos são dicionários com strings e inteiros; cópias rasas dos dicionários são suficientes e mais simples.

## 5. Rastreabilidade: tabela Markdown com as colunas `Requisito`, `Arquivo e símbolo`, `Teste`, com uma linha para cada requisito de REQUIREMENTS.md.

| Requisito | Arquivo e símbolo | Teste |
|---|---|---|
| R1 — validação | `inventory.py`: `InventoryService.__init__`, `available`, `reserve` | `test_validation_rejects_invalid_values_and_unknown_available`, `test_constructor_validates_and_copies_stock`, `test_invalid_repeated_key_is_validated_before_idempotency` |
| R2 — atomicidade | `inventory.py`: `InventoryService.reserve` | `test_insufficient_reservation_is_atomic` |
| R3 — reserva | `inventory.py`: `InventoryService.reserve` | `test_r3_reserve_deducts_and_returns` |
| R4 — idempotência | `inventory.py`: `_reservations`, `reserve` | `test_r4_idempotent_replay`, `test_reservation_normalizes_key_and_items_are_order_independent` |
| R5 — conflito de chave | `inventory.py`: `reserve` | `test_conflicting_key_does_not_change_state` |
| R6 — eventos | `inventory.py`: `events`, `_event_log` | `test_r6_event_recorded`, `test_returned_data_and_input_items_are_isolated` |
| R7 — isolamento de dados | `inventory.py`: cópias de `stock`, `items` e eventos | `test_constructor_validates_and_copies_stock`, `test_returned_data_and_input_items_are_isolated` |

## 6. Comandos executados e resultados: os comandos de verificação que você rodou e o que cada um retornou.

- `python -m unittest discover -s tests -t .` — inicialmente: 5 testes, OK.
- `python -m unittest discover -s tests -t .` — após os ajustes: 12 testes, OK.
- `python -m py_compile inventory.py tests/test_public.py` — compilação concluída sem erros.
