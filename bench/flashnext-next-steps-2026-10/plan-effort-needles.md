# Flash-Next: effort no fim do prompt, `medium` fora do código e needles a 256K — runbook

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rodar os itens 3–5 das recomendações de 2026-10-16: P1 (instrução de effort no fim do prompt, braço `w1t`), `medium` em tarefas que não são de código no `w1`, e P3 (needles a 256K, `w1` × `n2`). Cada task termina com uma decisão escrita em `results/`.

**Architecture:** Continua a campanha [plan.md](plan.md) com os mesmos scripts (`run-arm.sh`, `run-seq.sh`, `run-battery.sh`, `agent_probes.py`, `decide.py`, `summarize_ab.py`). O `w1t` é o pack Swift 1.5 num diretório overlay de hardlinks, com só o `chat_template.jinja` trocado. O template alterado fica em `fixes/qwen3.8-flash-next/`.

**Tech Stack:** bash 3.2 (rig), Python 3 (stdlib), jinja2 só nos testes (`uv run --with jinja2`), mlx-serve 26.10.1.

**Spec:** [plan.md](plan.md), seção "Tasks possíveis" (P1, P3), e a resposta de 2026-10-16 com os próximos passos (itens 3–5).

## Global Constraints

- Tudo de [plan.md](plan.md) "Global Constraints" vale aqui: rig, runtime 26.10.1, sampling do vendor, protocolo térmico, gates de velocidade, idioma, `Testes: uv run --no-project --with pytest python -m pytest <caminho> -q`.
- Commits: `bench(flashnext): ...`, última linha `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Nunca `git commit -a`; stage só os caminhos da task.
- Branch: `bench/flashnext-effort-2026-10`, criada a partir de `bench/flashnext-next-steps-2026-10`.
- O submódulo `tools/local-llm-bench-m4-32gb` fica em `2403125` (avaliador de LCB corrigido). No rig: `git submodule update tools/local-llm-bench-m4-32gb` antes da primeira bateria. LCB novo já sai correto; o controle `w1` do 3d usa o LCB reavaliado de `results/e3d-lcb-regrade.md`.
- Margens G1 (`summarize_ab.py`): humaneval 3, gpqa 3, livecodebench 3, jdhodges 2, veerman 1, if 2.
- O driver diário (porta 11234) fica parado durante as tasks e volta no fim da Task 14.
- A ordem de execução é 11 (só até o gate do 3e) → 12 → 13 → 11 (bateria de qualidade) → 14. O 3e decide se a bateria longa do `w1t` roda.

## Review Focus

1. **O mlx-serve lê o template de outro lugar.** Se o `tokenizer_config.json` tiver `chat_template`, o overlay precisa trocar os dois. O `tokenizer_config.json` do Swift `13839b7` não tem a chave (conferido em 2026-10-16); o `make-overlay.sh` falha se a chave aparecer. O smoke do Step 5 da Task 11 confirma o template pelo hit da troca.
2. **Overlay que edita o pack original.** Escrever num hardlink muda o arquivo do pack `w1`. O `make-overlay.sh` remove o link do template antes de copiar o novo arquivo. Teste: `test_overlay_does_not_touch_the_source_template`.
3. **`medium` renderiza diferente nos dois templates.** O template oficial não escreve instrução no `medium`; o `w1t` também não. Os dois renders têm de ser iguais no `medium`, senão a Task 12 não vale para o `w1t`. Teste: `test_medium_render_is_identical`.
4. **Ruído de 1 rodada.** O Veerman tem 12 casos e já virou 3 casos entre rodadas. Toda decisão de qualidade usa 2 rodadas e a soma das duas.
5. **Truncado contado como erro a 256K.** A Task 13 usa `--max-tokens 8192` nos dois braços, e o `decide.py` separa `trunc` de `erro`.

---

## Mapa de arquivos

| Arquivo | Ação | Responsabilidade |
| --- | --- | --- |
| `fixes/qwen3.8-flash-next/swift15-effort-tail.jinja` | Create | template do Swift 1.5 com a instrução de effort num bloco `system` logo antes do `<|im_start|>assistant` final |
| `fixes/qwen3.8-flash-next/README.md` | Create | o que o template muda e onde foi medido |
| `bench/flashnext-next-steps-2026-10/scripts/make-overlay.sh` | Create | overlay de hardlinks do pack com um template trocado |
| `bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh` | Modify | braço `w1t` |
| `bench/flashnext-next-steps-2026-10/tests/test_effort_tail.py` | Create | testes do template e do overlay |
| `bench/flashnext-next-steps-2026-10/tests/test_arms.py` | Modify | teste do braço `w1t` |
| `results/etapa11-effort-tail.md`, `results/etapa12-medium.md`, `results/etapa13-needles256k.md` | Create | decisões |
| `results/summary.md`, `docs/models/qwen3.8-flash-next.md`, `bench/qwen38-flash-next/references.md` | Modify (Task 14) | resultados |

---

### Task 11: P1 — instrução de effort no fim do prompt (`w1t`)

**Files:** os quatro primeiros do mapa, mais `results/agent/3e-w1t.jsonl`, `results/e11/t1/<label>/*.jsonl`, `results/etapa11-effort-tail.md`.

**Interfaces:**
- Produces: braço `w1t` no `run-candidate.sh` (`MODEL_DIR` = `$MODEL_ROOT/Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0-efftail`, `REV=v26.10.1-efftail`, resto igual ao `w1`); `make-overlay.sh <src_dir> <dst_dir> <template>`.

**Template.** Copie o `chat_template.jinja` do Swift `13839b7` (MD5 `519239a4908bb1f805bbce5fa8c8a242`) e mude só isto:
- O bloco `system` de cima não recebe mais `reasoning_instructions` (linhas 59–61, 80–85 do original): o system prompt e as tools saem iguais aos do `medium`.
- No `add_generation_prompt`, antes de `'<|im_start|>assistant\n'`, se `reasoning_instructions` não for vazio, escreva `'<|im_start|>system\n' + reasoning_instructions + '<|im_end|>\n'`.

Assim o prefixo de uma conversa não depende do effort. Só o bloco final muda, e o turno seguinte o descarta.

**Regras de decisão:**
- Gate do 3e (Step 6): hit da troca ≥ 0.9 em `medium` e em `low`, nas 2 rodadas. Se falhar, a Task 11 para: escreva o `etapa11` com o 3e e o veredito "não adotar".
- Obediência (`scripts/effort_obedience.py`, revisada em 2026-10-16): por questão do GPQA e do LCB, média sobre as 2 rodadas de log(`reasoning_tokens`). O deslocamento `w1t`/`w1` no mesmo effort tem IC de 90% por bootstrap sobre as questões. Passa se o IC ficar dentro de ×0.80–×1.25 em `xhigh` e em `low`. O `medium` renderiza igual nos dois templates e serve de teste A/A. A regra antiga (medianas dentro de ±20%) não separava sinal de ruído: o mesmo `w1` em `xhigh` deu mediana de 3129 e 5027 chars no GPQA entre rodadas. Calibração com os dados do 3d: no `w1`, `low` gasta ×0.45 (0.38–0.53) do `xhigh` e `medium` ×0.62; a rodada 1 contra a rodada 2 do `w1` dá IC de ±10–13%. Um `low` ignorado apareceria como ×1.38, e um `xhigh` ignorado como ×0.62.
- Acerto: GPQA e LCB do `w1t` dentro da margem G1 do `w1` no mesmo effort (soma das 2 rodadas, margem × 2), nos três efforts.
- Tool-calling: 3f do `w1t` em `xhigh` (jdhodges + Veerman, 1 rodada) dentro da margem G1 do `w1` r1.
- Adoção: as quatro regras valem → o launcher diário ganha o perfil opcional `FLASHNEXT_TEMPLATE=efftail` (o default não muda sem o OK do usuário). Senão, o harness continua fixando o effort por sessão.

- [ ] **Step 1: Branch**

```bash
git switch -c bench/flashnext-effort-2026-10
```

- [ ] **Step 2: Testes que falham**

Em `tests/test_effort_tail.py` (pule o arquivo com `pytest.importorskip("jinja2")`), renderize com `jinja2.Environment(...).from_string` o template oficial (de `tests/fixtures/swift15-chat_template.jinja`, cópia do original) e o `swift15-effort-tail.jinja`, com `raise_exception` definido e `add_generation_prompt=True`:
- `test_medium_render_is_identical`: mesmas mensagens (system + user, com e sem tools), effort `medium` → os dois renders iguais.
- `test_effort_block_is_the_last_block`: effort `xhigh` e `low` no `w1t` → o render termina com `'<|im_start|>system\n' + instrução + '<|im_end|>\n<|im_start|>assistant\n<think>\n'`, e o início do system prompt não tem a instrução.
- `test_prefix_does_not_depend_on_effort`: renders `xhigh`, `medium` e `low` do `w1t` são iguais até o início do bloco final.
- `test_overlay_does_not_touch_the_source_template`: `make-overlay.sh` num `tmp_path` com 2 arquivos falsos → no destino, os pesos têm o mesmo inode da origem; o template tem inode diferente e o conteúdo novo; o template da origem não muda.
- `test_overlay_refuses_tokenizer_chat_template`: origem com `tokenizer_config.json` contendo `chat_template` → exit ≠ 0.

Em `tests/test_arms.py`: `test_w1t_uses_the_efftail_overlay` (o `--print` do braço `w1t` mostra o `MODEL_DIR` terminando em `-efftail` e `REV=v26.10.1-efftail`), no estilo dos testes de braço existentes.

Run: `uv run --no-project --with pytest --with jinja2 python -m pytest bench/flashnext-next-steps-2026-10/tests -q`
Expected: os 6 testes novos falham; os antigos passam.

- [ ] **Step 3: Template, `make-overlay.sh`, braço `w1t`, README**

`make-overlay.sh <src_dir> <dst_dir> <template>`: recusa se `dst_dir` já existir com template diferente; `ln` de cada arquivo regular de `src_dir` em `dst_dir`; `rm` do `chat_template.jinja` do destino e `cp` do template novo; exit 65 se `tokenizer_config.json` tiver `chat_template`. Grava `dst_dir/OVERLAY.txt` com a origem e o MD5 do template.

Run: o mesmo pytest do Step 2. Expected: tudo passa.

- [ ] **Step 4: Commit**

```bash
git add fixes/qwen3.8-flash-next bench/flashnext-next-steps-2026-10/scripts/make-overlay.sh \
  bench/flashnext-next-steps-2026-10/tests/test_effort_tail.py bench/flashnext-next-steps-2026-10/tests/test_arms.py \
  bench/flashnext-next-steps-2026-10/tests/fixtures/swift15-chat_template.jinja \
  bench/qwen38-flashnext-daily-driver-2026-09/scripts/run-candidate.sh bench/flashnext-next-steps-2026-10/plan-effort-needles.md
git commit -m "bench(flashnext): w1t arm - Swift 1.5 with the effort instruction at the end of the prompt"
git push -u origin bench/flashnext-effort-2026-10
```

- [ ] **Step 5: Rig — sync, overlay, smoke a 32K**

```bash
cd ~/LocalProjects/local-llms && git fetch -q && git switch bench/flashnext-effort-2026-10 && git pull --ff-only
git submodule update tools/local-llm-bench-m4-32gb
C=$PWD/bench/flashnext-next-steps-2026-10; R=~/.cache/local-llms/qwen3.8-prefix-cache
S=$R/Dankpaws-Swift1.5-Qwen3.8-Flash-Next-MLX-4.7bpw-13839b7191e0973ff9fea58232267c395b76c6c0
bash $C/scripts/make-overlay.sh $S $S-efftail fixes/qwen3.8-flash-next/swift15-effort-tail.jinja
P="$(lsof -nP -tiTCP:11234 -sTCP:LISTEN || true)"; [ -n "$P" ] && kill $P; sleep 10
bash $C/scripts/idle-gate.sh --minutes 0
bash $C/scripts/run-arm.sh w1t 32768 --tag e11smoke --exec \
  "python3 $C/scripts/agent_probes.py effortswitch --base-url \"\$BASE_URL\" --model \"\$MODEL_ID\" --arm w1t --context 32768 --switch-to low --rounds 1 --output $C/logs/3e-w1t-smoke.jsonl"
python3 $C/scripts/agent_probes.py summary $C/logs/3e-w1t-smoke.jsonl
```

Expected: `switch ... hit` ≥ 0.9. Hit 0.00 = o servidor não leu o template novo: confira o `OVERLAY.txt` e o boot log antes de seguir.

- [ ] **Step 6: 3e a 128K no `w1t` (gate)**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
bash $C/scripts/idle-gate.sh
P="python3 $C/scripts/agent_probes.py"; A="--base-url \"\$BASE_URL\" --model \"\$MODEL_ID\" --arm w1t"
caffeinate -i bash $C/scripts/run-arm.sh w1t 131072 --tag e11 --exec \
  "rc=0; $P effortswitch $A --context 131072 --switch-to medium --rounds 2 --output $C/results/agent/3e-w1t.jsonl || rc=\$?;
   $P effortswitch $A --context 131072 --switch-to low --rounds 2 --output $C/results/agent/3e-w1t.jsonl || rc=\$?; exit \$rc"
python3 $C/scripts/agent_probes.py summary $C/results/agent/3e-w1t.jsonl $C/results/agent/3e-w1.jsonl
```

Expected: 16 linhas. Aplique o gate do 3e. Se falhar, pule para o Step 9 só com o 3e.

- [ ] **Step 7: 3f `xhigh` e GPQA + LCB nos três efforts, 2 rodadas** (roda depois das Tasks 12 e 13)

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
bash $C/scripts/idle-gate.sh --minutes 2
caffeinate -i bash $C/scripts/run-battery.sh w1t e11 --suites "jdhodges veerman" --effort xhigh --label w1t-r1
for r in r1 r2; do for e in low medium xhigh; do
  bash $C/scripts/idle-gate.sh --minutes 2
  caffeinate -i bash $C/scripts/run-battery.sh w1t e11 --suites "gpqa livecodebench" --effort $e --label w1t-$e-$r
  echo "exit[e11 $e $r]=$?"
done; done
```

Expected: `results/e11/t1/w1t-<effort>-<rodada>/{gpqa,livecodebench}.jsonl` com 50 linhas cada, e `results/e11/t1/w1t-r1/{jdhodges,veerman}.jsonl`.

- [ ] **Step 8: Resumos contra o `w1`**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10; S=bench/swift15-flashnext-2026-10/scripts/summarize_ab.py
mkdir -p $C/results/e11/t1x
for r in r1 r2; do for e in low medium xhigh; do
  ln -sfn ../../e3d/t1/w1-$e-$r $C/results/e11/t1x/w1-$e-$r; ln -sfn ../t1/w1t-$e-$r $C/results/e11/t1x/w1t-$e-$r
  python3 $S --ab-dir $C/results/e11/t1x --base w1-$e-$r --cand w1t-$e-$r --out $C/results/e11-summary-$e-$r.md
done; done
ln -sfn ../../e3f/t1/w1-r1 $C/results/e11/t1x/w1-r1; ln -sfn ../t1/w1t-r1 $C/results/e11/t1x/w1t-r1
python3 $S --ab-dir $C/results/e11/t1x --base w1-r1 --cand w1t-r1 --out $C/results/e11-summary-3f.md
python3 $C/scripts/lcb_regrade.py $C/results/e3d/t1/w1-*/livecodebench.jsonl $C/results/e11/t1/w1t-*/livecodebench.jsonl
python3 $C/scripts/effort_obedience.py --base-root $C/results/e3d/t1 --cand-root $C/results/e11/t1 \
  --json $C/results/e11-obedience.json | tee $C/results/e11-obedience.md
