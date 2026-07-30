# Pyramidal Flow Matching — Speaker Notes

The sections follow the slide order in `presentation.qmd`. The Q&A appendix is preparation material and is not part of the spoken presentation.

## Outline

- The talk follows the paper in four parts.
- First: why video generation is expensive, and the flow-matching background.
- Second: the spatial pyramid and how one shared model is trained across its stages.
- Third: the temporal pyramid for autoregressive video generation.
- Finally: the implementation, experimental evidence, limitations, and a live demo.

## Motivation

- **Visual cue:** Compare the two trajectories from left to right: full resolution throughout versus resolution that increases over time.
- A ten-second video at 24 frames per second contains roughly 240 frames, and an iterative generator processes their latent tokens repeatedly.
- A conventional full-resolution model pays for the largest latent grid even during the earliest, mostly noisy steps.
- At that point there is little fine detail to represent, so much of this computation is redundant.
- Pyramidal Flow begins on a coarse grid and introduces resolution as structure becomes reliable.
- This is not a separate upscaling pipeline: the stages form one linked generative process handled by one shared model.

## Prior Approaches

- One option is full-resolution generation throughout. It is simple, but limits batch size, duration, or output resolution.
- Another option is a cascade: generate at low resolution, then refine with separately trained spatial or temporal super-resolution models.
- Cascades save computation, but require several objectives and checkpoints and share little knowledge across stages.
- The paper asks whether we can keep the computational advantage of a cascade while using one jointly trained model and one linked trajectory.
- **Transition:** Before changing the generation path, we need to establish the compressed space in which that path operates.

## Latent Video Generation

- **Visual cue:** Read the upper row as training and the lower row as generation; the encoder is absent from the generation path.
- The model does not operate on RGB pixels directly. A causal 3D VAE compresses video by eight in height, width, and time.
- The first latent frame is special: it represents the first video frame causally; each additional temporal latent represents roughly eight more frames.
- During training, the VAE encoder maps real videos into latent space. During generation, sampling starts from latent noise, and only the decoder is needed at the end.
- The authors trained this VAE separately from scratch on video and image data. During DiT pretraining, the VAE is frozen.
- Because the first frame is encoded without future context, an image naturally acts as the first frame of an autoregressive video.
- Everything that follows—the noise, pyramid stages, and temporal history—lives in this compressed latent space.

## Flow Matching vs. Diffusion

- Both diffusion and flow models generate iteratively from noise.
- Diffusion defines a forward noising process and learns reverse dynamics. Flow matching instead directly regresses the velocity of a chosen probability path.
- A common flow-matching choice is linear conditional interpolation between noise and data.
- These conditional paths are simple and often reduce integration difficulty, although the learned marginal trajectories are not guaranteed to be perfectly straight.
- The important freedom for this paper is that flow matching can be defined between carefully chosen distributions, not only between standard Gaussian noise and clean data.
- **Transition:** The next slide makes this conceptual distinction concrete with the actual training target and inference update.

## Flow Matching

- During training, sample real data `x₁`, noise `x₀`, and a random time `t`, then construct `xₜ = (1−t)x₀ + tx₁`.
- The target velocity is `x₁ − x₀`, learned with mean squared error.
- Training is simulation-free: it does not solve the complete ODE for every training example. The expensive DiT forward and backward passes still remain.
- During inference, begin with noise and numerically integrate the learned velocity field, here using Euler steps.
- An ODE stage itself cannot change dimensionality. Pyramid Flow therefore uses fixed-dimensional flow segments and changes the grid only through discrete transitions between them.
- **Transition:** We can now replace one noise-to-data path with three coupled flow segments at increasing resolutions.

## The Spatial Pyramid

