"""CLI de pontuação (TCC-060-prep).

  python3 -m analysis.cli build-packs [--force]          gera pacotes cegos, chave, fichas vazias e esqueleto objetivo
  python3 -m analysis.cli score-template [--force]       recria as fichas vazias (não sobrescreve sem --force)
  python3 -m analysis.cli status                         andamento das duas passagens (sem revelar identidade)
  python3 -m analysis.cli set --pass 1 S07 trace_code=2 ... notes="..."   preenche a ficha; calcula o total e registra scored_at
  python3 -m analysis.cli stamp --pass 1 [S07 ...]       registra scored_at (agora) em linhas completas sem carimbo
  python3 -m analysis.cli validate [--pass 1|2] [--completo]   valida as fichas (mensagens em português)
  python3 -m analysis.cli consolidate                    junta fichas, chave e dados objetivos; valida com protocol.records

Nenhum comando exibe a chave S -> run_id nem a condição. O autor é o avaliador único: nada é pontuado aqui.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from protocol import records, sensitivity

from . import blind, objective, sheets
from .paths import RESULTS, ROOT

PACKS = "blind_packs"


class Ctx:
    def __init__(self, results=RESULTS, code_root=ROOT, now=None):
        self.results = Path(results)
        self.code_root = Path(code_root)
        self._now = now

    def now(self):
        return self._now() if self._now else datetime.now().astimezone()

    @property
    def key_path(self):
        return self.results / "blinding_key.json"

    def sheet_path(self, passage):
        return self.results / "fichas" / f"passagem{passage}.csv"

    def key(self):
        if not self.key_path.is_file():
            raise SystemExit("chave ausente: rode 'build-packs' primeiro")
        return json.loads(self.key_path.read_text(encoding="utf-8"))

    def load(self, passage):
        p = self.sheet_path(passage)
        if not p.is_file():
            raise SystemExit(f"ficha ausente: {p}; rode 'build-packs' ou 'score-template'")
        return sheets.loads(p.read_text(encoding="utf-8"), sheets.COLS[passage])

    def save(self, passage, rows):
        p = self.sheet_path(passage)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(sheets.dumps(sheets.COLS[passage], rows), encoding="utf-8")
        tmp.replace(p)

    def n_req(self):
        """blind_id -> nº de requisitos da tarefa (lido do pacote; sem passar pela chave)."""
        out = {}
        for passage in ("passagem1", "passagem2"):
            for d in (self.results / PACKS / passage).glob("S*"):
                req = d / "workspace" / "REQUIREMENTS.md"
                if req.is_file():
                    out[d.name] = blind.requirements_count(req.read_text(encoding="utf-8"))
        return out


def stamp_text(now):
    return now.isoformat(timespec="seconds")


def _templates(ctx, force):
    key = ctx.key()
    made = []
    for passage, entries in ((1, key["pass1"]), (2, key["pass2"])):
        path = ctx.sheet_path(passage)
        if path.exists() and not force:
            continue
        ctx.save(passage, [sheets.blank_row(sheets.COLS[passage], e["blind_id"]) for e in entries])
        made.append(path)
    return made


def cmd_build(ctx, args):
    if (ctx.results / PACKS).exists() and not args.force:
        print("pacotes já existem; use --force para regenerar (as fichas preenchidas NÃO são apagadas)")
        return 1
    if (ctx.results / PACKS).exists():
        import shutil
        shutil.rmtree(ctx.results / PACKS)
    try:
        key = blind.build_all(ctx.code_root, ctx.results / PACKS, ctx.key_path, public_tests_by_run=None)
    except ValueError as exc:
        print(f"RECUSADO: {exc}", file=sys.stderr)
        return 1
    made = _templates(ctx, force=False)
    runs, _ = blind.load_runs(ctx.code_root)
    objective.write_skeleton(ctx.results / "consolidado_esqueleto.csv", objective.skeleton_rows(ctx.code_root, runs))
    print(f"{len(key['pass1'])} pacotes da passagem 1 e {len(key['pass2'])} da passagem 2 em {ctx.results / PACKS}")
    print(f"chave: {ctx.key_path} (NÃO abrir antes de pontuar)")
    for p in made:
        print(f"ficha criada: {p}")
    print("ordem de apresentação da passagem 1 (ficha): " + " ".join(e["blind_id"] for e in key["pass1"]))
    return 0


def cmd_template(ctx, args):
    made = _templates(ctx, args.force)
    print("\n".join(f"ficha criada: {p}" for p in made) or "fichas já existem (use --force para recriar, apaga o que foi preenchido)")
    return 0


def _all_errors(ctx, passages, completo):
    rows1, rows2 = ctx.load(1), ctx.load(2)
    errors = []
    if 1 in passages:
        errors += sheets.validate_rows(rows1, 1, ctx.n_req(), closed=sheets.pass1_closed(rows1), complete=completo)
    if 2 in passages:
        errors += sheets.validate_rows(rows2, 2, complete=completo)
        if any(sheets.state(r, 2) != "vazia" for r in rows2):
            avail = sheets.pass2_available_at(rows1)
            if avail is None:
                errors.append("passagem 2 preenchida antes de fechar a passagem 1")
            errors += sheets.validate_reevaluation_blind(rows1, rows2, ctx.key())
    return errors


def cmd_validate(ctx, args):
    passages = (1, 2) if args.passage is None else (args.passage,)
    errors = _all_errors(ctx, passages, args.completo)
    for passage in passages:
        rows = ctx.load(passage)
        done = [r for r in rows if sheets.state(r, passage) == "completa"]
        print(f"passagem {passage}: {len(done)}/{len(rows)} fichas completas")
        for r in rows:
            t = sheets.compute_total(r)
            if t is not None:
                print(f"  {r['blind_id']}: auditability_total = {t}")
    print("\n".join(f"ERRO {e}" for e in errors) if errors else "OK: nenhum erro encontrado")
    return 1 if errors else 0


def _parse_pairs(pairs):
    out = {}
    for p in pairs:
        if "=" not in p:
            raise SystemExit(f"campo inválido {p!r}: use nome=valor")
        k, v = p.split("=", 1)
        out[k.strip()] = v
    return out


def cmd_set(ctx, args):
    passage = args.passage
    rows = ctx.load(passage)
    rows1 = ctx.load(1)
    row = next((r for r in rows if r["blind_id"] == args.blind_id), None)
    if row is None:
        print(f"pacote {args.blind_id} não consta da ficha da passagem {passage}", file=sys.stderr)
        return 1
    updates = _parse_pairs(args.fields)
    forbidden = [k for k in updates if k in ("blind_id", "scored_at", "auditability_total")]
    unknown = [k for k in updates if k not in sheets.COLS[passage]]
    if forbidden or unknown:
        print(f"campos não permitidos em 'set': {', '.join(forbidden + unknown)}", file=sys.stderr)
        return 1
    now = ctx.now()
    if passage == 2:
        avail = sheets.pass2_available_at(rows1)
        if avail is None:
            print("RECUSADO: a passagem 2 só começa depois de fechar a passagem 1 (18 fichas completas).", file=sys.stderr)
            return 1
        if now < avail:
            print(f"RECUSADO: a passagem 2 só pode começar a partir de {stamp_text(avail)} "
                  f"({sheets.MIN_GAP_MSG} depois da última pontuação da passagem 1).", file=sys.stderr)
            return 1
    elif any(sheets.state(r, 2) != "vazia" for r in ctx.load(2)):
        print("RECUSADO: a passagem 2 já começou; a passagem 1 está encerrada.", file=sys.stderr)
        return 1
    new = dict(row, **updates)
    if passage == 1 and any(k in updates for k in sheets.ERR_FIELDS) and not sheets.pass1_closed(rows1):
        print("RECUSADO: err_* só depois de fechada a passagem 1.", file=sys.stderr)
        return 1
    touches_scores = any(k in updates for k in sheets.C_FIELDS)
    total = sheets.compute_total(new)
    new["auditability_total"] = "" if total is None else str(total)
    if touches_scores or (total is not None and not new["scored_at"]):
        new["scored_at"] = stamp_text(now)
    probe = [new if r["blind_id"] == args.blind_id else r for r in rows]
    errors = [e for e in sheets.validate_rows([new], passage, ctx.n_req(),
                                              closed=passage == 1 and sheets.pass1_closed(rows1))
              if not e.startswith(f"{args.blind_id}: ficha incompleta")]
    if errors:
        print("\n".join(f"ERRO {e}" for e in errors), file=sys.stderr)
        print("nada foi gravado", file=sys.stderr)
        return 1
    ctx.save(passage, probe)
    print(f"{args.blind_id}: gravado" + (f"; auditability_total = {total}; scored_at = {new['scored_at']}" if total is not None else ""))
    print(f"estado da ficha: {sheets.state(new, passage)}")
    return 0


def cmd_stamp(ctx, args):
    passage = args.passage
    rows = ctx.load(passage)
    now = ctx.now()
    if passage == 2:
        avail = sheets.pass2_available_at(ctx.load(1))
        if avail is None or now < avail:
            print("RECUSADO: a passagem 2 ainda não está liberada (24 h após a passagem 1).", file=sys.stderr)
            return 1
    n = 0
    for r in rows:
        if args.ids and r["blind_id"] not in args.ids:
            continue
        total = sheets.compute_total(r)
        if total is None or r["scored_at"]:
            continue
        r["auditability_total"] = str(total)
        r["scored_at"] = stamp_text(now)
        n += 1
    ctx.save(passage, rows)
    print(f"{n} linha(s) carimbada(s) com {stamp_text(now)}")
    return 0


def cmd_status(ctx, args):
    rows1, rows2 = ctx.load(1), ctx.load(2)
    for passage, rows in ((1, rows1), (2, rows2)):
        done = [r["blind_id"] for r in rows if sheets.state(r, passage) == "completa"]
        part = [r["blind_id"] for r in rows if sheets.state(r, passage) == "parcial"]
        todo = [r["blind_id"] for r in rows if sheets.state(r, passage) == "vazia"]
        print(f"passagem {passage}: {len(done)} completas, {len(part)} parciais, {len(todo)} vazias de {len(rows)}")
        if part or todo:
            print("  próximo pacote (ordem da ficha): " + (part + todo)[0])
    avail = sheets.pass2_available_at(rows1)
    print("passagem 2 liberada a partir de: " + (stamp_text(avail) if avail else "(depois de fechar a passagem 1)"))
    return 0


def _read_skeleton(ctx):
    path = ctx.results / "consolidado_esqueleto.csv"
    return {r["run_id"]: r for r in records.read_csv(path.read_text(encoding="utf-8"))}


def cmd_consolidate(ctx, args):
    key = ctx.key()
    rows1, rows2 = ctx.load(1), ctx.load(2)
    errors = _all_errors(ctx, (1,), True)
    if errors:
        print("\n".join(f"ERRO {e}" for e in errors))
        print("consolidação recusada: ajuste a passagem 1")
        return 1
    skeleton = _read_skeleton(ctx)
    recs, inputs = [], {}
    for r in rows1:
        run_id = key["key"][r["blind_id"]]
        rec = dict(skeleton[run_id])
        for c in sheets.C_FIELDS + ("auditability_total", "claims_checked") + sheets.CLAIM_FIELDS + sheets.RP_FIELDS + sheets.AP_FIELDS:
            rec[c] = int(r[c])
        failed = int(rec["hidden_tests_total"]) - int(rec["hidden_tests_passed"])
        err_vals = [r[c].strip() for c in sheets.ERR_FIELDS]
        if all(v == "" for v in err_vals):
            if failed != 0:
                print(f"ERRO {r['blind_id']}: há testes ocultos reprovados; classifique-os em err_* (PROTOCOL.md, seção 17)")
                return 1
            err_vals = ["0"] * len(err_vals)  # nenhum teste reprovado: soma 0 por definição
        for c, v in zip(sheets.ERR_FIELDS, err_vals):
            rec[c] = int(v or 0)
        rec["notes"] = r["notes"]
        recs.append(records.coerce_row(rec))
        req = ctx.results / PACKS / "passagem1" / r["blind_id"] / "workspace" / "REQUIREMENTS.md"
        inputs[run_id] = {"n_requirements": blind.requirements_count(req.read_text(encoding="utf-8")),
                          **{c: int(r[c]) for c in sheets.SENS_FIELDS}}
    runs, _ = blind.load_runs(ctx.code_root)
    freeze = json.loads((ctx.code_root / "protocol" / "FREEZE.json").read_text(encoding="utf-8"))
    errs = records.validate_dataset(sorted(recs, key=lambda x: x["run_id"]), runs, freeze=freeze)
    errs += sensitivity.consistency_errors(recs, inputs)
    if errs:
        print("\n".join(f"ERRO {e}" for e in errs))
        return 1
    (ctx.results / "results.csv").write_text(records.write_csv(sorted(recs, key=lambda x: x["run_id"])), encoding="utf-8")
    for run_id, inp in inputs.items():
        d = ctx.results / "scoring" / run_id
        d.mkdir(parents=True, exist_ok=True)
        (d / "sensitivity_inputs.json").write_text(json.dumps(inp, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {len(recs)} registros válidos em {ctx.results / 'results.csv'}")
    print("sensitivity_inputs.json em results/scoring/<run_id>/ (runs/ não é alterado; copiar é decisão do coordenador)")
    if any(sheets.state(r, 2) != "vazia" for r in rows2):
        e2 = _all_errors(ctx, (2,), True)
        if e2:
            print("\n".join(f"ERRO {e}" for e in e2))
            return 1
        rows = sheets.reeval_rows(rows1, rows2, key)
        errs = records.validate_reevaluation(rows, runs)
        if errs:
            print("\n".join(f"ERRO {e}" for e in errs))
            return 1
        import csv
        import io
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=records.reevaluation_header(), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        (ctx.results / "reevaluation.csv").write_text(out.getvalue(), encoding="utf-8")
        print(f"OK: reavaliação válida em {ctx.results / 'reevaluation.csv'} (python3 -m protocol.cli reeval)")
    else:
        print("passagem 2 ainda não feita: reevaluation.csv não gerado")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="analysis")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("build-packs")
    s.add_argument("--force", action="store_true")
    s = sub.add_parser("score-template")
    s.add_argument("--force", action="store_true")
    sub.add_parser("status")
    s = sub.add_parser("set")
    s.add_argument("--pass", dest="passage", type=int, choices=(1, 2), required=True)
    s.add_argument("blind_id")
    s.add_argument("fields", nargs="*")
    s = sub.add_parser("stamp")
    s.add_argument("--pass", dest="passage", type=int, choices=(1, 2), required=True)
    s.add_argument("ids", nargs="*")
    s = sub.add_parser("validate")
    s.add_argument("--pass", dest="passage", type=int, choices=(1, 2))
    s.add_argument("--completo", action="store_true")
    sub.add_parser("consolidate")
    return p


def main(argv=None, ctx=None):
    args = build_parser().parse_args(argv)
    ctx = ctx or Ctx()
    handler = {"build-packs": cmd_build, "score-template": cmd_template, "status": cmd_status, "set": cmd_set,
               "stamp": cmd_stamp, "validate": cmd_validate, "consolidate": cmd_consolidate}[args.cmd]
    return handler(ctx, args)


if __name__ == "__main__":
    sys.exit(main())
