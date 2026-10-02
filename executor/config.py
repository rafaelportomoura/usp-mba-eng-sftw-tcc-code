"""Parâmetros do executor, lidos de um execution_config.json explícito.

Modelo e esforço de raciocínio NUNCA vêm do ~/.codex/config.toml: são obrigatórios aqui
(valores escolhidos pelo autor em Q11: gpt-5.5 e medium, em author_choices do template) e ausentes/nulos/vazios/'nao_exposto' recusam a execução.
"""

import json
from dataclasses import dataclass
from pathlib import Path

PROTOCOL_TIMEOUT_S = 720


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ExecParams:
    model: str
    reasoning_effort: str
    timeout_s: float
    codex_version_expected: str | None  # ex.: "0.154.0"; se informado, divergência recusa a execução
    config_path: str | None = None


def _get(cfg, dotted):
    cur = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _required_str(cfg, dotted):
    value = _get(cfg, dotted)
    if not isinstance(value, str) or not value.strip() or value.strip().lower() == "nao_exposto":
        raise ConfigError(f"parâmetro obrigatório ausente, nulo ou vazio em execution_config: {dotted} "
                          "(modelo e esforço escolhidos em Q11 devem ser copiados de author_choices; não são herdados do config do usuário)")
    return value.strip()


def load(config_path):
    path = Path(config_path)
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConfigError(f"não foi possível ler {path}: {exc}") from exc
    model = _required_str(cfg, "model.name")
    effort = _required_str(cfg, "generation_parameters.reasoning_effort")
    timeout = _get(cfg, "execution.timeout_s")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ConfigError("execution.timeout_s deve ser número positivo")
    version = _get(cfg, "agent.codex_version")
    if isinstance(version, str) and version.strip() and version.strip().lower() != "nao_exposto":
        version = version.strip()
    else:
        version = None
    return ExecParams(model=model, reasoning_effort=effort, timeout_s=float(timeout),
                      codex_version_expected=version, config_path=str(path))
