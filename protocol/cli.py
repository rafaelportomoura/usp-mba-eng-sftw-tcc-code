"""CLI do protocolo.

  python3 -m protocol.cli manifest [--seed N] [--out PATH]   gera o manifesto RASCUNHO (determinístico)
  python3 -m protocol.cli fallback                           lista as 12 execuções balanceadas
  python3 -m protocol.cli blind [--completed R01,R02,...]    plano de avaliação cega (inclui a chave)
  python3 -m protocol.cli validate FILE.csv [--fallback]     valida o CSV consolidado
  python3 -m protocol.cli profile FILE.csv                   perfis descritivos de tipo de erro e de pontos de atenção (P1, P2, Q06)
  python3 -m protocol.cli reeval FILE.csv                    valida a reavaliação (>= 24 h entre passagens) e resume distribuição e concordância por critério
  python3 -m protocol.cli freeze --release-ref F --confirm-oracles-released   CONGELA (não executar antes da liberação)
  python3 -m protocol.cli verify-freeze                      confere os arquivos contra FREEZE.json
"""

import argparse
import json
import sys
from pathlib import Path

from . import freeze as freeze_mod
from . import descriptive, manifest, records

PROTOCOL_DIR = Path(__file__).resolve().parent


def main(argv=None):
    p = argparse.ArgumentParser(prog="protocol")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("manifest")
    s.add_argument("--seed", type=int, default=manifest.SEED)
    s.add_argument("--out")
    sub.add_parser("fallback")
    s = sub.add_parser("blind")
    s.add_argument("--seed", type=int, default=manifest.SEED)
    s.add_argument("--completed")
    s = sub.add_parser("validate")
    s.add_argument("file")
    s.add_argument("--fallback", action="store_true")
    s = sub.add_parser("profile")
    s.add_argument("file")
    s = sub.add_parser("reeval")
    s.add_argument("file")
    s = sub.add_parser("freeze")
    s.add_argument("--release-ref")
    s.add_argument("--confirm-oracles-released", action="store_true")
    s.add_argument("--version", default="v1.0.0")
    s.add_argument("--dry-run", action="store_true", help="só verifica precondições; não calcula hashes")
    sub.add_parser("verify-freeze")
    args = p.parse_args(argv)

    if args.cmd == "manifest":
        text = manifest.dumps(manifest.build_document(args.seed))
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
    elif args.cmd == "fallback":
        for r in manifest.fallback(manifest.generate()):
            print(r["run_id"], r["task_id"], r["condition"], r["replicate"])
    elif args.cmd == "blind":
        eligible = set(args.completed.split(",")) if args.completed else None
        print(json.dumps(manifest.blind_plan(manifest.generate(args.seed), args.seed, eligible=eligible),
                         indent=2, ensure_ascii=False))
    elif args.cmd == "validate":
        recs = records.read_csv(Path(args.file).read_text(encoding="utf-8"))
        errs = records.validate_dataset(recs, manifest.generate(), fallback=args.fallback)
        print("\n".join(errs) if errs else f"OK: {len(recs)} registros válidos")
        return 1 if errs else 0
    elif args.cmd == "profile":
        recs = records.read_csv(Path(args.file).read_text(encoding="utf-8"))
        errs = [e for r in recs for e in records.validate_record(r)]
        if errs:
            print("\n".join(errs))
            return 1
        print(json.dumps({"tipos_de_erro": descriptive.error_type_profile(recs),
                          "alegacoes_divergentes": descriptive.claim_divergence_profile(recs),
                          "pontos_de_atencao": descriptive.review_summary(recs),
                          "pontos_de_atencao_do_artefato": descriptive.attention_summary(recs),
                          "diferenca_pontos_do_artefato": descriptive.attention_difference(recs)},
                         indent=2, ensure_ascii=False))
    elif args.cmd == "reeval":
        rows = records.read_reevaluation_csv(Path(args.file).read_text(encoding="utf-8"))
        errs = records.validate_reevaluation(rows, manifest.generate())
        if errs:
            print("\n".join(errs))
            return 1
        print(json.dumps(descriptive.reevaluation_summary(rows), indent=2, ensure_ascii=False))
    elif args.cmd == "freeze":
        problems = freeze_mod.check_preconditions(PROTOCOL_DIR, args.release_ref, args.confirm_oracles_released)
        if args.dry_run:
            print("\n".join(problems) if problems else "precondições satisfeitas")
            return 1 if problems else 0
        from harness import workspace
        try:
            doc = freeze_mod.freeze(PROTOCOL_DIR, args.release_ref, args.confirm_oracles_released,
                                    workspace.baseline_hash, version=args.version)
        except freeze_mod.FreezeError as exc:
            print(f"RECUSADO: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(doc, indent=2, ensure_ascii=False))
    elif args.cmd == "verify-freeze":
        if not (PROTOCOL_DIR / "FREEZE.json").is_file():
            print("não congelado (FREEZE.json ausente)")
            return 1
        diffs = freeze_mod.verify_freeze(PROTOCOL_DIR)
        print("\n".join(diffs) if diffs else "íntegro")
        return 1 if diffs else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
