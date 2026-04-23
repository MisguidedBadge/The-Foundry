# Qwen3.6-35B-A3B

## Summary

- Model path: `/workspace/ai_projects/llm/model_explorer/terminal/models/Qwen3.6-35B-A3B/BF16/Qwen3.6-35B-A3B-BF16-00001-of-00002.gguf`
- Architecture: `qwen35moe`
- Datatype: `BF16`
- Size label: `35B-A3B`
- Total local model bytes: `69376638176`
- Max trained context: `262144`
- KV bytes per token estimate: `81920`
- Recommended interactive ctx: `16384`
- Recommended long ctx: `32768`
- Highest successfully stress-tested ctx: `262144`

## Stress Results

- ctx `4096`: pass, tok/s `3.21`, peak_gpu `28%`, peak_vram `158642176`, unload_delta `118784`
- ctx `8192`: pass, tok/s `4.33`, peak_gpu `27%`, peak_vram `157667328`, unload_delta `16384`
- ctx `16384`: pass, tok/s `3.35`, peak_gpu `27%`, peak_vram `158359552`, unload_delta `8192`
- ctx `32768`: pass, tok/s `3.77`, peak_gpu `48%`, peak_vram `161247232`, unload_delta `4096`
- ctx `65536`: pass, tok/s `4.09`, peak_gpu `49%`, peak_vram `164216832`, unload_delta `0`
- ctx `131072`: pass, tok/s `6.44`, peak_gpu `52%`, peak_vram `169582592`, unload_delta `4096`
- ctx `262144`: pass, tok/s `8.69`, peak_gpu `56%`, peak_vram `183685120`, unload_delta `0`
