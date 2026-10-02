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
- **R8 (API):** manter `calculate_order(items, customer, coupon=None)` e as seis chaves do retorno.

Os testes públicos em `tests/` cobrem apenas parte dos requisitos. Execute-os com:

```
python -m unittest discover -s tests -t .
```
