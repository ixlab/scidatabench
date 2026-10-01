# S4. Cost and Pricing

The table gives the per-million-token list prices (USD) used for every cost
figure in the paper (Figure 2 and Table 5). Prices were retrieved on
2026-09-15.

| Model | Input | Cached input | Output | Source |
|---|---:|---:|---:|---|
| GPT-OSS 120B | 0.03 | – | 0.17 | OpenRouter (AkashML, CoreWeave) |
| Gemma 4 31B | 0.08 | – | 0.30 | OpenRouter (Reka) |
| Qwen 3.6 27B | 0.30 | – | 2.00 | OpenRouter (Chutes) |
| Gemini 2.5 Flash | 0.30 | 0.03 | 2.50 | Google AI Developer API |
| Gemini 3 Flash | 0.50 | 0.05 | 3.00 | Google AI Developer API |
| Gemini 3.7 Flash | 0.75 | 0.075 | 3.75 | Google AI Developer API |
| Gemini 2.5 Pro | 1.25 | 0.125 | 10.00 | Google AI Developer API |
| Gemini 3.1 Pro | 2.00 | 0.20 | 12.00 | Google AI Developer API |

The cost of one scenario is

$$
(n_{\text{in}} - n_{\text{cached}}) \cdot p_{\text{in}}
+ n_{\text{cached}} \cdot p_{\text{cached}}
+ n_{\text{out}} \cdot p_{\text{out}},
$$

where $n_{\text{in}}$, $n_{\text{cached}}$ and $n_{\text{out}}$ are the input,
cached-input and output tokens summed over every model call in the scenario,
and $p$ is the corresponding price. Output tokens include thinking tokens.

- **Gemini.** Prices are the Standard paid-tier rates. The rate for prompts
  of at most 200K tokens is applied to every call. Cached input tokens are
  those served by the API's implicit caching and are charged at the context
  caching price. The harness creates no explicit cache, so no storage price
  applies. The Gemini 3.7 Flash rates are those listed for use through
  December 31, 2026.
- **Open-weights models.** These models were served locally. They are
  priced at the lowest-priced OpenRouter provider for each model, as the
  practitioner-facing equivalent. For each model, the same provider offers
  both the lowest input price and the lowest output price. No cached input
  is recorded for local serving, so every input token is charged at the
  input price.
