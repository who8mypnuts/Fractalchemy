"""Application-wide tunables. Adjust here rather than hunting through modules."""

APP_NAME = "HueClid"

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

# --- Editor appearance ------------------------------------------------------
EDITOR_MARGIN = 12              # px either side so edge nodes are fully visible
STRIP_MIN_HEIGHT = 80
NODE_BAR_HEIGHT = 26
NODE_RADIUS = 6
NODE_HIT_RADIUS = 9
