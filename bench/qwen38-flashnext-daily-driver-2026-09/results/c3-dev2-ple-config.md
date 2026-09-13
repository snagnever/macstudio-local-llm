# c3 (Jundot oQ4e Flash-Next @ oMLX 0.7.0.dev2) — offload de PLE por modelo

Task 6. Investigacao estatica (grep + import direto dos dois `site-packages`,
sem subir servidor) sobre como a oMLX 0.7.0.dev2 le `qwen4_ple_ssd_offload`
por modelo, e o que mudou em relacao a 0.6.4.

## Resultado principal: o mecanismo NAO mudou entre 0.6.4 e 0.7.0.dev2

Achado central: `omlx/model_settings.py`, `omlx/engine_pool.py` e
`omlx/utils/model_loading.py` sao **byte-identicos** entre as duas arvores
(`~/.local/share/uv/tools/omlx/` = 0.6.4 e
`~/.local/opt/qwen38/omlx-v0.7.0.dev2/`) nos trechos que decidem residente vs
mmap do PLE. Nao ha "maquina de config nova" nem schema diferente — a
hipotese registrada em `bench/qwen38-updates-2026-09/results/p4-item4-omlx-dev2-blocked.md`
("diferente do arm-config da 0.6.x") nao se confirmou.

### Arquivo e chave

- Arquivo: `<OMLX_BASE_PATH>/model_settings.json` (idem 0.6.x). Classe
  `ModelSettingsManager` (`omlx/model_settings.py`), atributo
  `self.settings_file = self.base_path / "model_settings.json"`.
- Formato: `{"version": <int>, "models": {<model_dir_name>: {...}}}`.
  `SETTINGS_VERSION = 1` em **ambas** as versoes
  (`omlx/model_settings.py:30`, idem em 0.6.4 e 0.7.0.dev2 — mesma linha,
  mesmo valor). Nao ha bump de versao entre as releases.
- Chave por modelo: o nome do diretorio do modelo (o mesmo
  `target_dir.name` que `omlx_config.py` ja usa), nao um profile separado.
  `model_profiles.json` existe na 0.7 mas so serve profiles/templates
  *universais* (sampling, grammar, etc.); `omlx/model_profiles.py:106-113`
  (0.6.4) e `omlx/model_profiles.py:112-113` (0.7.0.dev2) **excluem
  explicitamente** `qwen4_ple_ssd_offload` desse mecanismo — comentario no
  codigo: "Hardware-specific residency choice; never propagate across
  models." Ou seja: nao existe (nem deveria existir) um
  `model_profiles.json` para essa chave; `model_settings.json` e o unico
  lugar certo, em ambas as versoes.
- Campo: `qwen4_ple_ssd_offload: bool = False` (dataclass `ModelSettings`),
  mesma definicao/default nas duas arvores.

### Decisao residente vs mmap (`configure_ple_runtime`)

Cadeia idêntica nas duas versões:

1. `omlx/utils/model_loading.py` (dentro de `maybe_apply_pre_load_patches`,
   ramo `model_type == "qwen4_exp"`) monta o `mode` passado a
   `configure_qwen4_exp_runtime`:

   ```python
   configure_qwen4_exp_runtime(
       model_name,
       mode=(
           "mmap"
           if model_settings is not None
           and getattr(model_settings, "qwen4_ple_ssd_offload", False)
           else "resident" if model_settings is not None else None
       ),
       mtp_enabled=mtp_active,
   )
   ```

   Byte-idêntico entre 0.6.4 e 0.7.0.dev2 (`diff` do trecho = vazio).
2. `ModelSettingsManager.get_settings(model_id)` **nunca retorna `None`** —
   se o `model_id` nao estiver no arquivo, devolve `ModelSettings()` default
   (`qwen4_ple_ssd_offload=False`). Ou seja, sempre que o processo tem UM
   `model_settings.json` carregado (mesmo vazio), `model_settings is not
   None` e o `mode` explicito ("resident" ou "mmap") **sempre vence sobre**
   o env `OMLX_QWEN4_PLE_MODE` (que so e consultado dentro de
   `configure_ple_runtime` quando `mode is None`, isto e, quando nao existe
   manager de settings algum — praticamente nunca no fluxo do servidor).
   Isso bate exatamente com o diagnostico do `p4-item4-omlx-dev2-blocked.md`
   ("o env e sobreposto pelo setting explicito"); so que essa logica e a
   MESMA na 0.6.4 e na 0.7.0.dev2, nao uma regressao da 0.7.
3. `engine_pool.py::_qwen4_ple_offload_status` tambem le
   `getattr(settings, "qwen4_ple_ssd_offload", False)` diretamente — mesmo
   trecho nas duas arvores (linhas 404/419/596 na 0.6.4, 502/523/806 na
   0.7.0.dev2, logica identica).

### Por que o teste anterior (P4 item 4) viu "resident"

A hipotese mais provável, dado que a leitura é idêntica: naquela sessão o
`omlx serve` da 0.7.0.dev2 foi provavelmente exercitado direto (testando as
flags novas `--memory-guard`/`--paged-ssd-cache-dir`), sem passar pelo
`run-omlx.sh` + `omlx_config.py` apontando um `OMLX_BASE_PATH` com
`qwen4_ple_ssd_offload: true` já gravado para o diretorio exato do modelo —
portanto `get_settings()` caiu no default (`False`) e `mode` resolveu para
`"resident"` explicito, batendo com o log observado. Isso é reconciliável
com "o env é sobreposto pelo setting explícito": o problema nunca foi a 0.7
ler o formato errado, foi o processo não ter, no seu `OMLX_BASE_PATH`, um
`model_settings.json` com a chave setada para este modelo.

## O que foi mudado em `omlx_config.py` (e por quê)

