#info The Heighway dragon curve as a solid ribbon: the 2D inverse iteration in the xz plane, extruded along y and twisted
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Primitives.frag"

#group Dragon
uniform int Iterations; slider[0,10,20]
uniform float Height; slider[0.01,0.15,1]
uniform float Width; slider[0.001,0.01,0.2]
uniform float Twist; slider[-4,0,4]
uniform float Size; slider[0.5,2,5]

vec2 cmul2(vec2 a, vec2 b) { return vec2(a.x * b.x - a.y * b.y, a.x * b.y + a.y * b.x); }

float dragon2D(vec2 z) {
	float s = 1.0;
	vec2 c1 = vec2(0.1, 0.3), c2 = vec2(0.7, 0.1);
	for (int i = 0; i < Iterations; i++) {
		bool first = dot(z - c1, z - c1) < dot(z - c2, z - c2);
		z = first ? cmul2(z, vec2(1.0, -1.0)) : cmul2(vec2(1.0, 0.0) - z, vec2(1.0, 1.0));
		s *= 1.41421356;
	}
	return length(z - vec2(clamp(z.x, 0.0, 1.0), 0.0)) / s;
}

float DE(vec3 p) {
	p = opTwist(p, Twist);
	vec2 q = (p.xz + vec2(0.5 * Size, 0.2 * Size)) / Size;    // centre the curve on the origin
	float d2 = dragon2D(q) * Size - Width;
	vec2 w = vec2(d2, abs(p.y) - Height);
	return min(max(w.x, w.y), 0.0) + length(max(w, 0.0));
}

#preset Default
FOV = 0.4
Eye = 1.9,2.2,-2.6
Target = 0,0,0
Up = 0,1,0
Detail = -3.4
DetailAO = -1.5
FudgeFactor = 0.8
BaseColor = 0.95,0.8,0.6
OrbitStrength = 0
BackgroundColor = 0.28,0.3,0.4
GradientBackground = 0.3
#endpreset