```

Expected: 7 resumos. O LCB do `w1` vem da reavaliação; o do `w1t` já sai correto (o `lcb_regrade` deve dar o mesmo número que o bruto nos arquivos `w1t`).

- [ ] **Step 9: `results/etapa11-effort-tail.md` e commit**

Título e data; tabela do 3e (`w1` × `w1t`: TTFT e hit da troca); tabela por effort com GPQA, LCB reavaliado, chars de reasoning medianos e as razões `low/xhigh` e `medium/xhigh`; 3f; `## Veredito` com uma linha por regra; `## Leitura`. Se adotar, acrescente o perfil `FLASHNEXT_TEMPLATE=efftail` em `tools/scripts/serve-flashnext-daily-driver.sh` (troca o `MODEL` pelo diretório `-efftail`) e um teste no estilo dos testes do launcher.

```bash
git add bench/flashnext-next-steps-2026-10/results/etapa11-effort-tail.md bench/flashnext-next-steps-2026-10/results/e11* \
  bench/flashnext-next-steps-2026-10/results/agent/3e-w1t.jsonl
git commit -m "bench(flashnext): Task 11 - effort instruction at the end of the prompt (w1t)"
```

---

### Task 12: `medium` em tarefas que não são de código (`w1`)

**Origem.** No 3d, `medium` gasta ~27% do tempo do `xhigh`, passa no GPQA (−2 e 0) e no 3a (40/40), e perde só no LCB (−6 e −7). O `medium` renderiza igual no template oficial e no `w1t`, então o resultado vale para os dois.

