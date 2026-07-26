---
theme: default
title: Pyramidal Flow Matching
info: |
  A 20-minute introduction to Pyramidal Flow Matching for efficient video generation.
author: Marcel Sigl
class: text-left
drawings:
  persist: false
transition: fade-out
comark: true
duration: 20min
---

<div class="cover-shell">
  <div class="eyebrow">ADVANCED MACHINE LEARNING · ICLR 2025</div>
  <h1>Pyramidal<br/><span>Flow Matching</span></h1>
  <p class="cover-subtitle">Generate the structure cheaply.<br/>Spend full resolution only on the details.</p>
  <div class="cover-meta">
    <span>Marcel Sigl</span>
    <span>Efficient video generative modeling</span>
  </div>
</div>

<!--
Open with the central question: how can we generate high-resolution video without paying the full-resolution cost at every denoising step?

The paper's answer is a change of representation along the generative trajectory. Early, uncertain states are modeled at low resolution; resolution is added only as the signal becomes informative. The same idea is extended over time by compressing older context.

This talk builds the method from flow matching, then connects it to the implementation in this repository. Aim for about 40 seconds.
-->

---

# Video generation multiplies every expensive dimension

<div class="metric-row mt-10">
  <div class="metric-block">
    <div class="metric-value">1280 × 768</div>
    <div class="metric-label">spatial detail per frame</div>
  </div>
  <div class="metric-operator">×</div>
  <div class="metric-block">
    <div class="metric-value">24 fps</div>
    <div class="metric-label">temporal density</div>
  </div>
  <div class="metric-operator">×</div>
  <div class="metric-block">
    <div class="metric-value">10 s</div>
    <div class="metric-label">240 generated frames</div>
  </div>
</div>

<div class="statement mt-12">
  A video model must learn appearance, motion, and prompt alignment across a vast spatiotemporal token grid.
</div>

<div class="bottom-line">The costly default: process the entire latent video at full resolution throughout the generation trajectory.</div>

<!--
Start with the scale of the object being modeled. A ten-second 768p clip at 24 frames per second contains 240 frames. In practice the model works in a compressed VAE latent, but the token count is still large and attention or transformer blocks repeatedly process it.

The important point is multiplicative complexity: more pixels, more frames, more denoising evaluations, and model depth all compound. Conventional systems often manage this with cascades or multiple stages trained separately. Those approaches reduce cost, but knowledge sharing between stages is limited.

Pyramidal Flow Matching asks whether every point on the trajectory actually needs the same representation. About 70 seconds.
-->

---

# Early generative states contain little high-frequency information

<img class="paper-figure mt-6" src="../../Pyramid-Flow/assets/motivation.jpg" alt="Comparison of full-resolution video diffusion and pyramidal flow matching" />

<div class="two-claims mt-5">
  <div><b>Full-resolution diffusion</b><br/><span>pays for fine spatial grids even when the latent is mostly noise.</span></div>
  <div class="accent-claim"><b>Pyramidal flow</b><br/><span>increases resolution as semantic structure emerges.</span></div>
</div>

<div class="source">Source: Jin et al., “Pyramidal Flow Matching for Efficient Video Generative Modeling,” Fig. 1.</div>

<!--
This is the paper's key observation. On the left, every frame exists at the final resolution for the entire noisy-to-clean process. Yet the early states are dominated by noise and do not contain meaningful edges, textures, or fine geometry.

On the right, the model begins on a coarse grid. It first commits to global composition and motion, then moves to a larger grid, and only the final stage uses full resolution. The blue diagonal links also hint at the temporal pyramid: old frames can remain compressed while the current frame or clip receives the expensive treatment.

The method is not simply post-hoc super-resolution. It constructs one continuous generative path across resolutions. About 80 seconds.
-->

---

# Flow matching learns a velocity from noise to data

<div class="equation-card mt-7">
  <div class="equation-label">Linear probability path</div>
  $$x_t = (1-t)x_0 + tx_1, \qquad x_0\sim\mathcal{N}(0,I),\; x_1\sim q_{\text{data}}$$
</div>

<div class="flow-row mt-7">
  <div class="flow-node noise-node">noise<br/><span>$x_0$</span></div>
  <div class="flow-track">
    <div class="flow-arrow">→</div>
    <div class="flow-caption">integrate $dot{x}_t=v_\theta(x_t,t)$</div>
  </div>
  <div class="flow-node data-node">video latent<br/><span>$x_1$</span></div>
