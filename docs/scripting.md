# Fractalchemy scripting guide

Scripts are **Python**. The names below are available without any import; everything else is ordinary
Python (loops, functions, `math`, `random`, list comprehensions …). A script works on a *copy* of the
fractal shown in the main window; when it finishes, the result replaces it as one undo step (*Revert
flame* on the toolbar goes back too). Press **Ctrl+Enter** or **F9** (or ▶) to run.

## 1. The basics

```python
# Rotate every transform by a random angle
for t in transforms:
    t.rotate(random(-30, 30))
print('rotated', len(transforms), 'transforms')
```

* `flame` — the fractal (name, raw data)
* `transforms` — the transforms; `transform` is the *active* one
* `camera`, `gradient`, `xaos`, `coloring` — the view, the palette, the chaos matrix, the tone mapping
* `print()` — writes to the output panel under the editor

## 2. Transforms

```python
t = add_transform()                      # a new transform: linear 1, weight 0.5; it is now `transform`
t.variations['linear'] = 0               # remove linear …
t.variations['julian'] = 1               # … add julian (parameters get their defaults)
t.params['julian_power'] = 5
t.set_affine(0.5, 0, 0, 0.5, 0.3, 0)     # a b c d e f:  x' = a·x + c·y + e,  y' = b·x + d·y + f
t.rotate(30).scale(0.8).translate(0.2, 0)
t.weight = 0.75; t.color = 0.3; t.color_speed = 0.5; t.opacity = 1
t.post.a = 1.2                           # post transform
u = add_transform(weight=1, color=0.6, variations={'spherical': 0.7, 'linear': 0.3}, a=0.6, d=0.6)
remove_transform(0)                      # by index or object
set_final_transform(variations={'bubble': 1})   # set_final_transform(None) removes it
```

Every loaded formula can be used — built-ins, plugins and your own (*Help ▸ Formulas…*). Type
`t.variations['` and press Tab to pick from the list.

## 3. Colours and the gradient

```python
gradient.random()                                    # Gradient Library: Reroll
gradient.set_stops([(0, '#000020'), (0.5, (255, 120, 0)), (1, '#ffffff')])
gradient.hue_shift(30).adjust(saturation=20)
gradient.load('~/gradients/sunsets.ugr', 2)         # any file the Gradient Library reads
for i, t in enumerate(transforms):                   # spread the colours along the palette
    t.color = i / max(1, len(transforms) - 1)
coloring.brightness = 5; coloring.gamma = 3.5; coloring.background = '#101020'
```

## 4. Chaos / xaos

`xaos.set(a, b, weight)` controls how likely transform *b* follows transform *a* (0 = never, 1 = normal).

```python
xaos.reset()
xaos.chain()                     # 0 → 1 → 2 → … → 0
xaos.set(0, 0, 0)                # transform 0 never repeats itself
print(xaos)
```

## 5. Camera

```python
camera.x, camera.y = 0, 0.2
camera.scale = 180; camera.zoom = 0.5; camera.rotate = 15
camera.zoom_by(2); camera.rotate_by(90); camera.pan(0.1, 0)
camera.fit()                     # frame the attractor
camera.pitch = 30; camera.perspective = 0.2      # the 3D camera (degrees)
camera.set_size(1920, 1080)
```

## 6. Interaction and animation

```python
n = input_number('How many copies?', 4)
if n is None:
    stop()
if not confirm('Replace the gradient too?'):
    print('keeping the gradient')
for i in range(20):              # a preview animation
    camera.rotate_by(3)
    update()                     # push the flame to the main window and render
    sleep(0.1)
```

## 7. Script metadata

Comment lines at the top are shown in the *Info* tab and name the script when it is saved as a template:

```python
# @name Random rotate
# @author You
# @description Rotates every transform by a random angle.
```

## 8. Tips

* **Tab** completes names; **Ctrl+Space** opens the list anywhere. Inside `set_variation('…')`,
  `variations['…']` and `params['…']` the list holds the valid names.
* The *Context* tab follows the cursor: type `gradient.` to see the palette methods, or put the cursor
  inside a call to see its arguments.
* `seed(42)` makes a random script repeat exactly.
* Errors show the line; click one in the output panel to jump there.
* `snapshot()` / `restore()` try things out inside a script; *Revert flame* undoes a whole run.
* Apophysis users: `Transform`, `AddTransform`, `Rotate`, `Scale`, `Translate`, `Multiply`, `RotateFlame`,
  `UpdateFlame`, `Print`, `ShowMessage`, `Random` work as you expect. Scripts are Python, not Pascal:
  `:=` becomes `=`, blocks are indented, and `Transform.Linear` becomes `transform.variations['linear']`.

