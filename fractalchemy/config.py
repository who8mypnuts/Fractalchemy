"""Application-wide tunables. Adjust here rather than hunting through modules."""

APP_NAME = "Fractalchemy"
APP_VERSION = "0.1"

# --- Import behaviour -------------------------------------------------------
# Max per-channel deviation (0-255) allowed when dropping redundant stops on
# import. 0 keeps every stop; larger values yield fewer, more draggable nodes.
IMPORT_SIMPLIFY_TOLERANCE = 10

# --- Image extraction -------------------------------------------------------
IMAGE_COLOR_COUNT = 16          # number of nodes extracted from an image
IMAGE_ANALYSIS_SIZE = 256       # images are downscaled to this max edge first
IMAGE_ORDERING = "path"         # "path" | "luminance" | "hue"  (see imaging/ordering.py)

# --- Format specifics -------------------------------------------------------
FLAME_PALETTE_SIZE = 256        # Apophysis/flam3 palettes are always 256 entries
FLAME_COLORS_PER_LINE = 8
UGR_MAX_INDEX = 399             # Ultra Fractal gradients span index 0..399

# --- Appearance ---------------------------------------------------------------
HIGHLIGHT_COLOR = "#1e88e5"     # the accent used for active states (toolbar glyphs, the editor's mode buttons)

# --- Gradient editor appearance ------------------------------------------------
EDITOR_MARGIN = 12              # px either side so edge nodes are fully visible
STRIP_MIN_HEIGHT = 80
NODE_BAR_HEIGHT = 26
NODE_RADIUS = 6
NODE_HIT_RADIUS = 9

# --- Preview rendering --------------------------------------------------------
PREVIEW_PASSES = 6              # progressive passes per viewport render
PREVIEW_QUALITY = 8.0           # samples per pixel over all passes (Apophysis "quality")
PREVIEW_POINTS = 1 << 17        # point population iterated in parallel (GPU: per draw; CPU: per thread batch)
PREVIEW_FUSE = 20               # warm-up iterations before plotting
PREVIEW_OVERSAMPLE = 2          # supersampled buckets per pixel side (Apophysis "oversample"; 1 = none)
PREVIEW_FILTER = 0.5            # spatial filter radius in output pixels (Apophysis "filter radius")
MAX_OVERSAMPLE = 4
MAX_BUCKETS = 24_000_000        # histogram buckets a preview may use (≈ 2 × 16 bytes each on the GPU); oversample is lowered to fit
MAX_FILTER_RADIUS = 2.0
PREVIEW_REFINE_TO = 500.0       # keep refining the idle preview (doubling passes) up to this quality; 0 = stop at PREVIEW_QUALITY
MAX_REFINE_QUALITY = 20000.0
ZOOM_DENSITY_MAX = 64.0         # Apophysis renders quality · 4^zoom samples per pixel; capped here (zoom 3) for interactivity
INTERACTIVE_SCALE = 0.5         # viewport resolution factor while dragging / zooming
INTERACTION_SETTLE_MS = 250     # after the last interaction, re-render at full resolution
EDIT_RENDER_DELAY_MS = 1000     # the main viewport re-renders this long after the last Transform Editor change

# --- Transform Editor ---------------------------------------------------------
# (the quality levels of the live previews — Low / Medium / High — are in ui/live_preview.py)
EDITOR_PREVIEW_POINTS = 1 << 14  # a small population: the warm-up (fuse) is most of a tiny render's cost
EDITOR_PREVIEW_FUSE = 12
EDITOR_PREVIEW_THROTTLE_MS = 80    # at most one preview render per this interval (and one in flight) while dragging
EDITOR_PREVIEW_SIZE = (380, 240)   # the editor's preview box (the image is letterboxed into it)
THUMBNAIL_SIZE = (120, 75)      # fractal library thumbnails
THUMBNAIL_QUALITY = 3.0
THUMBNAIL_PASSES = 1
CPU_RENDER_THREADS = 0          # 0 = use every core