</div>

<div class="equation-card compact mt-7">
  <div class="equation-label">Simulation-free regression objective</div>
  $$\mathcal{L}_{\mathrm{FM}} = \mathbb{E}_{t,x_0,x_1}\left[\left\|v_\theta(x_t,t) - (x_1-x_0)\right\|_2^2\right]$$
</div>

<div class="bottom-line">Crucial flexibility: the endpoints do not have to be “noise” and “full-resolution data.”</div>

<!--
Flow matching gives the flexibility the pyramid needs. Choose a path from a simple source distribution to the data distribution. For the familiar linear path, x at time t is an interpolation between Gaussian noise and a data sample. The target velocity is simply x1 minus x0.

The neural network is trained by regression, without simulating the ODE during training. At inference, we start with noise and integrate the learned velocity field.

The decisive property is endpoint flexibility. A flow can connect other distributions too. Pyramidal Flow Matching uses that freedom to connect noisy representations at different spatial scales instead of forcing one full-resolution path. About 95 seconds.
-->

---

# One trajectory becomes a sequence of resolution stages

<div class="stage-rail mt-10">
  <div class="stage-card stage-low">
    <div class="stage-kicker">STAGE 1</div>
    <div class="stage-scale">¼ resolution</div>
    <div class="stage-purpose">composition<br/>and coarse motion</div>
  </div>
  <div class="stage-join">upsample<br/><span>+ re-noise</span></div>
  <div class="stage-card stage-mid">
    <div class="stage-kicker">STAGE 2</div>
    <div class="stage-scale">½ resolution</div>
    <div class="stage-purpose">shapes<br/>and scene layout</div>
  </div>
  <div class="stage-join">upsample<br/><span>+ re-noise</span></div>
  <div class="stage-card stage-high">
    <div class="stage-kicker">STAGE 3</div>
    <div class="stage-scale">full resolution</div>
    <div class="stage-purpose">texture<br/>and fine detail</div>
  </div>
</div>

<div class="statement mt-12">
  The same DiT is trained across all stages, so the pyramid shares parameters and learns end to end.
</div>

<div class="bottom-line">Unlike a cascade, the stages are pieces of one probability path—not independently trained models.</div>

<!--
The paper divides the original path into K intervals. Each interval operates at a different resolution. A typical three-stage implementation uses quarter, half, and full spatial resolution.

The first stage generates a low-resolution latent from noise. Its endpoint is upsampled and corrected before becoming the start distribution of the next stage. This repeats until the final full-resolution latent is produced.

The major architectural advantage over a cascade is unification: one Diffusion Transformer is conditioned on the stage or time and trained across all resolutions. The stages share features and can be optimized jointly. About 85 seconds.
-->

---

# The pyramid progressively turns uncertainty into detail

<div class="video-stage-grid mt-6">
  <div>
    <video src="../../Pyramid-Flow/pyramid_vis_stage_0.mp4" autoplay muted loop playsinline></video>
    <h3>160 × 96</h3>
    <p>global color and layout</p>
  </div>
  <div>
    <video src="../../Pyramid-Flow/pyramid_vis_stage_1.mp4" autoplay muted loop playsinline></video>
    <h3>320 × 192</h3>
    <p>objects and motion stabilize</p>
  </div>
  <div>
    <video src="../../Pyramid-Flow/pyramid_vis_stage_2.mp4" autoplay muted loop playsinline></video>
    <h3>640 × 384</h3>
    <p>high-frequency detail appears</p>
  </div>
</div>

<div class="bottom-line">These local samples expose the actual three-stage inference path used by this project.</div>

<!--
Let the three clips run. They show the same generated scene at the outputs of the three spatial stages in the local implementation.

At 160 by 96, the clip is already deciding the scene's dominant palette, perspective, and rough motion. At 320 by 192, pedestrians, stalls, and the street become recognizable. The final 640 by 384 stage spends computation on texture, edges, faces, and small motion.

This makes the allocation intuitive: high-resolution compute is most valuable late, when there is actually high-frequency information to resolve. About 75 seconds.
-->

---

# Coupled training keeps the stagewise path coherent