## Reference

Everything below is a global name in a script. Types (`Transform`, `Camera`, …) are described after the functions.

### Objects

* `flame : Flame` — The flame being edited (a copy; the main window takes it over when the script finishes, as one undo step). Use the helpers below for most edits.
  ```python
  flame.name = 'scripted'
  ```
* `transforms : TransformList` — The transforms as Transform objects: `transforms[0]`, `for t in transforms:`, `len(transforms)`.
  ```python
  for t in transforms:
      t.rotate(10)
  ```
* `transform : Transform` — The active transform (Apophysis style). `add_transform()` makes the new one active; `set_active_transform(i)` picks another.
  ```python
  transform.weight = 0.5
  ```
* `camera : Camera` — The view: centre, scale, zoom, rotation, image size and the 3D camera.
  ```python
  camera.zoom_by(1.5)
  ```
* `gradient : Gradient` — The palette and the Gradient Library's operations.
  ```python
  gradient.random().hue_shift(40)
  ```
* `xaos : Xaos` — The chaos matrix.
  ```python
  xaos.chain()
  ```
* `coloring : Coloring` — Brightness, gamma, threshold, vibrancy, contrast, background.
  ```python
  coloring.gamma = 3.5
  ```

### Transforms

* `add_transform(spec?, weight?, color?, color_speed?, opacity?, a?, b?, c?, d?, e?, f?, coefs?, post?, variations?, params?, name?, xaos?)` → `Transform` — Append a transform and make it active. Give a Transform / dict to copy, or keyword arguments.
  * `spec?` `Transform|dict`: What to copy (optional).
  * `weight?` `float`: Relative probability (default 0.5).
  * `color?` `float`: Palette position 0..1.
  * `color_speed?` `float`: 0..1, how strongly the point colour moves to `color`.
  * `opacity?` `float`: 0..1.
  * `coefs?` `tuple`: (a, b, c, d, e, f).
  * `post?` `tuple`: Post affine (a, b, c, d, e, f).
  * `variations?` `dict`: {'name': weight, …} — replaces the default linear.
  * `params?` `dict`: {'julian_power': 4, …}.
  * `xaos?` `list`: Chaos row.
  ```python
  t = add_transform(weight=1, variations={'spherical': 1}, color=0.3)
  ```
* `add_random_transform(variations?)` → `Transform` — Append a transform with one of Apophysis's random affines and random variations.
  * `variations?` `list[str]`: Names to choose from (default: every formula). (any loaded formula name)
* `insert_transform(index, spec?, weight?, color?, color_speed?, opacity?, a?, b?, c?, d?, e?, f?, coefs?, post?, variations?, params?, name?, xaos?)` → `Transform` — Insert a transform at a position.
  * `weight?` `float`: Relative probability (default 0.5).
  * `color?` `float`: Palette position 0..1.
  * `color_speed?` `float`: 0..1, how strongly the point colour moves to `color`.
  * `opacity?` `float`: 0..1.
  * `coefs?` `tuple`: (a, b, c, d, e, f).
  * `post?` `tuple`: Post affine (a, b, c, d, e, f).
  * `variations?` `dict`: {'name': weight, …} — replaces the default linear.
  * `params?` `dict`: {'julian_power': 4, …}.
  * `xaos?` `list`: Chaos row.
* `remove_transform(which?)` → `Transform` — Delete a transform (default: the active one).
* `copy_transform(which?)` → `Transform` — Duplicate a transform (default: the active one); the copy becomes active.
* `clear_transforms()` — Remove every transform and the final transform.
* `get_transform(which)` → `Transform` — A transform by index.
* `set_active_transform(which)` → `Transform` — Choose what `transform` refers to.
* `move_transform(which, to)` — Re-order: move a transform to another position.
* `swap_transforms(first, second)` — Swap two transforms (their xaos rows and columns follow).
* `for_each_transform(fn)` — Call fn(transform, index) for every transform.
  ```python
  for_each_transform(lambda t, i: t.set_variation('linear', 1))
  ```
