# Qwen3.8 prefix-cache campaign summary

> Generated: 2026-08-28T00:41:47.724674+00:00

## Runtime gates

| Arm | Runtime | Records | Status | Complete | Failures |
|---|---|---:|---|---|---|
| K | oMLX | 15 | PASS | no | — |
| L | oMLX | 82 | FAIL | yes | correct, cache_hit_ratio, error, ram_peak_gb, swap_delta_gb_unavailable, ram_peak_gb_unavailable |
| M | oMLX | 30 | FAIL | no | correct, error, cache_hit_ratio |
| N | oMLX | 30 | FAIL | no | cache_hit_ratio, correct, error |
| P | mlx-dspark | 15 | FAIL | no | ram_peak_gb, correct, error |
| Q | mlx-dspark | 145 | FAIL | no | cache_hit_ratio, correct, error, ram_peak_gb |
| R | mlx-dspark | 130 | FAIL | no | cache_hit_ratio, swap_delta_gb, ram_peak_gb, correct, error |
| S | mlx-dspark | 151 | FAIL | yes | cache_hit_ratio, correct, error, ram_peak_gb, swap_delta_gb_unavailable, ram_peak_gb_unavailable |
| T | oMLX | 67 | FAIL | no | correct, error, cache_hit_ratio, ram_peak_gb |
| U | oMLX | 15 | FAIL | no | correct, error |
| V | MTPLX | 65 | FAIL | yes | cache_hit_ratio, correct, ram_peak_gb, swap_delta_gb, error |
| W | oMLX | 15 | FAIL | no | correct, error |
| X | oMLX | 15 | PASS | no | — |
| Y | MTPLX | 78 | FAIL | yes | cache_hit_ratio, correct, ram_peak_gb, error, swap_delta_gb, swap_delta_gb_unavailable, ram_peak_gb_unavailable |
| Z | MTPLX | 30 | FAIL | no | cache_hit_ratio, ram_peak_gb, correct |

## Measurements

