# Etapa 2 (extra) — contexto maior: o s1 cabe a 256K e 512K (2026-09-16)

Pergunta levantada em revisão: a afirmação "a 128K não há margem de memória" era forte demais
para o s1. Este teste re-mede o driver no **perfil 512k** (524288, YaRN 2.0 + KV 8-bit) e o
arranjo B (+s1) a **256K** e **512K**, 1 repetição, driver reiniciado antes de cada arranjo.

## Resultado

| banda | arranjo | `T_turno` | Δ vs A | decode | cold TTFT | wired | swap Δ | servidos |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 256K | A sozinho | 11,48 s | — | 56,8 tok/s | 419,9 s | 110,6 GB | −0,01 | 5/5 |
| 256K | **B +s1** | 17,18 s | **+49,7%** | 35,8 | 419,9 s | 112,6 GB | −0,03 | **5/5** |
| 512K | A sozinho | 16,24 s | — | 38,9 tok/s | 843,6 s | 117,3 GB | −0,03 | 5/5 |
| 512K | **B +s1** | 21,86 s | **+34,6%** | 28,1 | **933,7 s** | 116,1 GB | −0,01 | **5/5** |

## Leitura

- **O s1 cabe a 256K e a 512K.** Nos dois, o arranjo B completou os 5 cenários, **sem nenhum
  erro de contexto** (o s2 é que reduz o contexto, não o s1) e sem swap crescente.
- O perfil 512k usa **KV 8-bit**, o que dá margem: o wired do B@512K (116,1 GB) fica até abaixo
  do A@512K (117,3 GB) — variação entre execuções.
- O custo é **velocidade**, e ela piora com o contexto: +31,1% (128K), +49,7% (256K), +34,6%
  (512K) na carga contínua. O `cold` do B@512K leva 933,7 s contra 843,6 s do driver sozinho.

## Conclusão corrigida

A tese "não cabe" só se sustenta para o **s2** a 128K (contexto reduzido a ~87K). Para o s1,
**cabe em toda a faixa testada (32K–512K)**; o que reprova no gate é a perda de `T_turno`
(+31% a +50%) sob carga contínua — que cai para ≤12% a 32K quando os turnos são intermitentes.

Dados: `A/B-262144-t1.0.jsonl`, `A/B-524288-t1.0.jsonl` (perfil 512k, KV 8-bit).
