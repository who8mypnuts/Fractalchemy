#info The 3D Koch snowflake: a tetrahedron grows a half-size tetrahedron on the middle of every face, again and again, and converges to a cube (a stella octangula after one step)
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Primitives.frag"

#group Koch3D
uniform int Iterations; slider[0,4,8]
// Two is the Koch tetrahedron; other values stretch the generator
uniform float Scale; slider[1.5,2,3]
uniform float Offset; slider[0,1,2]
// Round the tetrahedra a little
uniform float Rounding; slider[0,0,0.1]

// the regular tetrahedron with vertices (1,1,1), (1,-1,-1), (-1,1,-1), (-1,-1,1): a GDF-style distance
float sdTetra(vec3 p, float s) {
	const float k = 0.57735027;
	float d = max(max(dot(p, vec3(k, k, k)), dot(p, vec3(k, -k, -k))), max(dot(p, vec3(-k, k, -k)), dot(p, vec3(-k, -k, k))));
	return d - s * k;
}

float DE(vec3 p) {
	float s = 1.0;
	float d = sdTetra(p, 1.0);
	for (int i = 0; i < Iterations; i++) {
		// every face of the current surface gets a tetrahedron on its middle triangle: the surface splits into the four
		// corner copies (the Sierpinski branch) and the four inverted face copies; follow the branch the point is nearest to
		vec3 corner = foldSierpinski(p) * Scale - Offset * (Scale - 1.0);
		vec3 face = foldSierpinski(-p) * Scale - Offset * (Scale - 1.0);
		float dc = sdTetra(corner, 1.0), df = sdTetra(face, 1.0);
		p = (dc < df) ? corner : face;
		s *= Scale;
		d = min(d, min(dc, df) / s);
	}
	return d - Rounding;
}

#preset Default
FOV = 0.4
Eye = 2.8,2.2,-3.4
Target = 0,0,0
Up = 0,1,0
Detail = -3.2
DetailAO = -1.4
FudgeFactor = 0.6
BaseColor = 0.95,0.97,1
OrbitStrength = 0.3
X = 0.5,0.6,0.6,0.7
Y = 1,0.6,0,0.4
Z = 0.8,0.78,1,0.5
R = 0.4,0.7,1,0.12
BackgroundColor = 0.28,0.32,0.42
GradientBackground = 0.3
#endpreset