| Runtime | Arm | Context | Scenario | N | TTFT median ms | E2E median ms | Cache hit median | Failed records |
|---|---|---:|---|---:|---:|---:|---:|---:|
| MTPLX | V | 131072 | append | 3 | 11290.45 | 103349.29 | 0.9905 | 3 |
| MTPLX | V | 131072 | cold | 3 | 853223.42 | 894961.89 | 0.0000 | 3 |
| MTPLX | V | 131072 | identical | 3 | 725.20 | 48940.00 | 1.0000 | 3 |
| MTPLX | V | 131072 | middle_mutation | 3 | 818807.43 | 890598.82 | 0.0000 | 3 |
| MTPLX | V | 131072 | tool_turn | 3 | 827581.42 | 860887.22 | 0.0000 | 3 |
| MTPLX | V | 262144 | append | 1 | 21604.58 | 519402.07 | 0.9954 | 1 |
| MTPLX | V | 262144 | cold | 1 | 2609073.77 | 2746648.60 | 0.0000 | 1 |
| MTPLX | V | 262144 | identical | 1 | 1903.85 | 125868.16 | 1.0000 | 1 |
| MTPLX | V | 262144 | middle_mutation | 1 | 2640191.22 | 2895263.11 | 0.0080 | 1 |
| MTPLX | V | 262144 | tool_turn | 1 | 20801.12 | 374714.22 | 0.9958 | 1 |
| MTPLX | V | 32768 | append | 3 | 6097.71 | 14384.34 | 0.9603 | 3 |
| MTPLX | V | 32768 | cold | 3 | 119175.00 | 124125.23 | 0.0000 | 3 |
| MTPLX | V | 32768 | identical | 3 | 271.34 | 6249.25 | 1.0000 | 3 |
| MTPLX | V | 32768 | middle_mutation | 3 | 111318.90 | 131563.97 | 0.0751 | 3 |
| MTPLX | V | 32768 | tool_turn | 3 | 5887.25 | 11617.51 | 0.9621 | 3 |
| MTPLX | V | 65536 | append | 3 | 7962.93 | 53618.00 | 0.9806 | 3 |
| MTPLX | V | 65536 | cold | 3 | 298947.02 | 331320.51 | 0.0000 | 3 |
| MTPLX | V | 65536 | identical | 3 | 341.18 | 48847.36 | 1.0000 | 3 |
| MTPLX | V | 65536 | middle_mutation | 3 | 290914.96 | 354505.21 | 0.0341 | 3 |
| MTPLX | V | 65536 | tool_turn | 3 | 7293.39 | 40025.08 | 0.9825 | 3 |
| MTPLX | V | 8192 | append | 3 | 4909.88 | 9610.79 | 0.6923 | 3 |
| MTPLX | V | 8192 | cold | 3 | 10827.80 | 15209.81 | 0.0000 | 0 |
| MTPLX | V | 8192 | identical | 3 | 169.41 | 5398.73 | 0.9996 | 0 |
| MTPLX | V | 8192 | middle_mutation | 3 | 10969.85 | 29133.67 | 0.0000 | 0 |
| MTPLX | V | 8192 | tool_turn | 3 | 4672.36 | 9389.06 | 0.7132 | 3 |
| MTPLX | Y | 131072 | append | 3 | 14050.86 | 116109.53 | 0.9905 | 3 |
| MTPLX | Y | 131072 | cold | 3 | 818669.29 | 870473.32 | 0.0000 | 3 |
| MTPLX | Y | 131072 | identical | 3 | 549.46 | 44443.25 | 1.0000 | 3 |
| MTPLX | Y | 131072 | middle_mutation | 3 | 818278.58 | 917766.58 | 0.0000 | 3 |
| MTPLX | Y | 131072 | tool_turn | 3 | 827456.71 | 857327.28 | 0.0000 | 3 |
| MTPLX | Y | 262144 | append | 1 | 22342.80 | 315075.96 | 0.9954 | 1 |
| MTPLX | Y | 262144 | cold | 1 | 2591502.32 | 2718468.02 | 0.0000 | 1 |
| MTPLX | Y | 262144 | identical | 1 | 1942.85 | 124804.38 | 1.0000 | 1 |
| MTPLX | Y | 32768 | append | 6 | 6164.02 | 14511.29 | 0.9603 | 6 |
| MTPLX | Y | 32768 | cold | 6 | 119219.79 | 126531.33 | 0.0000 | 6 |
| MTPLX | Y | 32768 | identical | 6 | 324.69 | 9150.86 | 1.0000 | 6 |
| MTPLX | Y | 32768 | middle_mutation | 6 | 111469.02 | 153012.60 | 0.0751 | 6 |
| MTPLX | Y | 32768 | tool_turn | 6 | 5966.19 | 11811.82 | 0.9621 | 6 |
| MTPLX | Y | 65536 | append | 3 | 8115.43 | 58685.11 | 0.9806 | 3 |
| MTPLX | Y | 65536 | cold | 3 | 299097.83 | 329726.85 | 0.0000 | 3 |
| MTPLX | Y | 65536 | identical | 3 | 390.53 | 51442.18 | 1.0000 | 3 |
| MTPLX | Y | 65536 | middle_mutation | 3 | 295662.72 | 408901.52 | 0.0341 | 3 |
| MTPLX | Y | 65536 | tool_turn | 3 | 7441.31 | 37905.82 | 0.9825 | 3 |
| MTPLX | Y | 8192 | append | 3 | 5055.13 | 10878.64 | 0.6923 | 3 |
| MTPLX | Y | 8192 | cold | 3 | 10893.15 | 16931.79 | 0.0000 | 0 |
| MTPLX | Y | 8192 | identical | 3 | 224.04 | 6257.35 | 0.9996 | 0 |
| MTPLX | Y | 8192 | middle_mutation | 3 | 11036.44 | 32446.35 | 0.0000 | 1 |
| MTPLX | Y | 8192 | tool_turn | 3 | 4826.60 | 7471.73 | 0.7132 | 3 |
| MTPLX | Z | 32768 | append | 3 | 6154.27 | 15704.96 | 0.9603 | 3 |
| MTPLX | Z | 32768 | cold | 3 | 119236.03 | 126406.79 | 0.0000 | 3 |
| MTPLX | Z | 32768 | identical | 3 | 333.17 | 5761.57 | 1.0000 | 3 |
| MTPLX | Z | 32768 | middle_mutation | 3 | 111448.09 | 136090.16 | 0.0751 | 3 |
| MTPLX | Z | 32768 | tool_turn | 3 | 5893.64 | 10449.29 | 0.9621 | 3 |
| MTPLX | Z | 8192 | append | 3 | 4991.83 | 11909.13 | 0.6923 | 3 |
| MTPLX | Z | 8192 | cold | 3 | 10900.71 | 18383.84 | 0.0000 | 0 |
| MTPLX | Z | 8192 | identical | 3 | 240.02 | 5951.88 | 0.9996 | 0 |
| MTPLX | Z | 8192 | middle_mutation | 3 | 11057.90 | 45351.98 | 0.0000 | 0 |
| MTPLX | Z | 8192 | tool_turn | 3 | 4769.81 | 10372.79 | 0.7132 | 3 |
| mlx-dspark | P | 32768 | append | 3 | 112281.00 | 272527.44 | 0.0000 | 3 |
| mlx-dspark | P | 32768 | cold | 3 | 107846.00 | 192677.17 | 0.0000 | 3 |
| mlx-dspark | P | 32768 | identical | 3 | 107829.00 | 219783.36 | 0.0000 | 3 |
| mlx-dspark | P | 32768 | middle_mutation | 3 | 107978.00 | 245020.18 | 0.0000 | 3 |
| mlx-dspark | P | 32768 | tool_turn | 3 | 112514.00 | 183335.84 | 0.0000 | 3 |
| mlx-dspark | Q | 32768 | append | 16 | 17238.00 | 132276.57 | 0.8674 | 16 |
| mlx-dspark | Q | 32768 | cold | 16 | 107908.50 | 178968.78 | 0.0015 | 12 |
| mlx-dspark | Q | 32768 | identical | 16 | 232.00 | 74789.68 | 1.0000 | 13 |
| mlx-dspark | Q | 32768 | middle_mutation | 16 | 78777.00 | 227155.78 | 0.2997 | 12 |
| mlx-dspark | Q | 32768 | tool_turn | 16 | 5219.00 | 65996.26 | 0.9623 | 12 |
| mlx-dspark | Q | 8192 | append | 13 | 14033.00 | 268037.21 | 0.0109 | 13 |
| mlx-dspark | Q | 8192 | cold | 13 | 10133.00 | 54805.60 | 0.0150 | 0 |
| mlx-dspark | Q | 8192 | identical | 13 | 206.00 | 50702.74 | 0.9996 | 1 |
| mlx-dspark | Q | 8192 | middle_mutation | 13 | 10234.00 | 120434.15 | 0.0148 | 2 |
| mlx-dspark | Q | 8192 | tool_turn | 13 | 4332.00 | 120147.32 | 0.7183 | 13 |
| mlx-dspark | R | 32768 | append | 13 | 17388.00 | 65373.88 | 0.8674 | 13 |
| mlx-dspark | R | 32768 | cold | 13 | 108777.00 | 145128.48 | 0.0015 | 13 |
| mlx-dspark | R | 32768 | identical | 13 | 172.00 | 30596.11 | 1.0000 | 13 |
| mlx-dspark | R | 32768 | middle_mutation | 13 | 79345.00 | 145707.07 | 0.2997 | 13 |
| mlx-dspark | R | 32768 | tool_turn | 13 | 5242.00 | 25144.21 | 0.9623 | 13 |
| mlx-dspark | R | 8192 | append | 13 | 14127.00 | 109219.91 | 0.0109 | 13 |
| mlx-dspark | R | 8192 | cold | 13 | 10200.00 | 39941.03 | 0.0150 | 9 |
| mlx-dspark | R | 8192 | identical | 13 | 152.00 | 21452.42 | 0.9996 | 9 |
| mlx-dspark | R | 8192 | middle_mutation | 13 | 10296.00 | 51597.17 | 0.0151 | 9 |
| mlx-dspark | R | 8192 | tool_turn | 13 | 4346.00 | 42314.86 | 0.7183 | 13 |
| mlx-dspark | S | 131072 | append | 3 | 30615.00 | 93776.33 | 0.9702 | 3 |
| mlx-dspark | S | 131072 | cold | 3 | 708900.00 | 752944.00 | 0.0000 | 3 |
| mlx-dspark | S | 131072 | identical | 3 | 301.00 | 44519.57 | 1.0000 | 3 |
| mlx-dspark | S | 131072 | middle_mutation | 3 | 495872.00 | 555900.50 | 0.3912 | 3 |
| mlx-dspark | S | 131072 | tool_turn | 3 | 9309.00 | 42459.35 | 0.9915 | 3 |
| mlx-dspark | S | 262144 | append | 2 | 174815.00 | 310290.56 | 0.9537 | 2 |
| mlx-dspark | S | 262144 | cold | 1 | 2059434.00 | 2136736.16 | 0.0000 | 1 |
| mlx-dspark | S | 262144 | identical | 2 | 437.50 | 128725.73 | 1.0000 | 2 |
| mlx-dspark | S | 262144 | middle_mutation | 1 | 1642274.00 | 1718439.49 | 0.3830 | 1 |
| mlx-dspark | S | 262144 | tool_turn | 1 | 14786.00 | 111013.43 | 0.9958 | 1 |
| mlx-dspark | S | 32768 | append | 10 | 17214.00 | 66313.93 | 0.8674 | 10 |
| mlx-dspark | S | 32768 | cold | 10 | 107850.50 | 124516.94 | 0.0015 | 6 |
| mlx-dspark | S | 32768 | identical | 10 | 173.00 | 17056.18 | 1.0000 | 7 |
| mlx-dspark | S | 32768 | middle_mutation | 10 | 78722.50 | 139129.99 | 0.2997 | 6 |
| mlx-dspark | S | 32768 | tool_turn | 9 | 5192.00 | 16360.75 | 0.9623 | 5 |
| mlx-dspark | S | 65536 | append | 3 | 21572.00 | 107887.79 | 0.9386 | 3 |
| mlx-dspark | S | 65536 | cold | 3 | 268813.00 | 329755.67 | 0.0007 | 3 |
| mlx-dspark | S | 65536 | identical | 3 | 198.00 | 39369.53 | 1.0000 | 3 |
| mlx-dspark | S | 65536 | middle_mutation | 3 | 174201.00 | 288060.36 | 0.4089 | 3 |
| mlx-dspark | S | 65536 | tool_turn | 3 | 6480.00 | 42169.42 | 0.9825 | 3 |
| mlx-dspark | S | 8192 | append | 13 | 14029.00 | 101565.62 | 0.0109 | 13 |
| mlx-dspark | S | 8192 | cold | 13 | 10127.00 | 30713.11 | 0.0150 | 0 |
| mlx-dspark | S | 8192 | identical | 13 | 154.00 | 18398.68 | 0.9996 | 0 |
| mlx-dspark | S | 8192 | middle_mutation | 13 | 10218.00 | 58520.83 | 0.0148 | 3 |
| mlx-dspark | S | 8192 | tool_turn | 13 | 4305.00 | 44510.14 | 0.7183 | 13 |
| oMLX | K | 32768 | append | 3 | 8204.38 | 24641.04 | 0.9420 | 0 |
| oMLX | K | 32768 | cold | 3 | 116404.74 | 128890.37 | 0.0000 | 0 |
| oMLX | K | 32768 | identical | 3 | 3289.32 | 19480.79 | 0.9778 | 0 |
| oMLX | K | 32768 | middle_mutation | 3 | 67101.38 | 103909.03 | 0.4506 | 0 |
| oMLX | K | 32768 | tool_turn | 3 | 8371.15 | 25196.59 | 0.9408 | 0 |
| oMLX | L | 131072 | append | 3 | 15599.20 | 107400.11 | 0.9864 | 3 |
| oMLX | L | 131072 | cold | 3 | 773945.17 | 817637.15 | 0.0000 | 3 |
| oMLX | L | 131072 | identical | 3 | 6754.57 | 55817.36 | 0.9945 | 3 |
| oMLX | L | 131072 | middle_mutation | 3 | 469689.53 | 533168.91 | 0.4890 | 3 |
| oMLX | L | 131072 | tool_turn | 3 | 16044.94 | 66469.80 | 0.9861 | 3 |
| oMLX | L | 16384 | append | 3 | 7754.52 | 81904.28 | 0.8566 | 3 |
| oMLX | L | 16384 | cold | 3 | 45084.13 | 68818.31 | 0.0000 | 0 |
| oMLX | L | 16384 | identical | 3 | 3374.00 | 48050.63 | 0.9376 | 3 |
| oMLX | L | 16384 | middle_mutation | 3 | 28922.92 | 121005.21 | 0.3738 | 2 |
| oMLX | L | 16384 | tool_turn | 3 | 7900.32 | 38064.04 | 0.8539 | 3 |
| oMLX | L | 262144 | append | 2 | 25099.53 | 144296.94 | 0.9934 | 2 |
| oMLX | L | 262144 | cold | 1 | 2233928.18 | 2422952.81 | 0.0000 | 1 |
| oMLX | L | 262144 | identical | 2 | 12057.02 | 83282.82 | 0.9974 | 2 |
| oMLX | L | 262144 | middle_mutation | 1 | 1450714.24 | 1570858.99 | 0.4947 | 1 |
| oMLX | L | 262144 | tool_turn | 1 | 25433.06 | 78338.33 | 0.9933 | 1 |
| oMLX | L | 32768 | append | 6 | 8615.01 | 32883.49 | 0.9408 | 1 |
| oMLX | L | 32768 | cold | 6 | 119140.37 | 134635.38 | 0.0000 | 0 |
| oMLX | L | 32768 | identical | 6 | 3620.81 | 21148.55 | 0.9765 | 0 |
| oMLX | L | 32768 | middle_mutation | 6 | 68940.11 | 146968.73 | 0.4500 | 2 |
| oMLX | L | 32768 | tool_turn | 6 | 8783.03 | 17065.45 | 0.9396 | 1 |
| oMLX | L | 65536 | append | 3 | 11062.62 | 96158.76 | 0.9721 | 0 |
| oMLX | L | 65536 | cold | 3 | 296739.30 | 356429.38 | 0.0000 | 0 |
| oMLX | L | 65536 | identical | 3 | 4699.89 | 50489.89 | 0.9888 | 0 |
| oMLX | L | 65536 | middle_mutation | 3 | 171328.06 | 289477.47 | 0.4771 | 2 |
| oMLX | L | 65536 | tool_turn | 3 | 11315.89 | 45173.79 | 0.9715 | 0 |
| oMLX | M | 16384 | append | 3 | 22850.62 | 101388.23 | 0.0000 | 3 |
| oMLX | M | 16384 | cold | 3 | 20635.20 | 62367.10 | 0.0000 | 1 |
| oMLX | M | 16384 | identical | 3 | 21019.40 | 104210.05 | 0.0000 | 3 |
| oMLX | M | 16384 | middle_mutation | 3 | 20632.74 | 104237.19 | 0.0000 | 3 |
| oMLX | M | 16384 | tool_turn | 3 | 22991.40 | 109840.58 | 0.0000 | 3 |
| oMLX | M | 32768 | append | 3 | 57182.07 | 148019.50 | 0.0000 | 3 |
| oMLX | M | 32768 | cold | 3 | 53290.31 | 145838.17 | 0.0000 | 3 |
| oMLX | M | 32768 | identical | 3 | 55202.52 | 147197.15 | 0.0000 | 3 |
| oMLX | M | 32768 | middle_mutation | 3 | 52563.08 | 138906.35 | 0.0000 | 3 |
| oMLX | M | 32768 | tool_turn | 3 | 57277.68 | 146950.18 | 0.0000 | 3 |
| oMLX | N | 16384 | append | 3 | 26272.86 | 75543.36 | 0.0000 | 3 |
| oMLX | N | 16384 | cold | 3 | 23761.34 | 62422.98 | 0.0000 | 0 |
| oMLX | N | 16384 | identical | 3 | 24139.72 | 107333.70 | 0.0000 | 3 |
| oMLX | N | 16384 | middle_mutation | 3 | 23746.05 | 86546.06 | 0.0000 | 1 |
| oMLX | N | 16384 | tool_turn | 3 | 26534.07 | 114130.29 | 0.0000 | 3 |
| oMLX | N | 32768 | append | 3 | 66235.16 | 158870.51 | 0.0000 | 3 |
| oMLX | N | 32768 | cold | 3 | 61116.57 | 152203.62 | 0.0000 | 2 |
| oMLX | N | 32768 | identical | 3 | 63705.79 | 153874.01 | 0.0000 | 3 |
| oMLX | N | 32768 | middle_mutation | 3 | 61059.23 | 152270.86 | 0.0000 | 3 |
| oMLX | N | 32768 | tool_turn | 3 | 66377.02 | 159763.27 | 0.0000 | 3 |
| oMLX | T | 131072 | append | 3 | 15710.43 | 148763.31 | 0.9864 | 3 |
| oMLX | T | 131072 | cold | 3 | 775665.19 | 818373.24 | 0.0000 | 3 |
| oMLX | T | 131072 | identical | 3 | 6803.51 | 50626.53 | 0.9945 | 3 |
| oMLX | T | 131072 | middle_mutation | 3 | 470639.05 | 535022.54 | 0.4890 | 3 |
| oMLX | T | 131072 | tool_turn | 3 | 16105.95 | 57374.68 | 0.9861 | 3 |
| oMLX | T | 262144 | append | 2 | 25360.29 | 130190.98 | 0.9934 | 2 |
| oMLX | T | 262144 | cold | 1 | 2259879.88 | 2312888.21 | 0.0000 | 1 |
| oMLX | T | 262144 | identical | 2 | 12135.76 | 119618.51 | 0.9974 | 2 |
| oMLX | T | 262144 | middle_mutation | 1 | 1468376.40 | 1573084.52 | 0.4947 | 1 |
| oMLX | T | 262144 | tool_turn | 1 | 26224.69 | 72568.83 | 0.9933 | 1 |
| oMLX | T | 32768 | append | 3 | 9302.15 | 66056.65 | 0.9443 | 1 |
| oMLX | T | 32768 | cold | 3 | 137379.49 | 173625.81 | 0.0000 | 0 |
| oMLX | T | 32768 | identical | 3 | 3977.05 | 41825.74 | 0.9775 | 0 |
| oMLX | T | 32768 | middle_mutation | 3 | 70660.83 | 105067.92 | 0.4882 | 1 |
| oMLX | T | 32768 | tool_turn | 3 | 9224.50 | 21336.49 | 0.9431 | 0 |
| oMLX | T | 65536 | append | 6 | 157253.37 | 249509.70 | 0.4861 | 3 |
| oMLX | T | 65536 | cold | 6 | 297028.61 | 338401.10 | 0.0000 | 0 |
| oMLX | T | 65536 | identical | 6 | 150841.84 | 203024.64 | 0.4944 | 3 |
| oMLX | T | 65536 | middle_mutation | 6 | 234546.47 | 328076.25 | 0.2385 | 1 |
| oMLX | T | 65536 | tool_turn | 6 | 157496.93 | 184366.00 | 0.4858 | 3 |
| oMLX | U | 32768 | append | 3 | 8313.76 | 74593.60 | 0.9443 | 2 |
| oMLX | U | 32768 | cold | 3 | 122296.93 | 161017.73 | 0.0000 | 0 |
| oMLX | U | 32768 | identical | 3 | 3593.72 | 43111.21 | 0.9775 | 0 |
| oMLX | U | 32768 | middle_mutation | 3 | 66000.52 | 129165.63 | 0.4882 | 2 |
| oMLX | U | 32768 | tool_turn | 3 | 8595.92 | 66151.36 | 0.9431 | 1 |
| oMLX | W | 32768 | append | 3 | 122692.46 | 237981.54 | 0.0000 | 0 |
| oMLX | W | 32768 | cold | 3 | 117612.04 | 167179.19 | 0.0000 | 0 |
| oMLX | W | 32768 | identical | 3 | 117616.34 | 154797.01 | 0.0000 | 0 |
| oMLX | W | 32768 | middle_mutation | 3 | 117784.16 | 289495.63 | 0.0000 | 2 |
| oMLX | W | 32768 | tool_turn | 3 | 122885.09 | 172616.16 | 0.0000 | 0 |
| oMLX | X | 32768 | append | 3 | 125448.19 | 242899.21 | 0.0000 | 0 |
| oMLX | X | 32768 | cold | 3 | 120431.80 | 157960.73 | 0.0000 | 0 |
| oMLX | X | 32768 | identical | 3 | 120437.93 | 170535.42 | 0.0000 | 0 |
| oMLX | X | 32768 | middle_mutation | 3 | 120613.25 | 171985.58 | 0.0000 | 0 |
| oMLX | X | 32768 | tool_turn | 3 | 125615.44 | 157552.71 | 0.0000 | 0 |

## SpecPrefill gate

| Arm | Baseline | Status | Advance to 65K | Failures |
|---|---|---|---|---|
| M | L | FAIL | no | ttft_16384, incompatible_comparison, functional, prompt_work_mode, needle_evidence, static_prefix |
| N | L | FAIL | no | ttft_16384, incompatible_comparison, functional, prompt_work_mode, needle_evidence, static_prefix |

## ANE prefill gate

| Arm | Baseline | Status | Confirmed operations | Failures |
|---|---|---|---:|---|
| O | J | INCONCLUSIVE | 0 | missing_16384, missing_32768, ttft |

## mlx-dspark Gate 8

| Arm | Status | 8K decode | 32K decode | 32K warm total | Failures |
|---|---|---:|---:|---:|---|
| R | FAIL | 2.212 | 1.904 | 2.327698214442458 | correct |
| S | INCONCLUSIVE | 0.000 | 0.000 | — | performance_pairs |
