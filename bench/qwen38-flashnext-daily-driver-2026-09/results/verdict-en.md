The incumbent, ddalcu mixed-4/8 on mlx-serve 26.9.2, is the most responsive Flash-Next daily driver on the M4 Max 128 GB. Its T_turn (median of 3 reps) is 11.03 s at 32K and 12.35 s at 128K. That is 18% ahead of oQ4e on oMLX 0.7.0.dev2 (13.48 / 15.03 s).

The lead comes from TTFT. At 128K the warm turn responds in 2.1 s against 4.8 s, and the first turn in 178 s against 259 s. Decode ties at ~50 tok/s.

MTPLX 2.11.2 leads decode at 32K, but it refuses 128K and 256K on this Mac (HTTP 507, fit of 114,688 tokens). oMLX 0.6.4 trails 0.7.0.dev2 on the same weights. Agent quality (Terminal-Bench) was not measured.
