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
  `{"type": "reservation_created", "reservation_key": key, "items": {...}}`, em ordem cronológica.
  `events` retorna uma cópia independente, inclusive dos dicionários de cada evento e de seus `items`:
  modificar a lista devolvida ou qualquer dicionário contido nela não afeta o serviço.
- **R7 (isolamento de dados):** o serviço não retém referência ao dicionário `stock` nem a `items`
  do chamador; alterá-los depois não afeta o serviço, e o serviço não os modifica.

Os testes públicos em `tests/` cobrem apenas parte dos requisitos. Execute-os com:

```
python -m unittest discover -s tests -t .
```
