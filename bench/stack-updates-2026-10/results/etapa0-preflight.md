# Etapa 0 — pré-voo (2026-10-22 17:55:48)

## Rig

```
Apple M4 Max
137438953472
/dev/disk3s1s1      1858   11       275     5%  458732 2892251000    0%   /
ProductName:		macOS ProductVersion:		26.6.2 BuildVersion:		25G83 
```

## Driver diário parado

PID 24746, comando em `results/daily-driver-cmd.txt` (mlx-serve 26.10.1, Swift 1.5, 262144).

## Runtimes

| runtime | versão | asset SHA256 |
|---|---|---|
| mlx-serve | mlx-serve 26.10.3 | d1781c89c206f0d077d6d1abbcab43aa9ec65280202c83eac908f957956b652b (= digest publicado) |
| Splash | Splash 1.4.0 | 4c0f032a5392a6c559f081a0052278fbc0ea5abee2d16b820a015cc9b1826a2d (= digest publicado) |
| oMLX | 0.7.2, mlx 0.32.4 | git tag v0.7.2 |

O gh do rig não autentica numa sessão ssh. Os assets do mlx-serve e do Splash foram baixados no laptop, conferidos contra o digest publicado e copiados. A extração repete os passos do `install-runtime.sh`.
