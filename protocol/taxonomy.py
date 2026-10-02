"""Taxonomia de tipos de erro (P1) e mapa PROPOSTO de classificação padrão. RASCUNHO.

Taxonomia e mapa são decisões do autor, sem fonte externa, pendentes de aprovação antes do
congelamento. Servem para classificar (a) testes ocultos reprovados e (b) alegações do relatório
que divergem do código. O mapa é definido a priori (antes de qualquer execução) a partir dos
requisitos R# de tasks/*/REQUIREMENTS.md e dos RISKS.md; a classificação padrão pode ser
substituída pelo avaliador somente com justificativa registrada (PROTOCOL.md, seção 17).
"""

import re

VALIDACAO = "validacao_entrada"
REGRA = "regra_negocio"
NUMERICO = "arredondamento_numerico"
ATOMICIDADE = "atomicidade_estado"
IDEMPOTENCIA = "idempotencia_conflito"
CONTRATO = "contrato_api"
OUTROS = "outros"
RELATO = "relato_verificacao"  # somente para alegações do relatório

# Tipos aplicáveis a testes ocultos reprovados (ordem = ordem das colunas err_*).
ERROR_TYPES = (VALIDACAO, REGRA, NUMERICO, ATOMICIDADE, IDEMPOTENCIA, CONTRATO, OUTROS)
# Tipos aplicáveis a alegações divergentes (colunas claimdiv_*): os mesmos mais o relato.
CLAIM_TYPES = ERROR_TYPES + (RELATO,)

# Classificação padrão por (tarefa, requisito). Concorrência/threads não é requisito de nenhuma
# tarefa (RISKS.md T3, item 7) e, por isso, não há tipo próprio.
REQUIREMENT_DEFAULT = {
    "t1_shipping": {1: VALIDACAO, 2: VALIDACAO, 3: VALIDACAO, 4: REGRA, 5: REGRA, 6: NUMERICO, 7: CONTRATO},
    "t2_order_pricing": {1: VALIDACAO, 2: REGRA, 3: REGRA, 4: REGRA, 5: REGRA, 6: NUMERICO,
                         7: ATOMICIDADE, 8: CONTRATO},
    "t3_inventory_reservation": {1: VALIDACAO, 2: ATOMICIDADE, 3: CONTRATO, 4: IDEMPOTENCIA,
                                 5: IDEMPOTENCIA, 6: ATOMICIDADE, 7: ATOMICIDADE},
}

# Exceções por teste oculto, quando o mecanismo falho difere do tipo do requisito.
TEST_OVERRIDE = {
    "t1_shipping": {
        "test_r4_fractional_weights_round_up": NUMERICO,
        "test_r4_tiny_excess_still_started_kg": NUMERICO,
        "test_r6_minimum_applies": REGRA,
        "test_r6_percentage_above_minimum": REGRA,
        "test_r6_express_due_when_free": REGRA,
    },
    "t2_order_pricing": {
        "test_r3_vip_false_no_discount": REGRA,
        "test_r4_save10_half_up_on_remaining": NUMERICO,
        "test_r4_unknown_or_invalid_coupon": VALIDACAO,
    },
    "t3_inventory_reservation": {
        "test_r2_exact_stock_allowed_and_zero_stock_rejected": REGRA,
        "test_r6_events_chronological": REGRA,
        "test_r3_key_is_normalized_in_result_and_event": REGRA,
    },
}

_TEST_RE = re.compile(r"(test_r(\d+)_\w+)")


def test_name(identifier):
    """Extrai 'test_rN_...' de um identificador (por exemplo 'test_hidden.Cls.test_r4_x')."""
    m = _TEST_RE.search(identifier)
    return m.group(1) if m else None


def default_error_type(task_id, identifier):
    """Tipo padrão de um teste oculto; None quando não há mapa (classificar manualmente)."""
    name = test_name(identifier)
    if name is None:
        return None
    override = TEST_OVERRIDE.get(task_id, {}).get(name)
    if override:
        return override
    req = int(_TEST_RE.search(name).group(2))
    return REQUIREMENT_DEFAULT.get(task_id, {}).get(req)


def default_requirement_type(task_id, requirement):
    """Tipo padrão de uma alegação sobre o requisito `requirement` (inteiro)."""
    return REQUIREMENT_DEFAULT.get(task_id, {}).get(requirement)


def err_field(error_type):
    return f"err_{error_type}"


def claim_field(claim_type):
    return f"claimdiv_{claim_type}"
