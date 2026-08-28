import styles from "./page.module.css";

export function RelatedWork() {
  return (
    <section className={styles.relatedWork} aria-labelledby="related-work-heading">
      <header>
        <p className={styles.kicker}>Context / prior art</p>
        <h2 id="related-work-heading">Related work</h2>
      </header>

      <div className={styles.relatedWorkCopy}>
        <p>
          <a href="https://huggingface.co/MiniMaxAI/MiniMax-H3">MiniMax H3</a> was
          trained with native sparse attention, although its initial open release exposed
          full-attention inference. Contemporary work has explored training-free and learned
          sparse attention for video diffusion through systems including{" "}
          <a href="https://arxiv.org/abs/2607.24027">Sol-Attn</a>,{" "}
          <a href="https://arxiv.org/abs/2505.21036">RainFusion</a>,{" "}
          <a href="https://arxiv.org/abs/2604.12219">PASA</a>, and{" "}
          <a href="https://arxiv.org/abs/2509.24006">SLA</a>.
        </p>

        <p>
          H3-specific community implementations have also introduced timestep-dependent
          sparsity. <a href="https://github.com/Saganaki22/ComfyUI-sol-attn">Scheduled H3
          Sol-Attn</a> ramps attention density through sampling; vLLM-Omni&apos;s{" "}
          <a href="https://github.com/vllm-project/vllm-omni/pull/5851">Sol-Attn study</a>
          evaluates leading dense-step guards; and its{" "}
          <a href="https://github.com/vllm-project/vllm-omni/pull/6037">RainFusion tail
          fallback</a> adds an explicit final dense window. ComfyUI implementations from{" "}
          <a href="https://github.com/PlagueKind/ComfyUI-PlagueKind-Nodes/tree/0e289348269dfba610520b8c0ca0d75c598239a2/ComfyUI-H3-SLA-Attention">
            PlagueKind
          </a> and <a href="https://github.com/wjie98/comfyui-turing-utils">Turing Utils</a>
          expose related H3 sparse-attention and dense-guard controls.
        </p>

        <p>
          Recent H3 results from{" "}
          <a href="https://www.lmsys.org/blog/2026-08-27-minimax-h3-h200">LMSYS, SGLang,
          NVIDIA, and Ant Group</a> further quantify the speed-similarity tradeoff, while{" "}
          <a href="https://github.com/loading-awesome/MiniMax-H3-Swift/blob/main/docs/PERFORMANCE_GUIDE.md">
            H3-Swift&apos;s negative Sol-Attn findings
          </a> document the risk of temporal pulsing and flicker. NVIDIA&apos;s{" "}
          <a href="https://nvlabs.github.io/Sana/Sol-Engine/H3-Super-Acceleration/">H3 Super
          Acceleration</a> explores a separate H3-draft-to-LTX-refinement pipeline.
        </p>

        <p className={styles.relatedWorkContribution}>
          This study adds a controlled, reproducible H3 Turbo ablation across every integer
          sparse-to-dense handoff at fixed 4-, 6-, 8-, and 12-NFE budgets, using matched inputs
          and publishing measured wall times and the complete output set for direct comparison.
        </p>
      </div>
    </section>
  );
}
