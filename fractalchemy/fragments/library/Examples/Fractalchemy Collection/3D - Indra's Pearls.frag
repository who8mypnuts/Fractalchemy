#info Indra's Pearls in three dimensions: the limit set of inversions in a closed chain of kissing spheres — a necklace with two poles, or the spheres of a tetrahedron, octahedron or cube. Every sphere is reflected into every other for ever, and the pearls nest down to the fractal. Pearls larger than PearlSize are left invisible so the smaller ones inside them show: lower it to approach the limit set, raise it (or cut the structure open) to see the big pearls.
#define providesColor
#define providesInit
#include "MathUtils.frag"
#include "DE-Raytracer.frag"

#group Pearls
// How the generating spheres sit: a ring (with or without a sphere at each pole), or the vertices of a solid
uniform int Configuration; menu[1, Necklace;Necklace with poles;Tetrahedron;Octahedron;Cube]
uniform int Iterations; slider[1,40,80]
// Spheres in the necklace (ring configurations only)
uniform int Count; slider[3,6,12]
// Radius of the ring / solid the sphere centres sit on
uniform float RingRadius; slider[0.3,1,2]
// 1 = neighbouring spheres just kiss; smaller pulls them apart (Schottky dust), larger makes them overlap
uniform float Kiss; slider[0.3,1,1.5]
// Height of the polar spheres above and below the ring (their radius follows so they kiss the ring)
uniform float PoleHeight; slider[0.1,0.8,2]
// Only pearls up to this radius are drawn; the larger ones are invisible, so the nesting shows
uniform float PearlSize; slider[0.005,0.1,2]

#group Cutaway
uniform bool Cut; checkbox[false]
uniform vec3 CutNormal; slider[(-1,-1,-1),(0,1,0),(1,1,1)]
uniform float CutOffset; slider[-2,0,2]

#group Pearl colours
// The first pearls, and the deepest
uniform vec3 ShellColor; color[0.95,0.8,0.6]
uniform vec3 DeepColor; color[0.25,0.35,0.8]
// How quickly the colour changes with the depth of nesting
uniform float ColorSpeed; slider[0,0.3,1]
// A hue twist per depth on top of the two colours
uniform float HueTwist; slider[0,0.2,1]

const int MAX_SPHERES = 14;
vec3 centres[MAX_SPHERES];
float radii[MAX_SPHERES];
int sphereCount = 0;
int escapeSteps = 0;

void addSphere(vec3 c, float r) {
	if (sphereCount < MAX_SPHERES) { centres[sphereCount] = c; radii[sphereCount] = r; sphereCount++; }
}

void init() {
	sphereCount = 0;
	float R = RingRadius;
	if (Configuration <= 1) {
		float n = float(Count);
		float r = R * sin(PI / n) * Kiss;
		for (int k = 0; k < 12; k++) {
			if (k >= Count) break;
			float a = 2.0 * PI * float(k) / n;
			addSphere(R * vec3(cos(a), 0.0, sin(a)), r);
		}
		if (Configuration == 1) {
			float rp = (sqrt(R * R + PoleHeight * PoleHeight) - R * sin(PI / n)) * Kiss;   // tangent to every ring sphere
			addSphere(vec3(0.0, PoleHeight, 0.0), rp);
			addSphere(vec3(0.0, -PoleHeight, 0.0), rp);
		}
	} else if (Configuration == 2) {
		float r = R * sqrt(8.0 / 3.0) * 0.5 * Kiss;
		float s = R / sqrt(3.0);
		addSphere(s * vec3(1.0, 1.0, 1.0), r);
		addSphere(s * vec3(1.0, -1.0, -1.0), r);
		addSphere(s * vec3(-1.0, 1.0, -1.0), r);
		addSphere(s * vec3(-1.0, -1.0, 1.0), r);
	} else if (Configuration == 3) {
		float r = R * sqrt(2.0) * 0.5 * Kiss;
		for (int axis = 0; axis < 3; axis++) {
			vec3 e = vec3(axis == 0 ? 1.0 : 0.0, axis == 1 ? 1.0 : 0.0, axis == 2 ? 1.0 : 0.0);
			addSphere(R * e, r);
			addSphere(-R * e, r);
		}
	} else {
		float r = R / sqrt(3.0) * Kiss;
		float s = R / sqrt(3.0);
		for (int k = 0; k < 8; k++) {
			vec3 sgn = vec3((k & 1) != 0 ? 1.0 : -1.0, (k & 2) != 0 ? 1.0 : -1.0, (k & 4) != 0 ? 1.0 : -1.0);
			addSphere(s * sgn, r);
		}
	}
}

const int MAX_DEPTH = 80;
int chain[MAX_DEPTH];

// Inversion of a point in sphere k
vec3 invertPoint(vec3 p, int k) {
	vec3 d = p - centres[k];
	return centres[k] + d * (radii[k] * radii[k] / max(dot(d, d), 1e-12));
}

