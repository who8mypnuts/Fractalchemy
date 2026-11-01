#info The Koch snowflake as a solid: the 2D fold construction in the xz plane extruded along y, with a rounded edge
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Primitives.frag"

#group Koch
uniform int Iterations; slider[0,4,8]
uniform float Angle; slider[60,120,180]
uniform float Height; slider[0.02,0.3,2]
uniform float Rounding; slider[0,0.01,0.2]
// Scale the snowflake
uniform float Size; slider[0.2,1.5,4]

vec2 N(float angle) { return vec2(sin(angle), cos(angle)); }

float koch2D(vec2 uv) {
	float scale = 1.0;
	uv.x = abs(uv.x);
	uv.y += tan(radians(150.0)) * 0.5;
	vec2 n0 = N(radians(150.0));
	float d0 = dot(uv - vec2(0.5, 0.0), n0);
	uv -= n0 * max(0.0, d0) * 2.0;
	vec2 n = N(radians(Angle));
	uv.x += 0.5;
	for (int i = 0; i < Iterations; i++) {
		uv *= 3.0;
		scale *= 3.0;
		uv.x -= 1.5;
		uv.x = abs(uv.x);
		uv.x -= 0.5;
		uv -= n * min(0.0, dot(uv, n)) * 2.0;
	}
	// the signed distance: inside the snowflake the folded point lies below the segment
	float d = length(uv - vec2(clamp(uv.x, -1.0, 1.0), 0.0));
	return (uv.y < 0.0 ? -d : d) / scale;
}

float DE(vec3 p) {
	vec2 q = p.xz / Size;
	float d2 = koch2D(q) * Size;
	vec2 w = vec2(d2, abs(p.y) - Height);
	return min(max(w.x, w.y), 0.0) + length(max(w, 0.0)) - Rounding;
}

#preset Default
FOV = 0.4
Eye = 1.9,1.7,-2.3
Target = 0,0,0
Up = 0,1,0
Detail = -3.2
DetailAO = -1.4
BaseColor = 0.9,0.95,1
OrbitStrength = 0
BackgroundColor = 0.28,0.32,0.42
GradientBackground = 0.3
#endpreset