* `normalize_weights()` — Scale the weights so they add up to 1.
* `total_weight()` → `float` — Sum of the transform weights.
* `final_transform()` → `Transform|None` — The final transform as a Transform, or None.
* `set_final_transform(spec?, weight?, color?, color_speed?, opacity?, a?, b?, c?, d?, e?, f?, coefs?, post?, variations?, params?, name?, xaos?)` → `Transform` — Create or replace the final transform (keyword arguments as for add_transform); `set_final_transform(None)` removes it.
  * `weight?` `float`: Relative probability (default 0.5).
  * `color?` `float`: Palette position 0..1.
  * `color_speed?` `float`: 0..1, how strongly the point colour moves to `color`.
  * `opacity?` `float`: 0..1.
  * `coefs?` `tuple`: (a, b, c, d, e, f).
  * `post?` `tuple`: Post affine (a, b, c, d, e, f).
  * `variations?` `dict`: {'name': weight, …} — replaces the default linear.
  * `params?` `dict`: {'julian_power': 4, …}.
  * `xaos?` `list`: Chaos row.
  ```python
  set_final_transform(variations={'spherical': 1})
  ```
* `remove_final_transform()` — Remove the final transform.
* `new_transform(spec?, weight?, color?, color_speed?, opacity?, a?, b?, c?, d?, e?, f?, coefs?, post?, variations?, params?, name?, xaos?)` → `Transform` — A detached transform to prepare and add later.
  * `weight?` `float`: Relative probability (default 0.5).
  * `color?` `float`: Palette position 0..1.
  * `color_speed?` `float`: 0..1, how strongly the point colour moves to `color`.
  * `opacity?` `float`: 0..1.
  * `coefs?` `tuple`: (a, b, c, d, e, f).
  * `post?` `tuple`: Post affine (a, b, c, d, e, f).
  * `variations?` `dict`: {'name': weight, …} — replaces the default linear.
  * `params?` `dict`: {'julian_power': 4, …}.
  * `xaos?` `list`: Chaos row.

### Flame

* `new_flame(name?, keep_gradient?)` → `Flame` — Start from scratch: no transforms, default camera and colouring (the palette is kept unless keep_gradient=False).
* `random_flame(variations?, transforms?, seed?)` → `Flame` — Replace the flame with a random one, as the Random Batch window makes them.
  * `variations?` `list[str]`: Formulas to draw from (default: all). (any loaded formula name)
  * `transforms?` `tuple|int`: (min, max) or a count (default (2, 5)).
* `load_flame(path, index?)` → `Flame` — Replace the flame with an entry of a .flame / .chaos / .fa file.
  * `path` `str`: 
  * `index?` `int`: Entry (default 0).