// Inversion of a sphere in sphere k: the image of a sphere is a sphere (exactly), which is what makes the
// distance estimate exact — every pearl is a known sphere in the original space
void invertSphere(inout vec3 c, inout float r, int k) {
	vec3 v = c - centres[k];
	float D = dot(v, v) - r * r;
	float f = radii[k] * radii[k] / (abs(D) < 1e-9 ? 1e-9 : D);
	c = centres[k] + v * f;
	r = abs(f) * r;
}

// A pearl of radius r: drawn as a solid ball when small enough, else an invisible wall the ray steps through
void consider(vec3 p, vec3 c, float r, inout float d, inout float wall) {
	float dist = length(p - c) - r;
	if (r <= PearlSize) d = min(d, dist);
	else wall = min(wall, abs(dist));
}

float DE(vec3 p) {
	vec3 q = p;
	escapeSteps = 0;
	for (int i = 0; i < MAX_DEPTH; i++) {
		if (i >= Iterations) break;
		int inside = -1;
		for (int k = 0; k < MAX_SPHERES; k++) {
			if (k >= sphereCount) break;
			vec3 d = q - centres[k];
			if (dot(d, d) < radii[k] * radii[k]) { inside = k; break; }
		}
		if (inside < 0) break;
		q = invertPoint(q, inside);
		chain[i] = inside;
		escapeSteps++;
	}
	float d = 1e9, wall = 1e9;
	// the pearl p sits in (the last sphere's image through the chain) and the pearls of the next depth inside it
	// (the other spheres' images) — exact spheres, so the distance is exact
	for (int k = 0; k < MAX_SPHERES; k++) {
		if (k >= sphereCount) break;
		vec3 c = centres[k];
		float r = radii[k];
		for (int i = MAX_DEPTH - 1; i >= 0; i--) {
			if (i < escapeSteps) invertSphere(c, r, chain[i]);
		}
		consider(p, c, r, d, wall);
	}
	if (escapeSteps == 0) {
		// outside every generator: the pearls just inside each of them as well, since the generators are usually walls
		for (int a = 0; a < MAX_SPHERES; a++) {
			if (a >= sphereCount) break;
			for (int b = 0; b < MAX_SPHERES; b++) {
				if (b >= sphereCount) break;
				if (b == a) continue;
				vec3 c = centres[b];
				float r = radii[b];
				invertSphere(c, r, a);
				consider(p, c, r, d, wall);
			}
		}
	}
	// an invisible pearl's surface is crossed in one small step, after which its inside is measured exactly
	d = min(d, wall + max(0.002, 0.25 * PearlSize));
	if (Cut) d = max(d, dot(p, normalize(CutNormal)) - CutOffset);
	return d;
}

vec3 baseColor(vec3 point, vec3 normal) {
	DE(point);
	float t = float(max(escapeSteps - 1, 0)) * ColorSpeed;    // the first pearls take ShellColor, deeper ones shade towards DeepColor
	vec3 base = mix(ShellColor, DeepColor, clamp(t, 0.0, 1.0));
	return base * (1.0 - HueTwist + HueTwist * (0.5 + 0.5 * cos(6.2831853 * t + vec3(0.0, 2.0, 4.0))));
}

#preset Default
FOV = 0.5
Eye = 1.3,1.3,-2.1
Target = 0,0,0
Up = 0,1,0
Configuration = 1
Iterations = 40
Count = 6
RingRadius = 1
Kiss = 1
PoleHeight = 0.8
PearlSize = 0.1
Cut = false
CutNormal = 0,1,0
CutOffset = 0
ColorSpeed = 0.3
HueTwist = 0.2
Detail = -3.2
DetailAO = -1.5
FudgeFactor = 0.9
MaxRaySteps = 200
OrbitStrength = 1
BackgroundColor = 0.2,0.22,0.3
GradientBackground = 0.3
#endpreset

#preset Big pearls
PearlSize = 0.3
Iterations = 24
Eye = 1.8,1.9,-2.8
#endpreset

#preset Towards the limit set
PearlSize = 0.04
Iterations = 60
Eye = 1.0,1.1,-1.7
Detail = -3.6
#endpreset

#preset Tetrahedron
Configuration = 2
PearlSize = 0.12
Iterations = 40
Eye = 1.5,1.4,-2.2
#endpreset

#preset Octahedron
Configuration = 3
PearlSize = 0.1
Iterations = 40
Eye = 1.5,1.4,-2.2
#endpreset

#preset Cube
Configuration = 4
Kiss = 1.05
PearlSize = 0.12
Iterations = 40
Eye = 1.6,1.3,-2.2
#endpreset

#preset Cut open
Configuration = 1
PearlSize = 2
Cut = true
CutNormal = 0,1,0
CutOffset = 0
Eye = 2.2,2.3,-3.4
#endpreset

#preset Schottky dust
Configuration = 0
Count = 6
Kiss = 0.93
PearlSize = 0.12
Iterations = 40
Eye = 1.2,1.2,-1.9
#endpreset
