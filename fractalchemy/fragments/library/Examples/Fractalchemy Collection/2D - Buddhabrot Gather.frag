#info Buddhabrot by gathering: every subframe throws random c values and counts the orbit points that land in each pixel; the accumulation converges to the orbit density
#include "MathUtils.frag"
#include "Complex.frag"
#include "Progressive2D.frag"

#group Buddhabrot
// Random starting points tried per pixel per subframe (cost!)
uniform int Samples; slider[1,32,200]
uniform int Iterations; slider[10,200,2000]
// Only orbits that escape after at least this many iterations count (higher = finer filaments)
uniform int MinIterations; slider[0,20,500]
// Radius around the pixel that counts as a hit, in pixels
uniform float HitRadius; slider[0.5,2,8]
uniform float Brightness; slider[0.1,40,400]
uniform vec3 Tint; color[0.85,0.9,1.0]
// Split the colour by escape time (Nebulabrot look)
uniform bool Nebula; checkbox[true]

uniform int subframe;

vec3 color(vec2 p) {
	float hit2 = pow(HitRadius * aaScale.y, 2.0);      // aaScale: one pixel in fractal units (Progressive2D.frag)
	vec3 sum = vec3(0.0);
	for (int s = 0; s < Samples; s++) {
		vec2 rnd = rand2(p * 137.1 + vec2(float(subframe) * 0.731, float(s) * 1.373));
		vec2 c = vec2(-2.2, -1.5) + rnd * vec2(3.2, 3.0);
		vec2 z = vec2(0.0);
		int n = 0;
		int first = -1;
		float count = 0.0;
		for (int i = 0; i < Iterations; i++) {
			z = cSqr(z) + c;
			if (dot(z, z) > 16.0) { n = i; break; }
			vec2 d = z - p;
			if (dot(d, d) < hit2) { count += 1.0; if (first < 0) first = i; }
			n = i + 1;
		}
		if (n >= Iterations || n < MinIterations) continue;    // did not escape (or too early): not part of the Buddhabrot
		if (Nebula) {
			float t = float(n) / float(Iterations);
			sum += count * vec3(smoothstep(0.0, 0.2, t), smoothstep(0.05, 0.5, t), smoothstep(0.2, 1.0, t));
		} else sum += count * Tint;
	}
	return sum * Brightness / float(Samples);
}

#preset Default
Center = -0.5,0
Zoom = 0.45
Samples = 32
Iterations = 200
MinIterations = 20
HitRadius = 2
Brightness = 40
Nebula = true
#endpreset
