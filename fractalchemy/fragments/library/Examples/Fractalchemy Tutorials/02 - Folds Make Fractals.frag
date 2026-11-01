#info Tutorial 2: from a box to a Menger sponge with folds — the kaleidoscopic IFS recipe
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
// STEP 1: Primitives.frag has the folds (foldMenger, foldSierpinski, foldBox, foldSphere) and primitives (sdBox, sdSphere …) used here.
#include "Primitives.frag"

#group Folds
// STEP 2: The number of times the fold-and-scale step repeats. Each repeat adds a level of detail (and costs time).
uniform int Iterations; slider[0,5,12]
// STEP 3: The scale: 3 gives the Menger sponge; try 2.5 or 4.
uniform float Scale; slider[1.5,3,5]
// The offset the space is scaled away from
uniform vec3 Offset; slider[(0,0,0),(1,1,1),(3,3,3)]
// A rotation between folds turns the sponge into something new
uniform vec3 Rotation; slider[(-180,-180,-180),(0,0,0),(180,180,180)]

float DE(vec3 p) {
	float s = 1.0;
	for (int i = 0; i < Iterations; i++) {
		// STEP 4: foldMenger mirrors the point into one octant and sorts the axes: 48 copies of one wedge.
		p = foldMenger(p);
		// STEP 5: Scale the wedge out and shift it: the fixed point of this map is where the sponge's corner cube ends up.
		p = p * Scale - Offset * (Scale - 1.0);
		// STEP 6: Knighty's trick for the Menger sponge: wrap z back up so the middle column is removed, not the corner.
		if (p.z < -0.5 * Offset.z * (Scale - 1.0)) p.z += Offset.z * (Scale - 1.0);
		p = rotationMatrixXYZ(Rotation) * p;
		s *= Scale;
	}
	// STEP 7: Measure a plain box in the folded space and divide by the accumulated scale: the distance in world space.
	return sdBox(p, vec3(1.0)) / s;
}

#preset Default
FOV = 0.4
Eye = 3.0,2.3,-3.6
Target = 0,0,0
Up = 0,1,0
Iterations = 5
Scale = 3
Offset = 1,1,1
Rotation = 0,0,0
Detail = -3.0
BaseColor = 0.9,0.85,0.7
OrbitStrength = 0.3
X = 0.5,0.6,0.6,0.7
Y = 1,0.6,0,0.4
Z = 0.8,0.78,1,0.5
R = 0.4,0.7,1,0.12
BackgroundColor = 0.3,0.33,0.4
GradientBackground = 0.3
#endpreset
// STEP 8: Build ▸ DE Composer… makes this recipe visually; Build ▸ Debug view ▸ DE slice shows whether the estimate is sound.
