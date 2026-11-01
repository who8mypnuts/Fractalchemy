#info The Apollonian gasket as the limit set of inversions in four circles (Indra's Pearls): iterate the inversion the point falls into, and measure the leftover
#include "MathUtils.frag"
#include "Complex.frag"
#include "Progressive2D.frag"

#group Gasket
uniform int Iterations; slider[1,40,200]
// Line width of the circles, in units of the (scaled) plane
uniform float Thickness; slider[0,0.004,0.05]
uniform vec3 CircleColor; color[1.0,0.95,0.8]
uniform vec3 Inside; color[0.05,0.1,0.25]
// Colour the regions by how many inversions it took to settle
uniform bool DepthColors; checkbox[true]
uniform float ColorSpeed; slider[0,0.08,0.5]

// the four mirror circles: each passes through three of the tangency points of the unit circle and its three inscribed circles
const vec3 M0 = vec3(0.0, 0.0, 0.267949192);
const vec3 M1 = vec3(0.0, 0.535898385, 0.464101615);
const vec3 M2 = vec3(-0.464101615, -0.267949192, 0.464101615);
const vec3 M3 = vec3(0.464101615, -0.267949192, 0.464101615);

bool invert(inout vec2 z, inout float s, vec3 c) {
	vec2 d = z - c.xy;
	float r2 = dot(d, d);
	if (r2 >= c.z * c.z) return false;
	float f = c.z * c.z / max(r2, 1e-12);
	z = c.xy + d * f;
	s *= f;
	return true;
}

vec3 color(vec2 p) {
	vec2 z = p;
	float s = 1.0;
	int n = 0;
	for (int i = 0; i < Iterations; i++) {
		bool moved = invert(z, s, M0) || invert(z, s, M1) || invert(z, s, M2) || invert(z, s, M3);
		if (!moved) break;
		n++;
	}
	// the fundamental region is the unit disk outside the four mirrors: its boundary circles are the gasket's circles
	float d = abs(length(z) - 1.0);
	d = min(d, abs(length(z - M0.xy) - M0.z));
	d = min(d, abs(length(z - M1.xy) - M1.z));
	d = min(d, abs(length(z - M2.xy) - M2.z));
	d = min(d, abs(length(z - M3.xy) - M3.z));
	d /= s;
	if (d < Thickness) return CircleColor;
	if (length(p) > 1.0) return vec3(0.0);
	if (!DepthColors) return Inside;
	float t = float(n) * ColorSpeed;
	return Inside + 0.5 * (0.5 + 0.5 * cos(6.2831853 * t + vec3(0.0, 2.0, 4.0)));
}

#preset Default
Center = 0,0
Zoom = 0.95
Iterations = 40
Thickness = 0.004
DepthColors = true
ColorSpeed = 0.08
#endpreset