* `save_flame(path, name?)` → `int` — Append the flame to a .flame or .fa file (created if missing); returns its index.
  * `name?` `str`: Name to save under (default: the flame's).
* `set_flame(flame)` → `Flame` — Replace the flame with a Flame object (from copy_flame(), Flame(...) …).
* `copy_flame()` → `Flame` — An independent copy of the flame.
* `flame_text()` → `str` — The flame as .fa parameters text (what Copy Parameters uses).
* `flame_xml()` → `str` — The flame as Apophysis <flame> XML.
* `from_text(text)` → `Flame` — Replace the flame from parameters text (.fa JSON, <flame> XML or a Chaotica world).
* `snapshot(key?)` — Remember the flame under a key (script-local).
* `restore(key?)` → `Flame` — Go back to a snapshot.
* `validate()` → `list[str]` — Problems that would stop the flame rendering (an empty list is good).

### Variations

* `list_variations(filter?)` → `list[str]` — Names of every loaded formula.
  * `filter?` `str`: Only names containing this.
* `variation_info(name)` → `dict` — Facts about a formula: kind, parameters with defaults, origin, note.
  * `name` `str`:  (any loaded formula name)
* `variation_params(name)` → `list[str]` — Parameter names of a formula.
  * `name` `str`:  (any loaded formula name)
* `random_variation(exclude?)` → `str` — A random formula name.
  * `exclude?` `list[str]`: Names to skip (default ['pre_blur']).

### Randomness

* `random(a?, b?)` → `float` — random() → 0..1, random(n) → 0..n, random(a, b) → a..b.
* `random_int(a, b?)` → `int` — A random integer a..b (both included), or 0..a.
* `random_choice(items)` → `any` — A random element.
* `random_gauss(mean?, sigma?)` → `float` — A normally distributed number.
* `random_bool(probability?)` → `bool` — True with the given probability.
  * `probability?` `float`: Default 0.5.
* `random_color()` → `tuple` — A random (r, g, b).
* `seed(value)` — Seed the script's random numbers so it repeats exactly.

### Maths helpers

* `clamp(value, lo, hi)` → `float` — Limit a value to lo..hi.
* `lerp(a, b, t)` → `float` — Linear interpolation a → b.
* `deg2rad(degrees)` → `float` — Degrees → radians.
* `rad2deg(radians)` → `float` — Radians → degrees.
* `dist(x1, y1, x2, y2)` → `float` — Distance between two points.
* `hex_to_rgb(text)` → `tuple` — '#rrggbb' → (r, g, b).
* `rgb_to_hex(rgb)` → `str` — (r, g, b) → '#rrggbb'.
* `math : math` — Python's math module (sin, cos, atan2, hypot, …).
* `PI : float` — 3.14159…
* `TAU : float` — 2π

### Output & interaction

* `print(*values, sep=' ', end='\n')` — Write to the output panel (like Python's print).
  * `values` `any`: Anything; separated by spaces.
  ```python
  print('weights:', [t.weight for t in transforms])
  ```
* `clear()` — Clear the output panel.
* `message(text)` — Show a message box (the script continues afterwards).
* `input_text(prompt?, default?)` → `str|None` — Ask the user for text; None if cancelled.
  ```python
  name = input_text('Flame name?', flame.name)
  ```
* `input_number(prompt?, default?)` → `float|None` — Ask for a number (asks again until it is one); None if cancelled.
  ```python
  n = input_number('How many copies?', 4)
  if n is None:
      stop()
  ```
* `confirm(text?)` → `bool` — A Yes / No question.
* `update(wait?)` — Show the flame in the main window now and re-render — for step-by-step previews and animations.
  * `wait?` `bool`: Wait for the first render pass (default True).
  ```python
  for i in range(12):
      camera.rotate_by(30)
      update()
      sleep(0.2)
  ```
* `sleep(seconds)` — Pause for a while (Stop still works).
* `progress(fraction)` — Show progress 0..1 in the status bar.
* `stop(reason?)` — End the script here; what it changed so far is kept.

### Classes

* `Flame : Flame` — The model class (advanced: build flames by hand).
* `XForm : XForm` — The raw transform class (advanced).
* `Gradient : NodeGradient` — The node-gradient class (for set_stops / blend).
* `ColorStop : ColorStop` — A gradient node: ColorStop(position, (r, g, b)).

### Apophysis compatibility

* `Transform : Transform` — Apophysis alias of `transform` (the active transform).
* `AddTransform()` → `Transform` — Apophysis alias of add_transform().
* `DeleteTransform()` — Apophysis: delete the active transform.
* `CopyTransform()` → `Transform` — Apophysis alias of copy_transform().
* `SetActiveTransform(which)` — Apophysis alias of set_active_transform(i).
* `Rotate(degrees)` — Apophysis: rotate the active transform.
* `Scale(factor)` — Apophysis: scale the active transform.
* `Translate(dx, dy)` — Apophysis: translate the active transform.
* `Multiply(a, b, c, d)` — Apophysis: multiply the active transform's matrix.
* `RotateFlame(degrees)` — Apophysis: rotate the camera.
* `NormalizeWeights()` — Apophysis alias of normalize_weights().
* `RandomGradient()` — Apophysis alias of gradient.random().
* `UpdateFlame()` — Apophysis alias of update().
* `ShowMessage(text)` — Apophysis alias of message().
* `Print(*values)` — Apophysis alias of print().
* `Clear()` — Apophysis alias of clear().
* `Random(n?)` → `float` — Apophysis: 0..1, or an integer 0..n−1.
* `Trunc(value)` → `int` — Truncate.
* `Round(value)` → `int` — Round.
* `Sqr(value)` → `float` — x².

## Types

### Transform

A transform of the flame (a live view of one XForm). Attributes are read and assigned directly; editing methods return the transform so calls chain. Affine coefficients follow the flame-file / Apophysis script order: x′ = a·x + c·y + e, y′ = b·x + d·y + f. X = (a, b), Y = (c, d) and O = (e, f) are the triangle's vectors; y points down on screen.

* `weight : float` — Relative probability of choosing this transform (final transforms ignore it).
* `color : float` — Palette position 0..1 the point colour is pulled towards.
* `color_speed : float` — How strongly each hit pulls the colour to `color` (flam3 semantics, 0..1).
* `symmetry : float` — Apophysis's symmetry = 1 − 2·color_speed (get/set).
* `opacity : float` — Plot weight of points leaving this transform (0 = shapes the fractal but draws nothing).
* `var_color : float` — Blend of direct-colour variations into the point colour (Apophysis var_color).
* `name : str` — Optional label.
* `a : float` — Affine a (X vector, x component).
* `b : float` — Affine b (X vector, y component).
* `c : float` — Affine c (Y vector, x component).
* `d : float` — Affine d (Y vector, y component).
* `e : float` — Affine e (origin x).
* `f : float` — Affine f (origin y).
* `coefs : tuple` — All six coefficients (a, b, c, d, e, f) — get or assign.
* `post : Affine` — The post-variation affine: `t.post.a`, `t.post.coefs`, `t.post.reset()`.
* `origin : tuple` — (e, f): where the O point sits — get or assign.
* `determinant : float` *(read-only)* — a·d − b·c: the triangle's signed area factor.
* `variations : VariationMap` — Variation name → weight (live): `t.variations['julian'] = 1`; 0 removes.
* `variation_names : list[str]` *(read-only)* — Names of the variations in use.
* `params : dict` — Variation parameters keyed as in flame files: `t.params['julian_power'] = 4`.
* `xaos : list[float]` — This transform's chaos row (weight of every transform following it).
* `index : int` *(read-only)* — Position in `transforms` (0-based); −1 for the final transform.
* `is_final : bool` *(read-only)* — True for the final transform.
* `xform : XForm` *(read-only)* — The underlying model object.
* `set_affine(a, b, c, d, e, f)` → `Transform` — Set all six coefficients.
* `reset_affine()` → `Transform` — Identity affine.
* `reset_post()` → `Transform` — Identity post affine.
* `rotate(degrees)` → `Transform` — Turn the triangle about its own origin.
  * `degrees` `float`: Positive = counter-clockwise on screen.
  ```python
  transform.rotate(45)
  ```
* `rotate_around(degrees, x?, y?)` → `Transform` — Turn the whole triangle (origin included) about a point.
  * `x?` `float`: Pivot x (default 0).
  * `y?` `float`: Pivot y (default 0).
* `scale(sx, sy?)` → `Transform` — Scale the X and Y vectors about the origin.
  * `sy?` `float`: Separate y factor (default = sx).
* `translate(dx, dy)` → `Transform` — Move the origin by (dx, dy) fractal units.
* `move_to(x, y)` → `Transform` — Put the origin at (x, y).
* `multiply(a, b, c, d)` → `Transform` — Apophysis Multiply: compose the 2×2 part with [[a, b], [c, d]].
* `flip_horizontal()` → `Transform` — Mirror in the vertical axis through (0, 0).
* `flip_vertical()` → `Transform` — Mirror in the horizontal axis through (0, 0).
* `set_variation(name, weight)` → `Transform` — Set a variation's weight (0 removes it); its parameters get their defaults.
  * `name` `str`: Formula name. (any loaded formula name)
  ```python
  transform.set_variation('julian', 1)
  ```
* `get_variation(name)` → `float` — A variation's weight (0 if unused).
  * `name` `str`:  (any loaded formula name)
* `has_variation(name)` → `bool` — True if the variation is in use.
  * `name` `str`:  (any loaded formula name)
* `remove_variation(name)` → `Transform` — Drop one variation.
  * `name` `str`:  (any loaded formula name)
* `clear_variations()` → `Transform` — Remove every variation.
* `total_variation_weight()` → `float` — Sum of the variation weights.
* `normalize_variations()` → `Transform` — Scale the variation weights to add up to 1.
* `set_param(name, value)` → `Transform` — Set a variation parameter (name checked against the loaded formulas).
  * `name` `str`: e.g. julian_power (any variation parameter name)
* `get_param(name, default?)` → `float` — A parameter's value, else its formula default.
  * `name` `str`:  (any variation parameter name)
* `copy()` → `Transform` — A detached copy — add it with add_transform(copy).
* `to_dict()` → `dict` — Plain-data snapshot of the transform.

### Affine

Six coefficients of an affine (the post transform). Affine coefficients follow the flame-file / Apophysis script order: x′ = a·x + c·y + e, y′ = b·x + d·y + f. X = (a, b), Y = (c, d) and O = (e, f) are the triangle's vectors; y points down on screen.

* `a : float`
* `b : float`
* `c : float`
* `d : float`
* `e : float`
* `f : float`
* `coefs : tuple` — (a, b, c, d, e, f) — get or assign.
* `reset()` → `Affine` — Identity.

### VariationMap

Dict-like: variation name → weight. Any loaded formula name is a valid key; assigning 0 removes the variation; new ones get their parameter defaults.

Any loaded formula name is a valid key (`t.variations['julian'] = 1`).


### TransformList

`transforms`: the flame's transforms as Transform objects — `len()`, `transforms[i]`, slices, `for t in transforms`.

* `index(transform)` → `int` — Position of a Transform object.

### Camera

The view. `zoom` is Apophysis's log2 zoom (+1 = twice as close); angles are in degrees.

* `x : float` — Centre x (fractal units).
* `y : float` — Centre y (y points down on screen).
* `center : tuple` — (x, y) — get or assign.
* `scale : float` — Pixels per fractal unit at the flame's own width (Apophysis scale).
* `zoom : float` — log2 magnification: each +1 doubles it.
* `rotate : float` — Rotation in degrees.
* `width : int` — The flame's image width in pixels.
* `height : int` — The flame's image height.
* `size : tuple` *(read-only)* — (width, height).
* `pitch : float` — 3D camera: tilt about the screen's horizontal axis, degrees (Apophysis cam_pitch).
* `pitch_y : float` — 3D camera: tilt about the vertical axis, degrees (Fractalchemy cam_pitch_y).
* `yaw : float` — 3D camera: spin about the plane's normal, degrees (cam_yaw).
* `perspective : float` — Perspective strength (cam_perspective; 0 = orthographic).
* `zpos : float` — Depth offset (cam_zpos).
* `dof : float` — Depth-of-field blur (cam_dof).
* `set_size(width, height)` → `Camera` — The flame's own image size.
* `reset()` → `Camera` — Centre (0, 0), scale 200, no zoom, rotation or 3D.
* `reset_3d()` → `Camera` — Flat again: pitch, yaw, perspective, zpos and dof to 0.
* `pan(dx, dy)` → `Camera` — Move the centre by (dx, dy) fractal units.
* `zoom_by(factor)` → `Camera` — Multiply the magnification (2 = twice as close, 0.5 = twice as far).
* `rotate_by(degrees)` → `Camera` — Add to the rotation.
* `fit(margin?)` → `bool` — Frame the attractor like the Random Batch does (samples the system); False if it blows up.
  * `margin?` `float`: Space around the attractor (default 1.15).
  ```python
  camera.fit()
  ```
* `to_dict()` → `dict` — Plain-data snapshot.

### Coloring

The tone mapping (Apophysis semantics).

* `brightness : float` — Overall log-density brightness (default 4).
* `gamma : float` — Display gamma (default 4).
* `gamma_threshold : float` — Below this density gamma blends linearly (default 0.01).
* `vibrancy : float` — 1 = colour from palette ratios, 0 = per-channel gamma.
* `contrast : float` — Density scaling (default 1).
* `background : color` — Background colour — (r, g, b) or '#rrggbb'.
* `background_hex : str` *(read-only)* — The background as '#rrggbb'.
* `reset()` → `Coloring` — Apophysis defaults.
* `reset_curves(channel?)` → `Coloring` — Straighten the tone curves.
  * `channel?` `str`: One channel, or all when omitted. (overall / red / green / blue / alpha)

### Gradient

The flame's palette (256 colours) plus the Gradient Library's node operations. A colour is (r, g, b) with 0..255 or a '#rrggbb' string.

* `colors : list` — All 256 palette colours (a copy; assign a list of colours to replace the palette).
* `stops : NodeGradient` *(read-only)* — The palette as a simplified node gradient (a copy, like the Gradient Library shows).
* `get_color(index)` → `tuple` — One palette entry.
  * `index` `int`: 0..255
* `set_color(index, color)` → `Gradient` — Set one palette entry.
  * `index` `int`: 0..255
* `color_at(position)` → `tuple` — The colour a transform with `color = position` paints with.
  * `position` `float`: 0..1
* `hex_colors()` → `list[str]` — All 256 colours as '#rrggbb'.
* `set_stops(stops)` → `Gradient` — Rebuild the palette from nodes.
  * `stops` `list`: A Gradient, or [(position, color), …] with positions 0..1.
  ```python
  gradient.set_stops([(0, '#000'), (0.6, (255, 120, 0)), (1, '#fff')])
  ```
* `from_colors(colors)` → `Gradient` — Spread colours evenly over the palette.
  * `colors` `list`: e.g. ['#000', '#f80', '#fff']
* `random()` → `Gradient` — A whole new random gradient (Gradient Library: Reroll).
* `randomize_colors()` → `Gradient` — Keep the nodes, new harmonising colours.
* `randomize_positions()` → `Gradient` — Keep the colours, scatter the nodes.
* `add_nodes()` → `Gradient` — Insert a few harmonising nodes (Auto increase nodes).
* `remove_nodes()` → `Gradient` — Drop a share of the nodes (Decrease nodes).
* `smooth()` → `Gradient` — Blur the colour curve (Smooth gradient).
* `rotate(amount)` → `Gradient` — Cycle the palette.
  * `amount` `float`: Fraction of the length (0.5 = half a turn), or whole entries when |amount| ≥ 1.
* `reverse()` → `Gradient` — Reverse the palette.
* `invert()` → `Gradient` — Invert every colour.
* `hue_shift(degrees)` → `Gradient` — Turn every colour's hue.
* `adjust(hue?, saturation?, luminance?)` → `Gradient` — The Gradient Library's whole-gradient sliders.
  * `hue?` `float`: Degrees.
  * `saturation?` `float`: Percent −100..100.
  * `luminance?` `float`: Percent −100..100.
  ```python
  gradient.adjust(hue=30, saturation=20)
  ```
* `blend(other, amount?)` → `Gradient` — Mix with another palette.
  * `other` `list`: A list of colours, a Gradient or another gradient helper.
  * `amount?` `float`: 0..1 (default 0.5).
* `load(path, index?)` → `Gradient` — Load a gradient from any file the Gradient Library reads.
  * `path` `str`: .ugr, .map, .flame, .chaos, .fa, an image …
  * `index?` `int`: Entry in a multi-gradient file (default 0).

### Xaos

The chaos matrix: matrix[from][to] is the relative weight of transform `to` following transform `from` (1 = normal, 0 = never). Indices or Transform objects may be given.

* `matrix : list` *(read-only)* — The full matrix as nested lists (a copy).
* `is_default : bool` *(read-only)* — True when no xaos is in effect.
* `get(from_, to)` → `float` — One weight.
* `set(from_, to, weight)` → `Xaos` — Set one weight.
  * `weight` `float`: 0 = never, 1 = normal, larger = more often.
  ```python
  xaos.set(0, 1, 0)
  ```
* `set_matrix(matrix)` → `Xaos` — Set the whole matrix from nested lists.
* `set_row(from_, weights)` → `Xaos` — All weights leading from one transform.
* `set_column(to, weights)` → `Xaos` — All weights leading to one transform.
* `reset()` → `Xaos` — No xaos at all.
* `chain(allow_self?)` → `Xaos` — A ring: i may only be followed by i + 1.
  * `allow_self?` `bool`: Also allow i → i.
* `isolate(which)` → `Xaos` — A transform that only follows itself, with nothing leading to it.
* `from_function(fn)` → `Xaos` — Fill from fn(from_index, to_index) → weight.
  ```python
  xaos.from_function(lambda i, j: 0 if i == j else 1)
  ```
* `randomize(probability?)` → `Xaos` — Random on/off links (every transform keeps a way out).
  * `probability?` `float`: Chance of a link (default 0.5).

### Flame

The model object behind the helpers (fractalchemy.fractal.scene.Flame). The helpers are friendlier; these fields are the raw data.

* `name : str` — The flame's name (shown in the title, saved with the file).
* `xforms : list[XForm]` — The raw transforms (prefer `transforms`).
* `final : XForm|None` — The raw final transform.
* `camera : RawCamera` — The raw camera (centre tuple, angles in radians) — prefer `camera`.
* `coloring : RawColoring` — The raw tone mapping — prefer `coloring`.
* `palette : list` — The 256 palette colours — prefer `gradient`.
* `oversample : int` — The file's own final-render oversample hint.
* `filter_radius : float` — The file's own filter radius hint.
* `unsupported : list[str]` *(read-only)* — Variation names in the file no engine implements.
* `gradient : NodeGradient` *(read-only)* — The palette as a node Gradient (a copy).
* `set_gradient(gradient)` — Replace the palette by sampling a node Gradient.
* `renderable()` → `bool` — True if some transform has a positive weight.
* `copy()` → `Flame` — An independent copy.
* `to_dict()` → `dict` — JSON-ready data.

### XForm

The raw transform dataclass (weight, color, color_speed, opacity, coefs, post, variations, params, chaos, name, var_color).

* `weight : float`
* `color : float`
* `color_speed : float`
* `opacity : float`
* `coefs : tuple`
* `post : tuple`
* `variations : dict`
* `params : dict`
* `chaos : list|None`
* `name : str`
* `var_color : float`
* `copy()` → `XForm` — Deep copy.

### RawCamera

fractalchemy.fractal.scene.Camera: center (x, y), scale, zoom, rotate (degrees), width, height, pitch / yaw / pitch_y (radians), perspective, zpos, dof.

* `center : tuple`
* `scale : float`
* `zoom : float`
* `rotate : float`
* `width : int`
* `height : int`
* `pitch : float` — radians
* `yaw : float` — radians
* `pitch_y : float` — radians
* `perspective : float`
* `zpos : float`
* `dof : float`

### RawColoring

fractalchemy.fractal.scene.Coloring.

* `brightness : float`
* `gamma : float`
* `gamma_threshold : float`
* `vibrancy : float`
* `contrast : float`
* `background : tuple` — (r, g, b)
* `curves : Curves` — Tone curves.

### NodeGradient

fractalchemy.model.Gradient: a cyclic list of ColorStop(position, color) nodes.

* `name : str`
* `stops : list[ColorStop]` — Sorted by position.
* `color_at(t)` → `tuple` — Interpolated colour at 0..1.
* `sample(count)` → `list` — `count` evenly spaced colours.
* `move_stop(index, position)` → `int` — Move a node.
* `set_color(index, color)` — Recolour a node.
* `copy()` → `NodeGradient` — Deep copy.

### ColorStop

One gradient node.

* `position : float` — 0..1
* `color : tuple` — (r, g, b)

## Built-in templates

* **Add random transform** (Transforms) — Appends a transform with a random affine and random variations (Apophysis: Add random transform).
* **Gnarl** (Transforms) — A new flame: a near-identity transform with small popcorn2 / waves2 warps — the classic gnarl.
* **Julia mutation** (Transforms) — The classic Apophysis "Julia" script: pushes the transforms outwards and adds a julian transform.
* **Make rotational symmetry** (Transforms) — Adds rotated linear copies so the whole fractal gets N-fold rotational symmetry (the classic Apophysis trick).
* **Mirror horizontally** (Transforms) — Flips every transform (and the final transform) in the vertical axis.
* **Mutate (jitter) coefficients** (Transforms) — Nudges every affine coefficient a little — a quick way to explore nearby fractals.
* **Normalize weights** (Transforms) — Scales the transform weights so they add up to 1 (Apophysis: Normalize Weights).
* **Random rotate about the centre** (Transforms) — Rotates every transform, position included, by a random angle about (0, 0).
* **Random rotate all transforms** (Transforms) — Rotates every transform by a random angle about its own origin.
* **Random variation swap** (Transforms) — Keeps linear and replaces every other variation with a random one of the same weight.
* **Reset post transforms** (Transforms) — Sets every post transform back to the identity.
* **Reset variations to linear** (Transforms) — Replaces every variation with linear = 1, keeping affines, colours and weights.
* **Scale all transforms** (Transforms) — Scales every transform about its origin by a factor you choose.
* **Spiral** (Transforms) — A new flame: a logarithmic spiral from a scaled-and-rotated transform plus a decorative one.
* **Tile the plane** (Transforms) — A new flame: four half-scale linear transforms that tile the plane, plus one shaping transform.
* **Gradient cycle preview** (Colours) — Animates the gradient rotating through the fractal in the main window (uses update()).
* **Gradient from a file** (Colours) — Loads a gradient from a file the Gradient Library reads (.ugr, .map, .flame, an image …).
* **Rainbow gradient** (Colours) — Fills the palette with a full hue cycle.
* **Random gradient** (Colours) — A whole new random gradient (the Gradient Library's Reroll).
* **Spread colours evenly** (Colours) — Distributes the transform colours evenly along the gradient.
* **Warm / cool shift** (Colours) — Turns the hue of the whole gradient and boosts its saturation (the Gradient Library's sliders).
* **Random xaos** (Xaos) — Random on / off links with a chosen density; every transform keeps at least one way out.
* **Reset xaos** (Xaos) — Clears all chaos weights.
* **Xaos chain** (Xaos) — Each transform may only be followed by the next one (a ring), self-loops allowed.
* **Xaos: no self loops** (Xaos) — Transforms never follow themselves.
* **3D tilt** (Camera) — Tilts the plane with the 3D camera and adds a little perspective.
* **Camera spin preview** (Camera) — Rotates the camera in steps, re-rendering each — a mini animation preview.
* **Fit camera to the fractal** (Camera) — Frames the attractor the way the Random Batch does.
* **Reset camera** (Camera) — The default camera: centre (0, 0), scale 200, no zoom, rotation or 3D.
* **Set HD image size** (Camera) — Sets the flame's own image size to 1920 × 1080, keeping the framing.
* **Build a flame from scratch** (Flame) — A commented walk-through of the whole API: transforms, variations, colours, xaos and the camera.
* **Flame report** (Flame) — Prints everything about the current flame to the output panel.
* **Print flame XML** (Flame) — Prints the flame as Apophysis <flame> XML.
* **Random flame explorer** (Flame) — Shows random flames one after another; answer Yes to keep the current one.
* **Save rotated variants to a file** (Flame) — Appends several rotated copies of the flame to a .flame file of your choice.