- **Visual cue:** Follow the stage cards from left to right, but keep attention on the arrows—the transitions are where the distributions must be repaired.
- Generation is divided into quarter-, half-, and full-resolution stages.
- The coarse stage establishes global composition and motion; later stages progressively add spatial detail.
- Within each stage, both endpoints have the same tensor shape. The starting endpoint is an upsampled coarse latent with more noise; the ending endpoint is the cleaner latent at the current resolution.
- Both endpoints are derived from the same clean video and coupled with the same noise sample. This organizes the conditional trajectories and makes them straighter than independently sampled endpoints.
- One DiT handles all stages. The global timestep falls into a stage-specific window; the input resolution and positional encoding also expose the current scale, so no separate learned stage embedding is required.
- The hard part is not the flow inside a stage. It is making the distribution after a resolution jump match what the next stage saw during training.

## Attention Cost

- Quarter width and height means one sixteenth as many spatial tokens per frame.
- Pure self-attention over only those tokens is quadratic, so that component can be about `1/256` of its full-resolution equivalent.
- This is not a 256× end-to-end speedup. Video-history tokens, linear-cost transformer blocks, decoding, and the final full-resolution stage remain.
- With three uniformly sized time windows, the paper describes the spatial-pyramid computation as approaching a factor of `1/K`, roughly one third of the full-resolution path.
- The temporal pyramid addresses the remaining cost of attending to past frames.
- **Transition:** Before discussing temporal history, the intermediate outputs make the spatial progression easier to see directly.

## Stages in Practice

- **Visual cue:** Compare the same scene across all three videos rather than treating them as independent samples.
- These videos come from one local generation trajectory. I modified the output path so the normally hidden endpoint of each spatial stage is retained and decoded.
- At 160 by 96, the broad colors, composition, and motion are already visible.
- At 320 by 192, object shapes and motion become clearer.
- At 640 by 384, the final stage adds edges and high-frequency texture.
- This is an illustration of what the stages contain, not a controlled ablation proving that every semantic decision occurs in the first stage.
- Next, the important question is how the sampler moves safely between these resolutions.

## Stage Transitions

- **Visual cue:** The top row shows the three transition operations. The lower-left code implements them, while the lower-right formulas explain why the coefficients are necessary.
- After a stage finishes, nearest-neighbour upsampling duplicates each latent value into a 2 × 2 block.
- That also duplicates the noise, producing perfectly correlated values inside the block. The next stage was trained on an isotropic Gaussian start distribution, so plain upsampling creates a mismatch.
- The transition rescales the upsampled result to match the target mean and adds structured Gaussian noise to match the target covariance.
- The corrective noise has a 4 × 4 equicorrelation covariance with off-diagonal value `γ = −1/3`. The scaled upsampled signal and scaled correction jointly cancel the unwanted cross-covariance.
- Why `−1/3`: the common-direction eigenvalue is `1 + 3γ`, so positive semidefiniteness requires `γ ≥ −1/3`. Choosing the lower bound maximizes decorrelation while minimizing added noise.
- Matching the two distributions yields `eₖ₊₁ = 2sₖ/(1+sₖ)`. Because `eₖ₊₁ > sₖ`, the transition rolls the effective time slightly backward and reintroduces noise before the next flow segment.

## Pyramidal Training

- Training must reproduce the distributions encountered by the sampler.
- From one clean video, construct a latent pyramid. For each training example, uniformly sample one stage and one time within that stage's global time window.
- Couple the two endpoints using the same noise sample. Independent endpoint noise would create more intersecting conditional paths and a harder velocity field.
- Interpolate between the coupled endpoints and regress their difference with the same flow-matching MSE objective.
- A single DiT is shared across all resolutions; there is no separate generator or super-resolution model per stage.
- “End-to-end” here means all stages are jointly optimized through this shared objective and the same DiT parameters. Each update samples a stage and time directly; training does not run or backpropagate through the complete sequential inference trajectory.
- Repository detail: its interpolation ratio runs from one toward zero, so the implemented target is written as start minus end rather than end minus start.
- **Transition:** The spatial pyramid reduces the cost of generating the current unit; the next step is reducing the cost of its growing video history.

## The Temporal Pyramid

