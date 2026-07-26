# Pyramidal Flow Matching presentation

The primary implementation is now a Quarto/reveal.js deck. It provides a general, approximately 20-minute introduction to Pyramidal Flow Matching and connects the paper's method to the implementation in `Pyramid-Flow/`.

## Quarto presentation

Install [Quarto](https://quarto.org/docs/download/), then run:

```bash
cd quarto
quarto preview presentation.qmd
```

Build the standalone presentation with:

```bash
quarto render presentation.qmd --output-dir _output/main
```

Open `_output/main/presentation.html` to present. Press `S` for speaker view and `O` for the slide overview. The deck keeps all media under `quarto/assets/`, so it can run locally without reaching outside the presentation directory.

The separate presenter companion contains bullet-point talking cues for every main slide, plus live-demo preparation:

```bash
quarto preview talking-points.qmd
```

To build both standalone decks:

```bash
quarto render presentation.qmd --output-dir _output/main
quarto render talking-points.qmd --output-dir _output/talking-points
```

## Slidev fallback

The previous Slidev implementation is preserved at `slides.md`:

```bash
pnpm install
pnpm run dev
```

The Quarto deck is the recommended version going forward.
