"""Executor do Codex (TCC-040/050): roda `codex exec` por execução, isolado e com captura completa.

Não executa a avaliação por conta própria: delega a `harness.cli.evaluate`. Nunca grava credenciais.
"""
