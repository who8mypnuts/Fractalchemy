#info Dragon curves by inverse iteration: the Heighway dragon and the Lévy C curve as distance fields (the curve runs from (0,0) to (1,0))
#include "MathUtils.frag"
#include "Complex.frag"
#include "Progressive2D.frag"

#group Dragon
uniform int Iterations; slider[0,14,24]
uniform int Curve; menu[0, Heighway dragon;Lévy C curve;Twin dragon]
uniform float Thickness; slider[0,0.004,0.05]
uniform vec3 CurveColor; color[1.0,1.0,1.0]
uniform vec3 FieldColor; color[0.9,0.4,0.2]
uniform float ContourScale; slider[1,25,200]

// the inverse of the two maps, chosen by the half (by its centroid) the point lies in; s grows by sqrt 2 per step
float dragon(vec2 z) {
	float s = 1.0;
	vec2 c1, c2;
	if (Curve == 1) { c1 = vec2(0.25, -0.25); c2 = vec2(0.75, -0.25); }       // Lévy: the halves bulge below the segment
	else { c1 = vec2(0.1, 0.3); c2 = vec2(0.7, 0.1); }                       // Heighway: the centroids of f1(D) and f2(D)
	for (int i = 0; i < Iterations; i++) {
		bool first = dot(z - c1, z - c1) < dot(z - c2, z - c2);
		if (Curve == 1) {
			z = first ? cMul(z, vec2(1.0, 1.0)) : vec2(1.0, 0.0) + cMul(z - vec2(1.0, 0.0), vec2(1.0, -1.0));   // g1 = z(1+i), g2 = 1 + (z-1)(1-i)
		} else {
			z = first ? cMul(z, vec2(1.0, -1.0)) : cMul(vec2(1.0, 0.0) - z, vec2(1.0, 1.0));                   // g1 = z(1-i), g2 = (1-z)(1+i)
		}
		s *= 1.41421356;
	}
	return length(z - vec2(clamp(z.x, 0.0, 1.0), 0.0)) / s;
}

vec3 color(vec2 p) {
	float d = dragon(p);
	if (Curve == 2) d = min(d, dragon(vec2(1.0, 0.0) - p));       // the twin: the dragon and its copy turned by 180 degrees about (0.5, 0)
	if (d < Thickness) return CurveColor;
	float rings = 0.5 + 0.5 * cos(d * ContourScale * 6.2831853);
	return FieldColor * (0.2 + 0.8 * rings) * exp(-d * 3.0);
}

#preset Default
Center = 0.4,0.15
Zoom = 1.1
Iterations = 14
Curve = 0
Thickness = 0.004
ContourScale = 25
#endpreset

#preset Levy
Center = 0.5,-0.3
Zoom = 0.8
Curve = 1
Iterations = 16
#endpreset