<div class="split-layout mt-5">
  <div>
    <div class="numbered-point"><span>1</span><p>Downsample each clean video latent into a spatial pyramid.</p></div>
    <div class="numbered-point"><span>2</span><p>Sample a stage and a time within that stage.</p></div>
    <div class="numbered-point"><span>3</span><p>Construct start and end points with <b>coupled noise</b>.</p></div>
    <div class="numbered-point"><span>4</span><p>Regress the usual rectified-flow velocity.</p></div>
  </div>
  <div class="equation-stack">
    <div class="equation-mini">$$x_t = r_t x_{\text{start}} + (1-r_t)x_{\text{end}}$$</div>
    <div class="equation-mini accent-eq">$$u_t = x_{\text{end}} - x_{\text{start}}$$</div>
    <p>Shared noise ties adjacent stages to compatible trajectories and reduces crossings.</p>
  </div>
</div>

<div class="bottom-line">The learning rule stays simple; the innovation lies in how each stage's endpoint distributions are constructed.</div>

<!--
Training can still use the standard flow-matching loss. The implementation first encodes a video with the VAE, constructs low-, mid-, and high-resolution latents, and samples examples from the different pyramid stages.

Within the selected stage it linearly interpolates between a stage-specific start and end point. The target remains the difference between those endpoints.

The subtle part is coupling. If each stage used independent noise, the piecewise trajectories could point in unrelated directions and cross. Coupling the noise makes adjacent stage endpoints statistically compatible and encourages a straighter overall path. About 90 seconds.
-->

---

# Upsampling alone breaks the noise statistics

<div class="jump-grid mt-6">
  <div class="jump-cell">
    <div class="jump-title">1 · finish a stage</div>
    <p>Integrate the learned flow on the current grid.</p>
  </div>
  <div class="jump-arrow">→</div>
  <div class="jump-cell">
    <div class="jump-title">2 · upsample</div>
    <p>Copying values creates blockwise correlation.</p>
  </div>
  <div class="jump-arrow">→</div>
  <div class="jump-cell accent-cell">
    <div class="jump-title">3 · re-noise</div>
    <p>Correct the covariance before continuing.</p>
  </div>
</div>

<div class="equation-card mt-9">
  $$\hat{x}_{s_k}=\frac{1+s_k}{2}\,\mathrm{Up}(\hat{x}_{e_{k+1}})+\frac{\sqrt{3}(1-s_k)}{2}\,n'$$
</div>

<div class="bottom-line">Renoising is what turns separate resolution intervals into a continuous distributional path.</div>

<!--
Inference introduces a distribution-matching problem at every resolution jump. Nearest-neighbor upsampling repeats each value into a block, so the resulting noise is correlated. The next stage, however, expects a particular marginal variance and covariance.

The paper derives a linear rescaling plus corrective Gaussian noise. The displayed rule is the chosen special case that maximally preserves signal while decorrelating blocks. The stage time is rolled back slightly, then integration continues.

This is more than a cosmetic anti-blocking trick: without matching the start distribution of the next stage, a model trained on one distribution would be evaluated on another. About 90 seconds.
-->

---

# A temporal pyramid compresses the past, not the future

<div class="timeline mt-9">
  <div class="history history-old">
    <span>older history</span>
    <div class="history-grid tiny"></div>
    <div class="history-grid tiny"></div>
    <div class="history-grid tiny"></div>
  </div>
  <div class="history history-mid">
    <span>recent history</span>
    <div class="history-grid medium"></div>
    <div class="history-grid medium"></div>
  </div>
  <div class="history history-now">
    <span>current unit</span>
    <div class="history-grid large"></div>
  </div>
</div>

<div class="three-points mt-10">
  <div><b>Autoregressive</b><span>generate the next latent frame unit</span></div>
  <div><b>Causal</b><span>attend only to already generated content</span></div>
  <div><b>Compressed context</b><span>keep distant history on coarser grids</span></div>
</div>

<div class="bottom-line">The model preserves long context without repeatedly processing every past frame at full resolution.</div>

<!--
The spatial pyramid reduces the cost of the current denoising path. The temporal pyramid addresses a second source of redundancy: the history used for autoregressive generation.

The model generates a small unit of new frames while conditioning on earlier units. Recent history remains relatively detailed because it matters most for continuity. Older history is represented at lower spatial resolution. Blockwise causal attention ensures the model cannot look into future units.

