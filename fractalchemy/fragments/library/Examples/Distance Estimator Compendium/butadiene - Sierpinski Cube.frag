#info A Sierpinski tetrahedron of cubes under a cube superstructure, by butadiene. From the Distance Estimator Compendium, CC BY-NC-SA 3.0.
#include "MathUtils.frag"
#include "DE-Raytracer.frag"

#group Fractal
uniform int Iterations; slider[1,12,20]
uniform float Scale; slider[1.2,1.8,3]
uniform vec3 Offset; slider[(-2,-2,-2),(1,1,1),(2,2,2)]
uniform float CubeSize; slider[0.2,1.5,3]
// Size of the cube superstructure (0 = none)
uniform float Super; slider[0,1,3]

float cubeDE(vec3 p, vec3 s) {
	vec3 q = abs(p);
	vec3 m = max(s - q, 0.0);
	return length(max(q - s, 0.0)) - min(min(m.x, m.y), m.z);
}

float tetDE(vec3 p) {
	vec4 z = vec4(p, 1.0);
	for (int i = 0; i < Iterations; i++) {
		if (z.x + z.y < 0.0) z.xy = -z.yx;
		if (z.x + z.z < 0.0) z.xz = -z.zx;
		if (z.z + z.y < 0.0) z.zy = -z.yz;
		z *= Scale;
		z.xyz += Offset * (1.0 - Scale);
	}
	return cubeDE(z.xyz, vec3(CubeSize)) / z.w;
}

float DE(vec3 p) {
	if (Super > 0.0) {
		p = abs(p) - 4.0 * Super;
		p = abs(p) - 2.0 * Super;
		p = abs(p) - 1.0 * Super;
	}
	return tetDE(p);
}

#preset Default
FOV = 0.4
Eye = 9,7,-12
Target = 0,0,0
Up = 0,1,0
Detail = -3.2
DetailAO = -1.4
BaseColor = 0.85,0.8,0.75
OrbitStrength = 0.4
X = 0.5,0.6,0.6,0.7
Y = 1,0.6,0,0.4
Z = 0.8,0.78,1,0.5
R = 0.4,0.7,1,0.12
BackgroundColor = 0.28,0.3,0.38
GradientBackground = 0.3
#endpreset
