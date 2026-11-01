#info Indra's Pearls: the limit set of inversions in a necklace of kissing circles — a loop of pearls that breaks into dust as the circles pull apart
#include "MathUtils.frag"
#include "Complex.frag"
#include "Progressive2D.frag"

#group Necklace
uniform int Iterations; slider[1,30,200]
// Circles in the necklace
uniform int Count; slider[3,6,12]
// Radius of the ring the circle centres sit on
uniform float RingRadius; slider[0.2,1,2]
// 1 = the circles just kiss; smaller pulls them apart (Schottky dust), larger makes them overlap
uniform float Kiss; slider[0.3,1,1.6]
// Add a circle in the middle, tangent to the necklace
uniform bool CentreCircle; checkbox[true]
uniform float CentreScale; slider[0.2,1,1.5]
uniform float Thickness; slider[0,0.004,0.05]
uniform vec3 CircleColor; color[1.0,0.95,0.85]
uniform vec3 Inside; color[0.08,0.05,0.2]
uniform float ColorSpeed; slider[0,0.1,0.5]

bool invert(inout vec2 z, inout float s, vec2 c, float r) {
	vec2 d = z - c;
	float r2 = dot(d, d);
	if (r2 >= r * r) return false;
	float f = r * r / max(r2, 1e-12);
	z = c + d * f;
	s *= f;
	return true;
}

vec3 color(vec2 p) {
	float n = float(Count);
	float r = RingRadius * sin(3.14159265 / n) * Kiss;
	float rc = (RingRadius - RingRadius * sin(3.14159265 / n)) * CentreScale;
	vec2 z = p;
	float s = 1.0;
	int steps = 0;
	for (int i = 0; i < Iterations; i++) {
		bool moved = false;
		for (int k = 0; k < 12; k++) {
			if (k >= Count) break;
			float a = 6.2831853 * float(k) / n;
			moved = invert(z, s, RingRadius * vec2(cos(a), sin(a)), r) || moved;
		}
		if (CentreCircle) moved = invert(z, s, vec2(0.0), rc) || moved;
		if (!moved) break;
		steps++;
	}
	float d = 1e9;
	for (int k = 0; k < 12; k++) {
		if (k >= Count) break;
		float a = 6.2831853 * float(k) / n;
		d = min(d, abs(length(z - RingRadius * vec2(cos(a), sin(a))) - r));
	}
	if (CentreCircle) d = min(d, abs(length(z) - rc));
	d /= s;
	if (d < Thickness) return CircleColor;
	float t = float(steps) * ColorSpeed;
	return Inside + 0.5 * (0.5 + 0.5 * cos(6.2831853 * t + vec3(0.0, 2.0, 4.0))) * (steps > 0 ? 1.0 : 0.3);
}

#preset Default
Center = 0,0
Zoom = 0.7
Iterations = 30
Count = 6
RingRadius = 1
Kiss = 1
CentreCircle = true
CentreScale = 1
#endpreset

#preset Schottky dust
Count = 4
Kiss = 0.7
CentreCircle = false
#endpreset
