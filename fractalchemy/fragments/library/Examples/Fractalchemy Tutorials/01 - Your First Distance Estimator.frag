#info Tutorial 1: a distance estimator from scratch — follow the STEP comments (Help ▸ Walkthrough lists them)
// STEP 1: Every 3D fragment starts with two includes: maths helpers and a raytracer. The raytracer calls your DE(vec3).
#include "MathUtils.frag"
#include "DE-Raytracer.frag"

// STEP 2: A #group names the tab (or section) the sliders below it appear in.
#group Tutorial

// STEP 3: An annotated uniform becomes a slider: slider[minimum, default, maximum]. The comment right above is its tooltip.
// Radius of the sphere
uniform float Radius; slider[0.1,1.0,3.0]
// Size of the box
uniform vec3 BoxSize; slider[(0.1,0.1,0.1),(0.8,0.8,0.8),(3,3,3)]
// Blend between the two shapes
uniform float Blend; slider[0,0.5,1]

// STEP 4: A distance estimator returns, for a point p, the distance to the surface: negative inside, positive outside.
float sphere(vec3 p) { return length(p) - Radius; }

float box(vec3 p) {
	vec3 q = abs(p) - BoxSize;
	return length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0);
}

// STEP 5: DE(vec3) is the function the raytracer marches along its rays. Combine shapes with min (union), max (intersection) or mix.
float DE(vec3 p) {
	return mix(box(p), sphere(p), Blend);
}

// STEP 6: A preset holds slider values; Default is applied when the fragment is built. F8 writes the current values as a new preset.
#preset Default
FOV = 0.4
Eye = 2.4,2.0,-3.2
Target = 0,0,0
Up = 0,1,0
Radius = 1
BoxSize = 0.8,0.8,0.8
Blend = 0.5
Detail = -2.8
BaseColor = 0.85,0.8,0.7
OrbitStrength = 0
BackgroundColor = 0.3,0.35,0.45
GradientBackground = 0.3
#endpreset
// STEP 7: Try it: drag the sliders, press F5 after editing the code, F1 resets everything. Then open tutorial 2 for folds.
