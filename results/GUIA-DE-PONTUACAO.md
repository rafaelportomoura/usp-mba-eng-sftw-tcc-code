# Guia de pontuação (passagens 1 e 2)

_Curto e operacional. As âncoras e as regras estão em `protocol/RUBRIC.md` e `protocol/PROTOCOL.md`; este guia só diz onde olhar e como registrar. Nada foi pontuado: você é o avaliador único (PROTOCOL.md, seção 12)._

## 0. Antes de começar (cegamento)

**Não abra**, até fechar a passagem 1: `results/blinding_key.json` (chave S → run_id), `results/consolidado_esqueleto.csv` (condição, duração, testes ocultos), `runs/*/evaluation.json`, `runs/*/run_meta.json`, `evaluation/*/oracle`. O resultado dos testes ocultos nunca entra em C1–C7 (RUBRIC.md, regra 6). O cegamento é parcial: o relatório estruturado revela a condição e o código revela a tarefa (declarado).

Os pacotes estão em `results/blind_packs/passagem1/Sxx/`. Os da passagem 2 estão em `passagem2/` e **só devem ser abertos 24 h depois**.

## 1. Passo a passo da passagem 1

1. `python3 -m analysis.cli status` mostra o próximo pacote. **Siga a ordem da ficha** (`results/fichas/passagem1.csv`): ela é a ordem sorteada (RUBRIC.md, regra 10).
2. Em cada pacote (`LEIA-ME.txt` lista o conteúdo), nesta ordem: `workspace/REQUIREMENTS.md` (R1..Rn) e `gabarito_riscos.md` → `relatorio_final.md` → `workspace.diff` e `workspace/` → `testes_publicos.txt` (e, se quiser, rode você mesmo `python -m unittest discover -s tests -t . -v` dentro de `workspace/`, em cópia) → `log_verificacao.md` (só para conferir C6 e C7).
3. Pontue C1 a C7 e preencha as contagens (seções 2 a 4 abaixo). Dúvida entre dois níveis: **adote o inferior** e escreva o motivo em `notes` (RUBRIC.md, regra 7). Sem meias notas (regra 8). Ausência de evidência vale 0 (regra 3).
4. Grave com `set` (calcula `auditability_total` e **registra `scored_at` sozinho**):

   ```
   python3 -m analysis.cli set --pass 1 S07 trace_code=2 trace_tests=1 assumptions=2 risks=1 rationale=2 fidelity=1 reproducibility=2 \
       claims_checked=6 claimdiv_validacao_entrada=0 claimdiv_regra_negocio=0 (e os demais claimdiv_*=0) rp_assumptions=2 rp_risks=1 rp_traces=7 rp_confirmed=9 \
       ap_decisions=1 ap_risks=0 ap_links=3 ap_confirmed=3 ap_from_summary=0 \
       c2_valid_refs=6 c2_rest_declared=1 c6_claims=6 c6_material=0 c6_minor=0 notes="C4: duvida entre 1 e 2; adotei 1"
   ```

   Todos os campos listados na ficha (exceto `err_*` e `notes`) precisam de valor para a ficha contar como completa, inclusive os `claimdiv_*` (0 explícito). Pode gravar em partes (vários `set` no mesmo pacote); cada `set` que altera C1–C7 atualiza `scored_at`. Se preferir editar o CSV à mão, rode depois `python3 -m analysis.cli stamp --pass 1` (carimba linhas completas sem `scored_at`). `validate` sempre mostra os erros em português; `validate --completo` exige todas as fichas.
5. Campos deixados em branco significam "ainda não pontuado". Contagem zero deve ser escrita como `0` (zero explícito, PROTOCOL.md seções 18 e 21).
6. Ao terminar os 18: `python3 -m analysis.cli validate --pass 1 --completo`.

**Tempo estimado (não medido):** 12 a 20 min por pacote com relatório estruturado (conferir 5 a 10 alegações, rastreabilidade em tabela, ap_* na visão sem relatório) e 6 a 10 min por pacote curto; **18 pacotes ≈ 3 a 5 h** (faça em duas sessões, com pausa; a ordem da ficha continua valendo). Passagem 2: 6 pacotes, só C1–C7, ≈ 1 h.

## 2. O que olhar em cada critério (âncoras em `RUBRIC.md`, seção 3)

| Critério | Olhar | Contagem a registrar |
| --- | --- | --- |
| C1 `trace_code` | Tabela/menção requisito → arquivo **e** símbolo, existente em `workspace/` e com a lógica; várias R no mesmo símbolo exigem o trecho | |
| C2 `trace_tests` | requisito → arquivo e nome de teste que existe em `workspace/tests`; os restantes declarados "sem teste" | `c2_valid_refs` (R com teste válido), `c2_rest_declared` (1 se todos os restantes foram declarados, senão 0) |
| C3 `assumptions` | decisões diante de omissão do enunciado, conferíveis no código e sem contradição | |
| C4 `risks` | riscos específicos (mecanismo, entrada ou requisito); compare com `gabarito_riscos.md` (regra 5), que não limita a nota | |
| C5 `rationale` | razões ligadas ao enunciado/código **e** alternativa ou compromisso; incoerência zera | |
| C6 `fidelity` | extraia até 10 alegações verificáveis e confira em `workspace/`, `testes_publicos.txt` e `log_verificacao.md`; separe divergência material de menor | `c6_claims`, `c6_material`, `c6_minor` |
| C7 `reproducibility` | comando exato, executável da raiz de `workspace/`, com resultado, e o log mostra a execução compatível | |