**Braço.** `w1`, 131072 (3c: 262144).

**Medidas:** 3f (jdhodges 40 + Veerman 12) em `medium`, 2 rodadas, contra o 3f `xhigh` de `results/e3f/t1/w1-r{1,2}`; IFEval (`if`) em `medium` e `xhigh`, 2 rodadas cada; 3c (sessão até 200K) em `medium`, 2 rodadas.

**Regra.** O harness passa a usar `medium` em chat e em tool-calling sem código se valer tudo: jdhodges, Veerman e IF dentro da margem G1 do `xhigh` (soma das 2 rodadas, margem × 2); 3c sem `char_run`, sem `degenerate`, com vazio + código errado ≤ o do `xhigh` + 1. Código continua em `xhigh`. Com o template oficial, essa troca é por sessão (o 3e zera o cache); com o `w1t` adotado, ela pode ser por turno.

- [ ] **Step 1: 3f e IF**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
for r in r1 r2; do
  bash $C/scripts/idle-gate.sh --minutes 2
  caffeinate -i bash $C/scripts/run-battery.sh w1 e12 --suites "jdhodges veerman if" --effort medium --label w1-medium-$r
  bash $C/scripts/idle-gate.sh --minutes 2
  caffeinate -i bash $C/scripts/run-battery.sh w1 e12 --suites "if" --effort xhigh --label w1-xhigh-$r
