#info Mosely snowflake: a Menger-like cube that keeps the 12 edge and 6 face sub-cubes and drops the 8 corners and the centre (Inigo Quilez's cut construction)
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Primitives.frag"

#group Snowflake
uniform int Iterations; slider[1,4,7]
// 1/3 is the snowflake; other cell sizes give cousins
uniform float CellSize; slider[0.2,0.33333,0.45]
// Also drop the centre cube
uniform bool DropCentre; checkbox[true]

float DE(vec3 p) {
	float d = sdBox(p, vec3(1.0));
	float s = 1.0;
	for (int m = 0; m < Iterations; m++) {
		vec3 a = mod(p * s, 2.0) - 1.0;           // cell coordinates in [-1, 1], at scale s
		vec3 q = abs(a);
		float cut = sdBox(q - (1.0 - CellSize), vec3(CellSize));         // the 8 corner cubes of the cell
		if (DropCentre) cut = min(cut, sdBox(a, vec3(CellSize)));
		d = max(d, -cut / s);
		s *= 3.0;
	}
	return d;
}

#preset Default
FOV = 0.4
Eye = 2.6,2.0,-3.0
Target = 0,0,0
Up = 0,1,0
Detail = -3.4
DetailAO = -1.5
BaseColor = 0.95,0.97,1
OrbitStrength = 0
BackgroundColor = 0.3,0.33,0.4
GradientBackground = 0.3
#endpreset