This is a pragmatic compression hypothesis: distant frames are valuable for global identity and scene state, but do not always require their original high-frequency detail. About 90 seconds.
-->

---

# A single model connects text, space, and time

<div class="system-grid mt-8">
  <div class="system-input">
    <div class="sys-icon">T</div>
    <b>Text encoder</b>
    <span>prompt embeddings</span>
  </div>
  <div class="system-input">
    <div class="sys-icon">V</div>
    <b>Causal video VAE</b>
    <span>compact video latents</span>
  </div>
  <div class="system-core">
    <div class="core-label">ONE SHARED NETWORK</div>
    <h2>Diffusion Transformer</h2>
    <p>stage-aware flow prediction<br/>with blockwise causal attention</p>
  </div>
  <div class="system-output">
    <b>Pyramid scheduler</b>
    <span>solve → upsample → re-noise</span>
  </div>
</div>

<div class="bottom-line">The efficiency gain comes from fewer expensive tokens—not from shrinking the central model at each stage.</div>

<!--
At the system level, the method remains recognizable. A text encoder supplies prompt conditioning. A causal 3D VAE maps video into and out of latent space. The central DiT predicts the flow velocity.

What changes is the structure of its inputs and schedule. The same transformer receives pyramid-stage latents, time information, text conditioning, and compressed past conditions. A specialized Euler scheduler divides the time path among stages and handles the transitions.

This distinction matters: the proposal is primarily an allocation strategy for tokens and compute, not a collection of tiny independent networks. About 75 seconds.
-->

---

# The repository mirrors the paper's four moving parts

<div class="code-map mt-6">
  <div>
    <code>get_pyramid_latent()</code>
    <p>builds low → high spatial VAE latents</p>
  </div>
  <div>
    <code>add_pyramid_noise_with_temporal_pyramid()</code>
    <p>samples stage paths and compressed history</p>
  </div>
  <div>
    <code>PyramidFlowMatchEulerDiscreteScheduler</code>
    <p>allocates timesteps and sigmas per stage</p>
  </div>
  <div>
    <code>generate_one_unit()</code>
    <p>integrates each stage, upsamples, and re-noises</p>
  </div>
</div>

<div class="repo-path mt-8">Pyramid-Flow/pyramid_dit/pyramid_dit_for_video_gen_pipeline.py</div>
<div class="repo-path">Pyramid-Flow/diffusion_schedulers/scheduling_flow_matching.py</div>

<!--
This repository closely follows the paper's conceptual decomposition. get_pyramid_latent builds the multiscale VAE representations. add_pyramid_noise_with_temporal_pyramid constructs the training examples, including the stage-dependent path and the progressively compressed conditioning history.

The scheduler stores separate time and sigma ranges per stage. During inference, generate_one_unit loops from low to high resolution. At each jump it upsamples the latent, adds block-structured corrective noise, and then resumes Euler integration.

These are useful anchors for anyone continuing the project: they are the locations where changes to the number of stages, scheduling, temporal context, or transition rule are expressed. About 75 seconds.
-->

---

# Spending tokens late makes ambitious video training feasible

<div class="hero-metrics mt-10">
  <div><b>20.7k</b><span>A100 GPU training hours</span></div>
  <div><b>768p</b><span>reported output resolution</span></div>
  <div><b>24 fps</b><span>temporal output rate</span></div>
  <div><b>5–10 s</b><span>reported clip duration</span></div>
</div>

<div class="statement mt-12">
  Only the final spatial stage uses full-resolution tokens, while the temporal pyramid reduces the cost of conditioning on history.
</div>

<div class="source">Reported by Jin et al. for the paper model trained on public data; hardware hours are not directly comparable across implementations.</div>

<!--
The payoff is the scale the authors reached with a comparatively modest training budget for video generation: 20.7 thousand A100 GPU hours, with reported generation at 768p and 24 frames per second for clips from five up to ten seconds.

These numbers should be interpreted carefully. GPU hours depend on model, software, utilization, and data pipeline, so they are not a universal efficiency metric. The stronger causal evidence comes from the paper's controlled ablations: with equal resources, the spatial pyramid converged faster than standard flow matching, and the temporal-pyramid variant learned coherent motion while the full-sequence baseline lagged.

The general mechanism is still clear: reduce the number of expensive full-resolution tokens seen during most of training. About 80 seconds.
-->

---