- **Visual cue:** Read the diagram from the current unit backwards in time: the farther a condition is in the past, the more aggressively it can be compressed.
- Video is generated autoregressively in latent units. In this implementation, the first unit is one frame and each later latent unit corresponds to roughly eight video frames.
- Each new unit conditions on previously generated units. Keeping the entire growing history at high resolution would recreate the original cost problem.
- The slide is a simplified view of the compression hierarchy. In the implementation, the immediately preceding unit is kept at the current stage's resolution, the next older unit is one level coarser, and all earlier units eventually use the coarsest available level.
- At the final spatial stage, that means the immediately previous unit is full resolution, the next older unit is half resolution, and the more distant history is quarter resolution.
- Training uses the same resolution pattern, but it conditions on ground-truth history with added corruption noise sampled up to strength `1/3`. Inference conditions on the model's own generated history.
- The noise makes training more tolerant to imperfect history, reducing—but not eliminating—the autoregressive train/inference gap.
- Blockwise causal attention prevents the current or future units from modifying the past condition. Interpolated temporal-pyramid position encodings keep compressed history spatially aligned.
- The trade-off is long-term drift: aggressively compressed history can lose identity or fine scene details.

## Architecture

- **Visual cue:** Start with the frozen components on the left, follow their conditions into the shared DiT, then follow the velocity prediction through the scheduler on the right.
- The central trainable generator is a shared DiT. It receives the current noisy latent, compressed history, timestep, and text embeddings, then predicts velocity.
- In the reported paper model, this is a 2B-parameter MM-DiT initialized from SD3-Medium, with frozen T5 and CLIP text encoders.
- The causal 3D VAE was trained separately from scratch, then frozen during DiT training.
- The scheduler is ordinary code, not another neural network. It selects stage timesteps, applies Euler updates, and performs the upsample-and-renoise transition.
- The paper therefore needs no learned model per resolution. Its efficiency comes from presenting the same DiT with far fewer high-resolution tokens for most of training.
- My local demo uses the repository's later miniFLUX checkpoint rather than the exact SD3-based model used for the paper's reported experiments. The pyramidal method is the same, but the base architecture differs.
- **Transition:** The architecture identifies the components; the code now shows how they interact during one sampling unit.

## The Inference Loop

- **Visual cue:** Read the code in the same order as the numbered annotations: choose a stage, repair its boundary, attach history, then integrate velocity.
- This is shortened code from the repository's core loop.
- The outer loop selects one resolution stage and its timestep interval.
- At every later stage, the latent is upsampled, rescaled, and combined with covariance-matching block noise.
- The inner loop attaches the temporal history, evaluates the shared DiT, applies classifier-free guidance, and advances the latent with an Euler step.
- My implementation change is instrumentation rather than a new sampling algorithm: I retain each stage endpoint across all autoregressive units, decode all three stage histories through the VAE, and expose them through the app.
- The model weights and intended sampling equations remain unchanged; the change makes intermediate states observable.
- Practical cue: start the first demo generation in the background now so it is ready at the end.

## Convergence Ablation

- **Visual cue:** The left side is the qualitative comparison; the FID curve on the right is the quantitative evidence for convergence speed.
- This is the paper's strongest controlled comparison: same image data, tokens per batch, hyperparameters, and model architecture; only the spatial-pyramid objective changes.
- On MS-COCO prompts, the pyramidal variant achieves almost three times the FID convergence speed.
- Important limitation: this is an early text-to-image ablation, not a direct measurement of complete video-training or inference speed.
- The temporal-pyramid ablation is mainly qualitative: under equal video-training steps, the full-sequence baseline is still far from convergence.
- **Transition:** This ablation tests whether the mechanism accelerates learning; the next table asks whether the resulting video model is competitive in quality.

## VBench Results

- **Visual cue:** Read the highlighted row horizontally: strong visual quality and motion, but noticeably weaker semantics.
- The reported DiT training phases sum to roughly 20.7 thousand A100 GPU hours and produce 5–10 second, 768p videos at 24 fps.
- On VBench, Pyramid Flow has the strongest visual-quality score in this table and very high motion smoothness. Its overall score does not beat every commercial model.
- Its main weakness is semantic alignment. The authors attribute this to coarse synthetic captions and note that they did not use prompt rewriting.
- The comparison is not controlled: systems differ in training data, model size, infrastructure, frame rate, and evaluation setup. Treat it as evidence of competitiveness, not proof that the pyramid alone causes the quality advantage.
- The controlled ablations support the efficiency mechanism more directly than this cross-model leaderboard.

