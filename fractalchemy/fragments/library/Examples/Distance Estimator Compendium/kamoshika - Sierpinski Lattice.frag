#info kamoshika's Sierpinski lattice (domain-repeated tetrahedra). From the Distance Estimator Compendium, CC BY-NC-SA 3.0.
#include "MathUtils.frag"
#include "DE-Raytracer.frag"

#group Fractal
uniform int Iterations; slider[1,6,12]
// Period of the lattice
uniform float Period; slider[0.5,1.73,4]
uniform float Scale; slider[1.5,2,3]
// Repeat the lattice (off: a single tetrahedron)
uniform bool Repeat; checkbox[true]

float DE(vec3 p) {
	float b = Period;
	vec3 Q = Repeat ? mod(p, b * 2.0) - b : p;
	float a = 1.0;
	for (int j = 0; j < Iterations; j++) {
		Q = abs(Q);
		if (Q.y > Q.x) Q.xy = Q.yx;
		if (Q.z > Q.x) Q.zx = Q.xz;
		Q *= Scale;
		Q.x -= b;
		a *= Scale;
	}
	return (dot(abs(Q), vec3(1.0) / b) - 1.0) / a;
}

#preset Default
FOV = 0.4
Eye = 3.6,2.4,-4.2
Target = 0,0,0
Up = 0,1,0
Detail = -3.2
DetailAO = -1.4
FudgeFactor = 0.6
BaseColor = 0.85,0.9,0.95
OrbitStrength = 0
BackgroundColor = 0.3,0.33,0.4
GradientBackground = 0.3
#endpreset
