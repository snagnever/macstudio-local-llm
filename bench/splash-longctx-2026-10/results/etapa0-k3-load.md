# Etapa 0 — o Splash 1.4.0 carrega o GSQ-RCO-Coder GGUF? (2026-10-24)

**Recusa.** `k3a` a 32768, cenário cold, tag `smoke`. O Splash leu o cache do HF e parou antes de subir o servidor (`run-candidate.sh` saiu com 69):

```
Could not reach the Hub (HF_HUB_OFFLINE is set); installing ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF@bba88856f8c3 from the Hub cache.
error: GGUF metadata does not match the target: expert_count 256 (expected 512)
error: model download or verification failed
```

A mensagem é a da [incoai/splash#527](https://github.com/incoai/splash/issues/527). A correção ([#561](https://github.com/incoai/splash/pull/561)) entrou no `main` em 23/10 e não está numa release. Consequências no plano:
- os braços `k3*` não rodam nos Tasks 1 a 4;
- o Task 5 mede o GSQ-RCO-Coder no mlx-serve (`r1z`, `r1zy`);
- o Task 5b roda se sair uma release com a #561 antes do Task 6.
