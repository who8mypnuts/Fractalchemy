# Logo proposal

![the mark at several sizes, and the wordmark](logo/logo_sheet.png)

**The idea.** Fractalchemy is *fractal* + *alchemy*: an alchemist's flask whose contents are a fractal. The flask
is drawn as the alchemical sign for fire — a triangle — with a neck, in one bold, rounded indigo stroke, so it
still reads at 16 px in a task bar. Inside it sits a logarithmic spiral of circles that shrink by the golden
ratio (self-similarity, the one thing every fractal has) coloured by the app's flame gradient — ember orange
through magenta to the accent blue the interface already uses for active states. Two blue bubbles rise in
the neck: something is brewing.

**Why it works small and large.** At 16–24 px the eye gets a flask with a warm glow — a silhouette no other
fractal program has (they use flames, spirals or Mandelbrot sets alone). At 64 px and up the spiral resolves
into its circles and the gradient shows; at 256 px the golden-ratio construction is visible. There is no
text in the mark, no thin detail, and only three colours plus the ink, so it survives monochrome and
favicon sizes. The wordmark sets the mark beside the name in a demi-bold sans, `Fractal` in ink and `chemy`
in the accent blue, with a dark variant for dark backgrounds.

**Files.** `fractalchemy/widgets/logo.py` paints it at any size (`logo_pixmap(size)`, `logo_icon()`,
`wordmark_pixmap()`); the PNGs in `docs/logo/` are renders of the same code. Adopting it is one line per
window — `setWindowIcon(logo_icon())` in place of `gradient_icon()` — plus `wordmark_pixmap()` in the About
box; nothing is switched over yet, pending your verdict.

**Variations worth trying if the direction is right.** A single-colour version for print; the spiral made of
squares (Sierpinski feel) instead of circles; a round-bottom flask; the bubbles as tiny triangles echoing the
fire sign.