done
```

Expected: `results/e12/t1/w1-medium-r{1,2}/{jdhodges,veerman,if}.jsonl` e `results/e12/t1/w1-xhigh-r{1,2}/if.jsonl`.

- [ ] **Step 2: 3c em `medium`**

`agent_probes.py longsession` aceita `--reasoning-effort`? Se não aceitar, acrescente a flag (default `xhigh`) com um teste em `tests/test_scripts.py` antes de rodar, no mesmo commit da Task 12.

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
bash $C/scripts/idle-gate.sh
caffeinate -i bash $C/scripts/run-arm.sh w1 262144 --tag e12c --exec \
  "python3 $C/scripts/agent_probes.py longsession --base-url \"\$BASE_URL\" --model \"\$MODEL_ID\" --arm w1 --rounds 2 --targets 150000,200000 --reasoning-effort medium --output $C/results/agent/3c-w1-medium.jsonl"
```

Expected: 2 sessões com `prompt_tokens` ≥ 200000.

- [ ] **Step 3: Resumos, `results/etapa12-medium.md` e commit**

Junte, num `results/e12/t1x/` de symlinks, `w1-xhigh-r{1,2}` (3f de `e3f/t1` e IF de `e12/t1`) e `w1-medium-r{1,2}`; rode `summarize_ab.py --base w1-xhigh-$r --cand w1-medium-$r` por rodada; rode `agent_probes.py summary` em `3c-w1.jsonl` e `3c-w1-medium.jsonl`. Escreva o `etapa12-medium.md` com as tabelas, o tempo total por suíte, `## Veredito` e `## Leitura`. Commit `bench(flashnext): Task 12 - medium effort on non-code tasks`.

