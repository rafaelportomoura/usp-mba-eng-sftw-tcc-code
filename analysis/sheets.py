"""Fichas de pontuação (CSV), validação em português e gate de 24 h da passagem 2.

Fichas da passagem 1 trazem só colunas que o avaliador preenche às cegas, mais `err_*` (que só valem depois de
fechada a passagem 1: PROTOCOL.md, seção 17). A passagem 2 reavalia apenas C1..C7 (seções 18 e 21: sem
reavaliação de rp_* e ap_*). Nenhuma ficha contém run_id, condição, tarefa, resultado de teste oculto, duração
nem hash.
"""

import csv
import io
import re
from datetime import timedelta

from protocol import manifest as manifest_mod
from protocol import records, sensitivity

C_FIELDS = records.SCORE_FIELDS
CLAIM_FIELDS = records.CLAIM_FIELDS
RP_FIELDS = records.RP_FIELDS + ("rp_confirmed",)
AP_FIELDS = records.AP_FIELDS + ("ap_confirmed", "ap_from_summary")
SENS_FIELDS = ("c2_valid_refs", "c2_rest_declared", "c6_claims", "c6_material", "c6_minor")
ERR_FIELDS = records.ERR_FIELDS
PASS1_COLS = (("blind_id", "scored_at") + C_FIELDS + ("auditability_total", "claims_checked") + CLAIM_FIELDS
              + RP_FIELDS + AP_FIELDS + SENS_FIELDS + ERR_FIELDS + ("notes",))
PASS2_COLS = ("blind_id", "scored_at") + C_FIELDS + ("auditability_total", "notes")
COLS = {1: PASS1_COLS, 2: PASS2_COLS}
# Preenchidos pelo avaliador na passagem 1 (err_* e notes ficam de fora da noção de "ficha completa").
REQUIRED = {1: tuple(c for c in PASS1_COLS if c not in ERR_FIELDS and c != "notes"),
            2: tuple(c for c in PASS2_COLS if c != "notes")}
TEXT_FIELDS = ("blind_id", "scored_at", "notes")
MIN_GAP = timedelta(hours=manifest_mod.MIN_REEVAL_INTERVAL_H)
MIN_GAP_MSG = f"{manifest_mod.MIN_REEVAL_INTERVAL_H} h"


def blank_row(cols, blind_id):
    row = {c: "" for c in cols}
    row["blind_id"] = blind_id
    return row


