"""Executa uma suíte unittest e grava o resultado em um ARQUIVO JSON.

Uso: python unittest_json.py START_DIR TOP_LEVEL_DIR RESULT_PATH NONCE
(executado com cwd no diretório alvo).

O resultado NÃO trafega por stdout: o código avaliado pode imprimir qualquer coisa. O arquivo é
escrito de forma atômica ao final e o processo encerra com ``os._exit`` para impedir que handlers
``atexit`` do código avaliado reescrevam o canal. Testes pulados, falhas esperadas e sucessos
inesperados NÃO contam como aprovados.
"""

import json
import os
import sys
import unittest


class Collector(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.passed = []
        self.failed = []
        self.not_run = []   # pulados / expectedFailure / unexpectedSuccess
        self.load_errors = []

    @staticmethod
    def _name(test):
        parts = test.id().split(".")
        return ".".join(parts[-2:])

    def _fail(self, test):
        if test.id().startswith("unittest.loader."):
            self.load_errors.append(test.id())
        self.failed.append(self._name(test))

    def addSuccess(self, test):
        self.passed.append(self._name(test))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._fail(test)

    def addError(self, test, err):
        super().addError(test, err)
        self._fail(test)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.not_run.append(self._name(test))

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.not_run.append(self._name(test))

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.not_run.append(self._name(test))

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.failed.append(self._name(test))


def collect(start, top):
    result = Collector()
    try:
        suite = unittest.defaultTestLoader.discover(start, top_level_dir=top)
        suite.run(result)
    except BaseException as exc:  # noqa: BLE001 - falha de coleta vira dado, nunca crash
        return {"fatal": f"{type(exc).__name__}: {exc}", "passed_tests": [], "failed_tests": [],
                "not_run_tests": [], "load_errors": [], "details": []}
    details = [t.id() + "\n" + tb[-2000:] for t, tb in result.failures + result.errors]
    return {
        "fatal": None,
        "passed_tests": sorted(set(result.passed) - set(result.failed) - set(result.not_run)),
        "failed_tests": sorted(set(result.failed)),
        "not_run_tests": sorted(set(result.not_run)),
        "load_errors": sorted(set(result.load_errors)),
        "details": details[:50],
    }


def main(start, top, result_path, nonce):
    data = collect(start, top)
    data["nonce"] = nonce
    tmp = result_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, result_path)
    os._exit(0)


if __name__ == "__main__":
    main(*sys.argv[1:5])