---

### Task 13: P3 — needles a 256K, `w1` × `n2`

**Braços.** `w1` e `n2` a 262144, KV sem quantização, 3 reps cada, alternados (`w1 n2 n2 w1 w1 n2`, 1 rep por subida), `QWEN38_PROBE_MAX_TOKENS=8192` nos dois.

**Regra.** O `n2` acerta 13/13 e o `w1` erra de novo → o card registra que o Swift perde retrieval a 256K, e o perfil `256k` não deve usar o Swift. Os dois erram → o limite é do contexto, não do pack. O `w1` acerta 13/13 → os erros da Task 2 eram variância; registre a taxa somada (Task 2 + Task 13). Classifique cada erro pelo `content_head`: valor de needle errado, needle ausente ou recusa.

- [ ] **Step 1: Fila**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
bash $C/scripts/idle-gate.sh
export QWEN38_PROBE_MAX_TOKENS=8192
caffeinate -i bash $C/scripts/run-seq.sh w1:262144:1:e13 n2:262144:1:e13 n2:262144:1:e13 w1:262144:1:e13 w1:262144:1:e13 n2:262144:1:e13 \
  2>&1 | tee $C/logs/etapa13.log
```

Expected: `results/{w1,n2}-262144-t1.0-e13.jsonl` com os registros de 3 reps cada.

- [ ] **Step 2: `results/etapa13-needles256k.md` e commit**

```bash
cd ~/LocalProjects/local-llms && C=$PWD/bench/flashnext-next-steps-2026-10
{ echo "# Etapa 13 — needles a 256K, Swift 1.5 × iQ ($(date +%F), mlx-serve 26.10.1, max_tokens 8192)"; echo
  python3 $C/scripts/decide.py --glob "w1-262144-t1.0-e13.jsonl" --glob "n2-262144-t1.0-e13.jsonl" --title "256K, 3 reps alternados"
} > $C/results/etapa13-needles256k.md
python3 - <<'EOF'
import json, glob
for f in sorted(glob.glob("bench/flashnext-next-steps-2026-10/results/*-262144-t1.0-e13.jsonl")):
    for l in open(f):
        r = json.loads(l)
        if r.get("content_head") is not None:
            print(f.split("/")[-1], r.get("scenario"), r.get("rep"), repr(r["content_head"][:200]))