def dumps(cols, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(cols), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def loads(text, cols):
    reader = csv.DictReader(io.StringIO(text))
    if tuple(reader.fieldnames or ()) != tuple(cols):
        raise ValueError(f"cabeçalho da ficha inválido; esperado: {','.join(cols)}")
    return [dict(r) for r in reader]


def _int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def state(row, passage):
    """'vazia' | 'parcial' | 'completa' (completa = todos os campos exigidos preenchidos)."""
    filled = [c for c in COLS[passage] if c != "blind_id" and str(row.get(c, "")).strip() != ""]
    if not filled:
        return "vazia"
    return "completa" if all(str(row.get(c, "")).strip() != "" for c in REQUIRED[passage]) else "parcial"


def compute_total(row):
    vals = [_int(row.get(c)) for c in C_FIELDS]
    return None if any(v is None for v in vals) else sum(vals)


def pass1_closed(rows1):
    return bool(rows1) and all(state(r, 1) == "completa" for r in rows1)


def pass2_available_at(rows1):
    """Instante a partir do qual a passagem 2 pode começar: 24 h depois da ÚLTIMA pontuação da passagem 1.

    Condição global (não por artefato) para que a mensagem não revele quais pacotes se repetem.
    """
    if not pass1_closed(rows1):
        return None
    return max(records.parse_timestamp(r["scored_at"]) for r in rows1) + MIN_GAP


def validate_rows(rows, passage, n_req=None, closed=False, complete=False):
    """Retorna lista de erros em português (vazia = válido). `n_req`: blind_id -> nº de requisitos da tarefa."""
    errors = []
    n_req = n_req or {}
    seen = set()
    for row in rows:
        bid = row["blind_id"]
        tag = f"{bid}"
        if bid in seen:
            errors.append(f"{tag}: pacote repetido na ficha")
        seen.add(bid)
        st = state(row, passage)
        if st == "vazia":
            if complete:
                errors.append(f"{tag}: ficha ainda vazia")
            continue
        if st == "parcial" and complete:
            missing = [c for c in REQUIRED[passage] if str(row.get(c, "")).strip() == ""]
            errors.append(f"{tag}: ficha incompleta; faltam {', '.join(missing)}")
        ints = {}
        for c in COLS[passage]:
            if c in TEXT_FIELDS or str(row.get(c, "")).strip() == "":
                continue
            v = _int(row[c])
            if v is None or str(v) != str(row[c]).strip():
                errors.append(f"{tag}: {c} deve ser um número inteiro (recebido {row[c]!r})")
                continue
            ints[c] = v
            if c in C_FIELDS and not 0 <= v <= 2:
                errors.append(f"{tag}: {c} deve estar entre 0 e 2 (sem meias notas); recebido {v}")
            elif c != "auditability_total" and v < 0:
                errors.append(f"{tag}: {c} não pode ser negativo")
        total = compute_total(row)
        if total is not None and "auditability_total" in ints and ints["auditability_total"] != total:
            errors.append(f"{tag}: auditability_total={ints['auditability_total']} difere da soma de C1..C7 ({total}); "
                          "deixe vazio e use o comando 'set' ou 'stamp'")
        if any(c in ints for c in C_FIELDS):
            if str(row.get("scored_at", "")).strip() == "":
                errors.append(f"{tag}: pontuação sem scored_at; use o comando 'stamp' (ou 'set', que registra sozinho)")
            else:
                try:
                    records.parse_timestamp(row["scored_at"])
                except ValueError as exc:
                    errors.append(f"{tag}: scored_at inválido ({exc}); use ISO 8601 com data, hora e fuso")
        if passage == 1:
            errors += _validate_pass1_row(tag, ints, n_req.get(bid), closed)
    return errors


def _validate_pass1_row(tag, v, n, closed):
    errors = []
    if "claims_checked" in v and v["claims_checked"] > 10:
        errors.append(f"{tag}: claims_checked > 10 (limite do procedimento de C6, RUBRIC.md)")
    claim_sum = sum(v.get(c, 0) for c in CLAIM_FIELDS)
    if claim_sum > v.get("claims_checked", 0) and any(c in v for c in CLAIM_FIELDS):
        errors.append(f"{tag}: claimdiv_* soma {claim_sum}, mais que claims_checked ({v.get('claims_checked', 0)})")
    rp = sum(v.get(c, 0) for c in records.RP_FIELDS)
    if v.get("rp_confirmed", 0) > rp:
        errors.append(f"{tag}: rp_confirmed excede a soma de rp_assumptions, rp_risks e rp_traces ({rp})")
    ap = sum(v.get(c, 0) for c in records.AP_FIELDS)
    for c in ("ap_confirmed", "ap_from_summary"):
        if v.get(c, 0) > ap:
            errors.append(f"{tag}: {c} excede a soma de ap_decisions, ap_risks e ap_links ({ap})")
    if "c2_rest_declared" in v and v["c2_rest_declared"] not in (0, 1):
        errors.append(f"{tag}: c2_rest_declared deve ser 0 ou 1")
    if "c6_claims" in v and v["c6_claims"] > 10:
        errors.append(f"{tag}: c6_claims > 10")
    if n is not None and v.get("c2_valid_refs", 0) > n:
        errors.append(f"{tag}: c2_valid_refs ({v['c2_valid_refs']}) excede o número de requisitos ({n})")
    if n is not None and all(c in v for c in SENS_FIELDS) and not errors:
        inp = dict(v, n_requirements=n)
        bad = sensitivity.check_inputs(inp)
        errors += [f"{tag}: {e}" for e in bad]
        if not bad:
            if "trace_tests" in v and sensitivity.c2_score(inp) != v["trace_tests"]:
                errors.append(f"{tag}: trace_tests (C2)={v['trace_tests']} difere da regra aplicada às contagens "
                              f"({sensitivity.c2_score(inp)}); a nota oficial segue as âncoras aplicadas às contagens (RUBRIC.md): revise as contagens ou a nota")
            if "fidelity" in v and sensitivity.c6_score(inp) != v["fidelity"]:
                errors.append(f"{tag}: fidelity (C6)={v['fidelity']} difere da regra aplicada às contagens "
                              f"({sensitivity.c6_score(inp)}); a nota oficial segue as âncoras aplicadas às contagens (RUBRIC.md): revise as contagens ou a nota")
    err_filled = [c for c in ERR_FIELDS if c in v]
    if err_filled and not closed:
        errors.append(f"{tag}: err_* só pode ser preenchido depois de fechada a passagem 1 (PROTOCOL.md, seção 17)")
    return errors


def pseudonymize(rows1, rows2, key):
    """Linhas no formato de reevaluation_header com run_id PSEUDÔNIMO (não revela a identidade nem o pareamento)."""
    import hashlib
    def pseud(run_id):
        return "X" + hashlib.sha256(("pseudo:" + run_id).encode()).hexdigest()[:6]
    out = []
    for passage, rows in ((1, rows1), (2, rows2)):
        for r in rows:
            out.append(_reeval_row(r, passage, pseud(key["key"][r["blind_id"]])))
    return out


def _reeval_row(r, passage, run_id):
    row = {"blind_id": r["blind_id"], "run_id": run_id, "pass": passage, "scored_at": r["scored_at"],
           "auditability_total": r["auditability_total"], "notes": r.get("notes", "")}
    row.update({c: r[c] for c in C_FIELDS})
    return row


def reeval_rows(rows1, rows2, key):
    text = io.StringIO()
    w = csv.DictWriter(text, fieldnames=records.reevaluation_header(), lineterminator="\n")
    w.writeheader()
    for passage, rows in ((1, rows1), (2, rows2)):
        for r in rows:
            w.writerow(_reeval_row(r, passage, key["key"][r["blind_id"]]))
    return records.read_reevaluation_csv(text.getvalue())


def validate_reevaluation_blind(rows1, rows2, key):
    """records.validate_reevaluation sobre run_id pseudônimo (mensagens sem identidade). Só com ambas completas."""
    if not (pass1_closed(rows1) and rows2 and all(state(r, 2) == "completa" for r in rows2)):
        return []
    text = io.StringIO()
    w = csv.DictWriter(text, fieldnames=records.reevaluation_header(), lineterminator="\n")
    w.writeheader()
    for row in pseudonymize(rows1, rows2, key):
        w.writerow(row)
    parsed = records.read_reevaluation_csv(text.getvalue())
    return records.validate_reevaluation(parsed, manifest_runs=None)