## Conclusion

- The central idea is to make compute follow information: use coarse grids while uncertainty is high and reserve the largest grid for the end.
- A unified flow-matching objective lets one DiT share knowledge across spatial stages, while the temporal pyramid compresses growing autoregressive history.
- The cost is additional complexity at stage boundaries and a risk of long-term identity drift.
- Other limitations from the paper: autoregressive generation cannot perform keyframe interpolation, the training data does not teach scene transitions, evaluation focuses on relatively short prompts, and inference is not real-time.
- The final quality still depends on the VAE, base DiT, caption quality, data, and guidance—not only on the pyramid.
- **Transition:** The final slide compresses the entire paper into one principle before we see that principle in the demo.

## One path · three resolutions · one shared model

- The takeaway in one sentence: use coarse resolution while little information is available, then increase resolution as structure becomes reliable.
- Apply that idea both to the current sample in space and to its history in time.
- The result is one shared model following a piecewise trajectory across three resolutions.
- Now to the demo.

## Live Demo

- Before the talk: start the app with `uv run app.py` and keep the browser tab behind the slides.
- State clearly that the demo uses the later miniFLUX checkpoint, while the paper reports the SD3-based MM-DiT.
- Show the prompt, settings, final video, and the three decoded stage endpoints.
- Explain that these endpoints come from one trajectory: coarse generation, covariance-corrected transition, then refinement.
- If generation is still running, use the prepared outputs. If the app fails, play `assets/demo.mp4`.
- After showing the result, return verbally to the central claim: “What you just saw is the paper's idea in practice: make the global decisions cheaply, then spend full-resolution computation only when detail becomes useful.”
- End by repeating that the intermediate stages are diagnostic views of one trajectory, then invite questions.

# Q&A Preparation

These are backup answers. Do not read them during the main presentation.

### What is the novelty compared with a cascade?

Pyramid Flow still has multiple resolution stages, but it uses one DiT, one time-conditioned objective, and one linked generative trajectory. A conventional cascade trains separate base and super-resolution models, often with separate noisy generation processes.

### How can an ODE change the number of dimensions?

It cannot. Each flow segment has a fixed tensor shape. Between segments, the sampler performs a discrete upsampling and renoising transformation. The full sampler is a piecewise flow with stochastic jumps, not one globally continuous fixed-dimensional ODE.

### Is the complete sampler deterministic?

Within each stage, ODE integration is deterministic once the starting state is fixed. At stage boundaries, new corrective Gaussian noise is sampled. The complete process is therefore hybrid: deterministic flow segments connected by stochastic transitions.

### Why not simply upsample between stages?

Nearest-neighbour upsampling makes the four values in each 2 × 2 noise block identical. The next stage expects independent Gaussian noise. Rescaling fixes the mean; structured corrective noise fixes the covariance so inference matches the next stage's training distribution.

### Why is the correction correlation exactly −1/3?

For a four-variable equicorrelation matrix, the eigenvalues are `1 − γ` with multiplicity three and `1 + 3γ` in the all-ones direction. Positive semidefiniteness requires `γ ≥ −1/3`. The minimum value maximizes anticorrelation and minimizes the corrective-noise weight.

### Why couple the endpoint noise during training?

Independent endpoints create randomly oriented, intersecting conditional paths. Sharing the noise direction makes the paths more organized and often straighter, so the learned velocity field is easier to approximate. The paper illustrates this with a toy experiment.

### Is the method really 256× faster?

No. `1/256` applies only to the quadratic attention term for quarter-resolution spatial tokens. End-to-end computation also includes the full-resolution stage, temporal history, MLPs, VAE work, and overhead. The controlled spatial ablation reports almost 3× faster FID convergence.

### Why does the temporal pyramid preserve useful history?

