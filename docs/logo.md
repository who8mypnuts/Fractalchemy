# The logo

![the mark and its alternatives](../logo/contact_sheet.png)

The mark is the application's icon (`main.py` sets it on the application, `MainWindow` on itself) and the
wordmark heads the About box. `python tools/render_logo.py` renders the main version and every alternative at
1024 px — transparent, on white and on dark — with the wordmarks and a contact sheet, into `logo/`.

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

**Files.** `fractalchemy/widgets/logo.py` paints it at any size (`logo_pixmap(size, variant=…)`, `logo_icon()`,
`wordmark_pixmap()`); the PNGs in `logo/` are renders of the same code (`tools/render_logo.py`).

**The alternatives** (`VARIANTS`): `mono` — a single-colour version for print and stamps; `squares` — the spiral
made of squares for a Sierpinski feel; `round` — a round-bottom flask; `triangles` — the bubbles as tiny
triangles echoing the fire sign. Any of them is one argument away from becoming the main mark.
