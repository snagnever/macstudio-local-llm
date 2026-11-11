# Task 0: Pré-voo (2026-11-11)

| item | valor |
|---|---|
| host | `macstudio`, acessível por `ssh -o BatchMode=yes vitor@mac-studio` |
| macOS | 26.6.2 |
| disco livre | 861 GB de 1.8 TB |
| swap no início | 1727 MB usados de 3072 MB |
| Claude Code | 2.1.292, em `/opt/homebrew/bin/claude` |
| runtimes Splash | `splash-v1.3.1`, `v1.4.0`, `v1.4.1`, `v1.5.0`, `v1.6.0`, `splash-main-3135ab4`; a `v1.6.1` entra neste Task |
| pack `k2` | snapshot `0142554` com 92 GB (`du -shL`) |
| servidor do usuário | Splash 1.5.0 na porta 8585, pid 29595, de 10/11 19:40 |
| `*_proxy` no shell interativo (`zsh -ilc env`) | nenhuma variável |

**Proxy (Step 2):** o shell interativo do rig não define `http_proxy`. A chave do servidor da 1.5.0 não vazou por esse caminho, e não há chave para trocar.

**Instalação (Step 3):** `SPLASH_TAG=1.6.1 INSTALL_EXPECTED_SHA256=0ed408a7…ce6c install-runtime.sh splash`, num shell de login. O `gh` do rig não tem login válido, então o script não lê o digest da API. O valor fixado é o digest que o GitHub publica para o asset, lido no MacBook. O SHA-256 do download confere. `splash --version` mostra `Splash 1.6.1`.

**Help:** [`splash-161-help.txt`](splash-161-help.txt). Contra a 1.6.0, o único flag novo é `--activations`, e nenhum flag foi removido. O `--ple-memory` aceita `off`, e o padrão é `auto`.
