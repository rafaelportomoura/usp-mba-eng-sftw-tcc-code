"""Enumeração ESTÁTICA dos testes esperados de uma suíte (denominador estável).

Lê os arquivos com ``ast`` sem importar nada: o total não depende do código do agente
(erro de sintaxe, crash, timeout).
"""

import ast
from pathlib import Path


def expected_tests(directory):
    """Retorna a lista ordenada de 'Classe.test_metodo' definidos em ``directory/*.py``."""
    names = []
    for path in sorted(Path(directory).glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and any(_is_testcase(b) for b in node.bases):
                names += [f"{node.name}.{f.name}" for f in node.body
                          if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name.startswith("test")]
    return sorted(names)


def _is_testcase(base):
    if isinstance(base, ast.Attribute):
        return base.attr == "TestCase"
    return isinstance(base, ast.Name) and base.id == "TestCase"
