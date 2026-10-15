# Recibo do pin do GGUF ggml-org (2026-10-15)

O rig baixou `ggml-org/Qwen3.8-Flash-Next-GGUF` na revisão `052beeaca7bec4a303e59cc7bc630c4f3a1b845d`. O HEAD em 2026-10-15 é `0a61d2b8d851e0bb9f22b973befd714413d63c6f`. O SHA-256 do LFS de cada arquivo que a Task 8 usa é o mesmo nas duas revisões (API `tree` do Hugging Face):

| arquivo | sha256 (LFS) | 052beea = 0a61d2b |
| --- | --- | --- |
| Qwen3.8-Flash-Next-IQ4_NL-00001-of-00002.gguf | 851652eef30d117a34fdc0d13e05da4c488a8cdad3654d38c4aa69a2d8a1fabc | sim |
| Qwen3.8-Flash-Next-IQ4_NL-00002-of-00002.gguf | 0299b147e42517ff8fa3a4fa66d370c77ce01c44ed8cbc3451b7a42caad5fc10 | sim |
| mtp-Qwen3.8-Flash-Next-Q8_0.gguf | 6be8a94e2d94107b7f38fdc957c3460ffeb6ff6302edef92c50738682f9dc0e0 | sim |

O teste mede os mesmos bytes do HEAD. Não recalculei o hash dos arquivos no disco; o download do `huggingface_hub` confere o SHA do LFS.