Como a leitura e identica, a menor mudanca que faz sentido nao e mudar o
*shape* do arquivo — e tornar o gerador **ciente da versao alvo** e
adicionar uma rede de seguranca para quando uma versao futura *realmente*
mudar o schema:

- `MODEL_SETTINGS_VERSION_BY_OMLX_LINE = {"0.6": 1, "0.7": 1}` +
  `model_settings_version_for(omlx_version)`: resolve o int de versao a
  escrever a partir da linha de release (`major.minor`); sem
  `omlx_version` conhecido, mantem o comportamemto anterior
  (`MODEL_SETTINGS_VERSION = 1`, sem mudanca de bytes); com uma versao
  **desconhecida** (nem "0.6" nem "0.7"), levanta `ValueError` em vez de
  silenciosamente gravar um arquivo que aquela release pode nao ler —
  evita repetir, numa versao futura ainda nao auditada, o mesmo tipo de
  suposicao errada que gerou o bloqueio anterior.
- `write_omlx_state(..., omlx_version: str | None = None)`: usa
  `model_settings_version_for(omlx_version)` no lugar do `MODEL_SETTINGS_VERSION`
  fixo. Chamadores que nao passam `omlx_version` (todos os testes
  existentes, e qualquer script antigo) continuam recebendo exatamente o
  mesmo `model_settings.json` de antes — confirmado rodando a suite de
  testes sem alteracao (12/12 verdes) e comparando bytes.
  `--print-profile` agora inclui `"omlx_version"` no JSON resolvido
  impresso (apenas para rastreabilidade do valor usado); nao afeta a
  extracao de `cache_enabled` que `run-omlx.sh` faz desse JSON.
- `main()` resolve `omlx_version` nesta ordem: `--omlx-version` explicito >
  `$QWEN38_OMLX_EXPECTED_VERSION` (env — o mesmo nome que `run-omlx.sh` ja
  usa para o proprio gate de versao, herdado pelo subprocesso do gerador
  sem precisar tocar em `run-omlx.sh`) > campo `omlx_version` do proprio
  `--config` (o pin estatico da campanha, hoje `"v0.6.3rc2"`). Isso significa
  que rodar `QWEN38_OMLX_EXPECTED_VERSION=0.7.0.dev2 bash run-omlx.sh FN
  --print` (o comando do Step 2 do brief) ja passa a resolver
  `omlx_version="0.7.0.dev2"` sem qualquer edicao em `run-omlx.sh`.
- Novo helper `_config_omlx_version(path)`: le o campo `omlx_version` do
  JSON de config (mesmo campo que `run-omlx.sh` ja le via `python3 -c
  'json.load(...)["omlx_version"]'`), so usado como ultimo fallback.

### Verificacao (sem subir servidor)

1. Suite existente `tests/test_omlx_config.py`: 12/12 passam sem alteracao
   apos o edit (nenhum teste passa `omlx_version`, entao exercitam o
   default `MODEL_SETTINGS_VERSION = 1`, igual a antes).
2. Gerado o `model_settings.json` da arm `FN` duas vezes — uma com
   `--omlx-version v0.6.3rc2`, outra com
   `QWEN38_OMLX_EXPECTED_VERSION=0.7.0.dev2` no ambiente (sem
   `--omlx-version`) — e comparado byte a byte: **identico** nos dois
   casos (`version: 1`, `qwen4_ple_ssd_offload: true`, chave
   `Jundot-Qwen3.8-Flash-Next-oQ4e-mtp-2615fc0e976e65c2f3b55daca3a948f1cdc5b9f8`).
3. Carreguei o `model_settings.json` gerado (caso 0.7.0.dev2) direto no
   `omlx.model_settings.ModelSettingsManager` **da propria instalacao
   dev2** (`~/.local/opt/qwen38/omlx-v0.7.0.dev2/bin/python`, sem subir
   servidor) e reproduzi a ternaria exata de
   `omlx/utils/model_loading.py` que decide o `mode`:

   ```
   qwen4_ple_ssd_offload = True
   mtp_enabled = True
   resolved PLE mode = mmap
   ```

   Ou seja: com o `model_settings.json` que `omlx_config.py` ja gera para
   a arm `FN`, a propria logica da 0.7.0.dev2 resolve `mode="mmap"` — o
   caminho que, na 0.6.x, derrubou o residente de ~99.6 GB para ~69.6 GB.
4. `model_settings_version_for("0.8.1")` levanta `ValueError` (linha de
   release nao cadastrada) — confirma a rede de seguranca sem quebrar
   `None`/`"0.6.4"`/`"v0.7.0.dev2"` (todos retornam `1`).

## Confianca e o que falta

Alta confianca de que o `model_settings.json` gerado fara a 0.7.0.dev2
escolher `mode="mmap"` no boot real: a leitura do arquivo, a resolucao do
`model_id` pelo nome do diretorio, e a ternaria de decisao foram todas
exercitadas com o codigo real da instalacao dev2 (import direto, sem mock),
so faltando o proprio `mlx_vlm.models.qwen4_exp.language.configure_ple_runtime`
de fato remapear os tensores do PLE para mmap e o processo ficar residente
em ~70 GB — isso so um boot real confirma (memoria wired, nao logica de
config). Prosseguir para o Step 4 do brief (`run-candidate.sh c3 ... --tag
ple-check`) para validar `wired max < 85 GB` e o log `PLE mode ... : mmap`.
Se esse boot mostrar wired > 95 GB mesmo com `qwen4_ple_ssd_offload: true`
resolvido, o problema estara em `configure_ple_runtime`/no runtime de
tensores em si (fora do escopo desta task, que era so o gerador de config)
— nesse caso o candidato c3 sai da campanha por essa razao, nao por falta
do setting.