# Quality remains competitive despite public-data training

<img class="results-table mt-5" src="../../Pyramid-Flow/assets/vbench.jpg" alt="VBench comparison table from the Pyramid Flow paper" />

<div class="result-callouts mt-5">
  <div><b>84.74</b><span>quality score</span></div>
  <div><b>99.12</b><span>motion smoothness</span></div>
  <div><b>81.72</b><span>total score</span></div>
</div>

<div class="source">Paper-reported VBench results. Comparisons mix public and non-public training data and should be read as benchmark evidence, not a controlled systems study.</div>

<!--
Efficiency matters only if quality survives. On the paper's VBench table, Pyramid Flow reports the best quality score among the listed systems and very strong motion smoothness. Its total score is competitive with commercial models and leads the listed public-data systems.

Avoid overclaiming. This table is not an apples-to-apples training comparison: systems differ in data, parameter count, infrastructure, and generation setup. Also, VBench decomposes quality into imperfect automatic metrics.

Still, combined with the ablations and qualitative samples, the evidence supports the narrower claim that the pyramid does not merely trade away all visual quality for speed. About 80 seconds.
-->

---

# Demo: watch coarse structure become a finished clip

<div class="demo-layout mt-5">
  <video src="../../Pyramid-Flow/8c72e467-bfa6-4abd-bdad-95baf02114e6_text_to_video_sample.mp4" autoplay muted loop controls playsinline></video>
  <div>
    <div class="prompt-label">PROMPT EXCERPT</div>
    <blockquote>“Beautiful, snowy city street … people shopping at nearby stalls”</blockquote>
    <div class="demo-checks">
      <p><span>01</span> Is the global scene stable?</p>
      <p><span>02</span> Does motion remain coherent?</p>
      <p><span>03</span> Where do fine details fail?</p>
    </div>
  </div>
</div>

<div class="bottom-line">The local stage videos on slide 6 and this final sample make the coarse-to-fine allocation directly observable.</div>

<!--
Use roughly two minutes here. First let the final clip play and ask the audience to track scene identity, pedestrian motion, and small details. The overall snowy market scene stays coherent; local faces and hands are more fragile, which is common in this generation regime.

If time allows, briefly jump back to slide 6 or mention the stage recordings: the final clip did not emerge at full resolution from the first step. Composition was established on a 160 by 96 latent, refined at 320 by 192, and completed at 640 by 384.

This is also a useful reminder that efficiency and capability are different claims. The method reallocates compute effectively, but it does not solve all semantic and long-horizon consistency problems.
-->

---

# The method trades flexibility for a strong efficiency prior

<div class="tradeoff-grid mt-7">
  <div class="strengths">
    <h3>What the pyramid gets right</h3>
    <ul>
      <li>Compute follows information content.</li>
      <li>One DiT shares knowledge across scales.</li>
      <li>Spatial and temporal savings compound.</li>
      <li>Text-to-video and image-to-video fit naturally.</li>
    </ul>
  </div>
  <div class="limits">
    <h3>What remains constrained</h3>
    <ul>
      <li>Autoregressive generation only; no keyframe interpolation.</li>
      <li>Compressed history can cause subtle long-term inconsistency.</li>
      <li>Stage transitions require carefully matched noise statistics.</li>
      <li>Quality still depends heavily on data and the base DiT.</li>
    </ul>
  </div>
</div>

<div class="closing-thesis mt-9">The lasting idea: <b>match representation fidelity to uncertainty along the generative path.</b></div>

<div class="source"><a href="https://arxiv.org/abs/2410.05954">Paper</a> · <a href="https://github.com/jy0205/Pyramid-Flow">Code</a> · <a href="https://pyramid-flow.github.io/">Project page and videos</a></div>

<!--
Close by balancing the method. Its strengths follow from a coherent principle: allocate resolution where information exists, share one model across scales, and compress temporal history according to recency.

The limitations are equally structural. The temporal design is autoregressive, so it cannot natively perform bidirectional video interpolation. Compressing older context may introduce long-term subject drift. The stage jumps also add mathematical and implementation complexity.

The broader takeaway is not just “use three resolutions.” It is to match representation fidelity to uncertainty. When the latent is mostly noise or the context is distant, a coarse representation can be sufficient. Spend full fidelity only when the model can use it. About 80 seconds, then open discussion.
-->
