#info A pseudo-Kleinian tower by mrange: mirrored repetition, inversions and a box. From the Distance Estimator Compendium, CC BY-NC-SA 3.0.
#include "MathUtils.frag"
#include "DE-Raytracer.frag"

#group Fractal
uniform int Iterations; slider[1,7,12]
uniform float BaseScale; slider[0.5,1.3,3]
// How much the scale grows with height
uniform float Growth; slider[0,0.95,3]
uniform float Period; slider[1,2,4]
uniform float Rotation; slider[0,0.5712,3.14]
uniform float BoxRound; slider[0,0.5,1]

void rotT(inout vec2 p, float a) {
	float c = cos(a), s = sin(a);
	p = vec2(c * p.x + s * p.y, -s * p.x + c * p.y);
}
float boxDE(vec3 p, vec3 b) {
	vec3 q = abs(p) - b;
	return length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0);
}
float mod1(inout float p, float size) {
	float halfsize = size * 0.5;
	float c = floor((p + halfsize) / size);
	p = mod(p + halfsize, size) - halfsize;
	return c;
}
vec2 modMirror2(inout vec2 p, vec2 size) {
	vec2 halfsize = size * 0.5;
	vec2 c = floor((p + halfsize) / size);
	p = mod(p + halfsize, size) - halfsize;
	p *= mod(c, vec2(2.0)) * 2.0 - vec2(1.0);
	return c;
}

float DE(vec3 p) {
	vec3 op = p;
	float s = BaseScale + smoothstep(0.15, 1.5, p.y) * Growth;
	float scale = 1.0;
	for (int i = 0; i < Iterations; i++) {
		mod1(p.y, Period);
		modMirror2(p.xz, vec2(Period));
		rotT(p.xz, Rotation);
		float r2 = dot(p, p);
		float k = s / r2;
		p *= k;
		scale *= k;
	}
	float d = boxDE(p - 0.1, vec3(1.0, 2.0, 1.0)) - BoxRound;
	d = abs(d) - 0.01;
	float d1 = 0.25 * d / scale;
	float db = boxDE(op - vec3(0.0, 0.5, 0.0), vec3(0.75, 1.0, 0.75)) - 0.5;
	float dp = op.y;
	return min(dp, max(d1, db));
}

#preset Default
FOV = 0.5
Eye = 2.6,1.9,-3.4
Target = 0,0.6,0
Up = 0,1,0
Detail = -3.4
DetailAO = -1.5
FudgeFactor = 0.6
BaseColor = 0.9,0.88,0.8
OrbitStrength = 0.3
X = 0.5,0.6,0.6,0.7
Y = 1,0.6,0,0.4
Z = 0.8,0.78,1,0.5
R = 0.4,0.7,1,0.12
BackgroundColor = 0.28,0.3,0.38
GradientBackground = 0.3
#endpreset
