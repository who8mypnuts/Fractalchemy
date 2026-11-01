#info Boolean Operations: union, subtraction, intersection and their smooth versions on a box and a sphere
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Primitives.frag"

#group Operation
// Which operation combines the two shapes
uniform int Operation; menu[3, Union;Subtract (box minus sphere);Intersect;Smooth union;Smooth subtract;Smooth intersect;Onion of the union]
// Blend radius of the smooth operations
uniform float Smoothness; slider[0.001,0.25,1.0]
// Where the sphere sits
uniform vec3 SphereOffset; slider[(-2,-2,-2),(0.7,0.4,-0.4),(2,2,2)]
uniform float SphereRadius; slider[0.05,0.75,2.0]
uniform vec3 BoxSize; slider[(0.05,0.05,0.05),(0.8,0.6,0.7),(2,2,2)]
// Rounding of the box edges
uniform float BoxRounding; slider[0,0.05,0.5]
// Wall thickness of the onion
uniform float Thickness; slider[0.005,0.05,0.3]

float DE(vec3 p) {
	float a = sdRoundBox(p, BoxSize, BoxRounding);
	float b = sdSphere(p - SphereOffset, SphereRadius);
	if (Operation == 0) return opUnion(a, b);
	if (Operation == 1) return opSubtract(a, b);
	if (Operation == 2) return opIntersect(a, b);
	if (Operation == 3) return opSmoothUnion(a, b, Smoothness);
	if (Operation == 4) return opSmoothSubtract(a, b, Smoothness);
	if (Operation == 5) return opSmoothIntersect(a, b, Smoothness);
	return max(opOnion(opSmoothUnion(a, b, Smoothness), Thickness), p.y);   // cut open at y = 0 to see inside
}

#preset Default
FOV = 0.4
Eye = 2.4,2.0,-3.2
Target = 0,0,0
Up = 0,1,0
Detail = -2.8
DetailAO = -1.2
BaseColor = 0.9,0.75,0.55
OrbitStrength = 0
BackgroundColor = 0.35,0.4,0.5
GradientBackground = 0.3
#endpreset