EOF
```

Acrescente a lista de erros classificados, `## Veredito` e `## Leitura` (com a taxa somada da Task 2 + Task 13 no `w1`). Commit `bench(flashnext): Task 13 - needles at 256K, Swift 1.5 vs iQ`.

---

### Task 15: o mesmo template no iQ (`n2t`), pedida pelo usuário em 2026-10-16

**Origem.** O pack iQ `dafff5c` usa o mesmo template oficial (MD5 `519239a4…`) e é o driver secundário. O Swift é um fine-tune que pensa menos; o iQ é o Flash-Next base quantizado. A obediência a uma instrução fora do lugar de treino pode ser diferente no modelo base.

**Braços.** `n2t` = `n2` com o overlay `-efftail`. O iQ também guarda o template na chave `chat_template` do `tokenizer_config.json` (igual ao `.jinja`); o `make-overlay.sh` troca as duas cópias.

**Medidas.**
- 3e a 128K no `n2t` (`medium` e `low`, 2 rodadas). Mesmo gate da Task 11 (hit ≥ 0.9). Se falhar, a Task 15 para.
- GPQA + LCB, 1 rodada: `n2t` em `xhigh`, `medium`, `low`; `n2` em `medium` e `low`. O controle `n2` em `xhigh` vem da campanha Swift (`bench/swift15-flashnext-2026-10/results/ab/t1/n2`, 2026-10-11, mesmo runtime e sampling), por symlink em `results/e15/t1x/n2-xhigh-r1`.

**Regra.** `effort_obedience.py --rounds r1` passa; GPQA e LCB do `n2t` dentro da margem G1 do `n2` (3) em cada effort. LCB sempre no avaliador corrigido.

- [ ] **Step 1:** rodar a fila (script do rig `task15.sh`: overlay, 3e, gate, bateria), depois da Task 11.
- [ ] **Step 2:** `results/etapa15-iq-effort-tail.md` com o 3e, a obediência e o acerto; commit `bench(flashnext): Task 15 - effort-tail template on the iQ pack`.

---

### Task 14: Resumo, docs e driver diário

- [ ] **Step 1:** Em `results/summary.md`, acrescente as linhas 11, 12 e 13 à tabela de decisões e as notas por task. Atualize `docs/models/qwen3.8-flash-next.md` e `bench/qwen38-flash-next/references.md` com as decisões (effort por sessão ou por turno, `medium` fora do código, retrieval a 256K).
- [ ] **Step 2:** No rig, suba o driver diário: `nohup bash tools/scripts/serve-flashnext-daily-driver.sh daily > /tmp/flashnext-daily-driver.log 2>&1 &`. Confira a porta 11234.
- [ ] **Step 3:** Ledger (`.superpowers/sdd/plan/progress.md`), commit `bench(flashnext): Tasks 11-13 summary and docs`, push.