Distant frames usually provide global identity and scene state, while recent frames carry detailed motion continuity. The model retains newer history at a higher resolution and compresses older history more aggressively. The assumption is useful but imperfect, which explains occasional long-term drift.

### Does corrupting history remove exposure bias?

No. Training still uses ground-truth history, while inference uses generated history. Adding corruption up to strength `1/3` makes the model more robust to errors and reduces the gap, but does not remove it.

### Why use blockwise causal attention instead of bidirectional attention?

The autoregressive past should behave as a fixed condition. With bidirectional attention, representations of past frames can be influenced by the unit currently being generated. The paper's ablation found worse subject consistency with bidirectional attention.

### What exactly was trained?

The authors separately trained the causal 3D VAE, then froze it for DiT training. The reported generator is a 2B MM-DiT initialized from SD3-Medium and trained in image, low-resolution-video, and high-resolution-video phases. T5 and CLIP provide text conditioning. The scheduler and transition equations are not learned.

### Does the reported 20.7k A100 GPU hours include everything?

It is the sum of the three reported DiT training phases: about 1,536, 11,520, and 7,680 A100 GPU hours. The paper does not clearly include separate VAE training, caption generation, or data preparation in that headline number.

### How convincing are the experiments?

The spatial ablation is the cleanest evidence because architecture, data, tokens per batch, and hyperparameters are controlled. The VBench table demonstrates competitiveness but cannot isolate the pyramid because the compared systems differ substantially. The temporal ablation shows a large qualitative convergence gap, but offers less quantitative evidence.

### What are the main limitations?

Autoregressive errors can accumulate; compressed history can cause identity drift; keyframe interpolation is unsupported; scene transitions were filtered out of the training data; prompt evaluation is relatively short; and inference remains far from real time.

### What did I personally implement?

I changed the inference output path to retain the endpoint of every spatial stage across all autoregressive units, decode each complete stage history, and expose the resulting videos in the app. I did not train new weights or introduce a new generation algorithm. The outputs are diagnostic visualizations of the existing trajectory, not a controlled ablation.

### Could a diffusion model use a similar pyramid?

Yes in principle. Dimensionality-varying and cascaded diffusion processes already exist. Flow matching is especially convenient here because it directly defines simulation-free objectives between chosen endpoint distributions and makes the piecewise construction simple. The paper demonstrates one effective formulation rather than proving that diffusion cannot use pyramids.

### Why did the authors choose exactly three stages?

Three stages—quarter, half, and full resolution—provide a practical balance between token savings and transition complexity. The paper uses three stages in all reported experiments, but does not establish that three or uniformly sized time windows are theoretically optimal.

### Why use nearest-neighbour rather than bilinear upsampling?

The paper permits nearest-neighbour or bilinear resampling, but the exact block-covariance derivation is simplest for nearest-neighbour upsampling because every source value is copied into a 2 × 2 block. The repository implementation uses nearest-neighbour at inference and applies the corresponding structured correction noise. A different upsampler would induce a different covariance that must be matched.

### Why does the repository store positive `gamma = 1/3` when the paper describes correlation `−1/3`?

The implementation stores the positive magnitude. In `sample_block_noise()`, it constructs the covariance so the off-diagonal entries are `−gamma`. Therefore a configured value of `1/3` produces the paper's negative correlation of `−1/3`.

### Do later stages recover details that were discarded at low resolution?

No. The discarded high-frequency information is not recoverable from the coarse latent. Later stages generate plausible details conditioned on the coarse structure, text prompt, learned data distribution, and newly introduced noise. “Decompression” here means generative refinement, not lossless reconstruction.

### What exactly does “end-to-end” mean if training samples only one stage at a time?

All stages share one DiT and one unified objective, so training examples from every stage update the same parameters. However, each optimization step samples a stage and timestep directly. The method does not differentiate through the complete multi-stage inference sampler or through every stochastic jump.

## Primary references

- Jin et al., [“Pyramidal Flow Matching for Efficient Video Generative Modeling”](https://arxiv.org/html/2410.05954v2), ICLR 2025.
- [Official Pyramid Flow repository](https://github.com/jy0205/Pyramid-Flow).