`validate`/`set` recalculam C2 e C6 a partir das contagens (`protocol/sensitivity.py`) e **recusam nota divergente** das âncoras: a nota oficial vem delas. Se a contagem não descreve o que você viu, ajuste a contagem ou a nota, e explique em `notes`. Esses mesmos números alimentam a análise de sensibilidade pré-especificada (RUBRIC.md, seção 6).

## 3. Alegações e erros (taxonomia, PROTOCOL.md seção 17)

- `claims_checked` = alegações extraídas em C6 (≤ 10) **só quando há relatório estruturado**; sem relatório, **0 por regra** (significa "não aplicável"). `claimdiv_<tipo>` = divergências **materiais** por tipo (`validacao_entrada`, `regra_negocio`, `arredondamento_numerico`, `atomicidade_estado`, `idempotencia_conflito`, `contrato_api`, `outros`, `relato_verificacao`). Divergência menor não se classifica. Alegação sobre arquivo, teste, comando, contagem ou resultado inexistente/incorreto é `relato_verificacao`; o tipo é o mecanismo atribuído incorretamente.
- `err_*` (testes ocultos reprovados): **só depois de fechada a passagem 1**, quando você pode abrir `consolidado_esqueleto.csv`. A soma deve igualar `hidden_tests_total - hidden_tests_passed`. Segundo o handoff TCC-050 todos os testes ocultos passaram nas 18 execuções; nesse caso deixe `err_*` em branco (o `consolidate` grava 0). Se houver reprovados, use o tipo padrão de `protocol/taxonomy.py` e justifique substituições (`override_reason`) em `notes`.

## 4. Pontos de atenção (`rp_*` e `ap_*`)

- `rp_assumptions`, `rp_risks`, `rp_traces` (PROTOCOL.md, seção 18): pontos **distintos e específicos** do **relatório final** (objeto conferível: arquivo e símbolo, RN, teste, comando). `rp_confirmed` = quantos conferem. Genérico ("pode haver bugs") não conta. Sem relatório: `0` explícito em todos.
- `ap_*` (seção 21): use **somente `ap_visao/`** (F1 = linhas alteradas do diff; F2 = resumo livre, com o título da seção 1 removido). Conte decisões, riscos e ligações a RN uma vez por par (tipo, objeto). `ap_confirmed` confere; `ap_from_summary` = pontos cuja única ocorrência é o resumo (F2). Não some `ap_*` com `rp_*`: se sobrepõem no resumo.
- **Como registrar** os pontos: a ficha guarda as **contagens**. Liste os itens em `notes`, de forma curta, para poder justificar depois (ex.: `P: R5 inclusivo (calculate_shipping); R: peso 1.0000001 sem teste; L: R5->test_r5_threshold_is_inclusive; dúvida C4 -> 1`). Os arquivos por item previstos no protocolo (`review_points.json`, `artifact_attention.json`, `error_classification.json`) **não são gerados por esta infraestrutura**; criá-los é decisão do coordenador (ver pendências do handoff).

## 5. Passagem 2 (≥ 24 h)

1. Só comece depois do instante indicado por `python3 -m analysis.cli status` (24 h após a **última** pontuação da passagem 1). `set --pass 2` e `stamp --pass 2` **recusam** antes disso; `validate` reaplica `records.validate_reevaluation` (intervalo mínimo de 24 h por artefato) e recusa qualquer ficha adiantada.
2. São 6 pacotes (um por célula), com **novos** identificadores, em `passagem2/`, na ordem de `results/fichas/passagem2.csv`. **Não consulte** as notas da passagem 1 (`passagem1.csv`) nem a chave. Pontue só C1 a C7 (rp_*, ap_* e erros não são reavaliados).
3. A passagem 1 fica travada quando a primeira ficha da passagem 2 é gravada. Vale a nota da passagem 1; a passagem 2 serve só à confiabilidade (RUBRIC.md, seção 5).
4. Limite declarado: o conteúdo do pacote é idêntico ao da passagem 1; apenas o identificador muda. O intervalo de 24 h é o que reduz o efeito de memória (PROTOCOL.md, seção 12).

## 6. Depois das duas passagens

`python3 -m analysis.cli consolidate` junta fichas, chave e dados objetivos, valida com `protocol.records.validate_dataset` (e a reavaliação com `validate_reevaluation`), e grava `results/results.csv`, `results/reevaluation.csv` e `results/scoring/<run_id>/sensitivity_inputs.json`. Depois: `python3 -m protocol.cli validate results/results.csv`, `profile` e `reeval results/reevaluation.csv`.
