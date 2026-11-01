#info Primitives Gallery: every distance primitive of Primitives.frag, one at a time
#define providesInit
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Primitives.frag"

#group Primitive
// Which primitive to show
uniform int Shape; menu[0, Sphere;Box;Round box;Box frame;Chamfer box;Ellipsoid;Cylinder;Rounded cylinder;Cylinder6;Cylinder8;Capsule;Capsule line;Torus;Torus82;Capped torus;Link;Disc;Solid angle;Wavy sphere;Cone;Capped cone;Round cone;Pyramid;Hex prism;Tri prism;Oct prism;Rhombus;Octahedron;Icosahedron;Dodecahedron;Rhombic dodecahedron;GDF octahedron;GDF dodecahedron;GDF icosahedron;GDF truncated octahedron;GDF truncated icosahedron;Gyroid ball;Schwarz P ball;Gyroid torus;Star;Twisted tube;Cross]
// Overall size
uniform float Size; slider[0.1,1.0,3.0]
// Secondary radius / thickness / height, by primitive
uniform float Radius; slider[0.01,0.3,2.0]
// Height / length, by primitive
uniform float Height; slider[0.05,0.8,3.0]
// Exponent of the GDF polyhedra (large = sharp)
uniform float Exponent; slider[1,16,64]
// Rounding applied to everything
uniform float Rounding; slider[0,0,0.5]
// Spin the shape
uniform vec3 Rotation; slider[(-180,-180,-180),(20,-30,0),(180,180,180)]

mat3 spin;
void init() { spin = rotationMatrixXYZ(Rotation); }

float shape(vec3 p) {
	float s = Size;
	if (Shape == 0) return sdSphere(p, s);
	if (Shape == 1) return sdBox(p, vec3(s, s * 0.6, s * 0.8));
	if (Shape == 2) return sdRoundBox(p, vec3(s * 0.8), Radius);
	if (Shape == 3) return sdBoxFrame(p, vec3(s), Radius * 0.3);
	if (Shape == 4) return sdChamferBox(p, vec3(s, s * 0.7, s * 0.5), Radius, Rounding);
	if (Shape == 5) return sdEllipsoid(p, vec3(s, s * 0.5, s * 0.7));
	if (Shape == 6) return sdCylinder(p, s * 0.6, Height);
	if (Shape == 7) return sdRoundedCylinder(p, s * 0.5, Radius, Height);
	if (Shape == 8) return sdCylinder6(p, s * 0.6, Height);
	if (Shape == 9) return sdCylinder8(p, s * 0.6, Height);
	if (Shape == 10) return sdCapsule(p, Height, Radius);
	if (Shape == 11) return sdCapsuleLine(p, vec3(-s, -0.5, 0.0), vec3(s, 0.5, 0.3), Radius);
	if (Shape == 12) return sdTorus(p, s, Radius);
	if (Shape == 13) return sdTorus82(p, vec2(s, Radius));
	if (Shape == 14) return sdCappedTorus(p, 2.0, s, Radius);
	if (Shape == 15) return sdLink(p, Height * 0.5, s * 0.6, Radius);
	if (Shape == 16) return sdDisc(p, s) - Radius * 0.3;
	if (Shape == 17) return sdSolidAngle(p, 1.0, s);
	if (Shape == 18) return sdWavySphere(p, s * 0.5, 7.0, 0.4);
	if (Shape == 19) return sdCone(p - vec3(0.0, -Height * 0.5, 0.0), s * 0.7, Height);
	if (Shape == 20) return sdCappedCone(p, Height * 0.5, s * 0.7, s * 0.3);
	if (Shape == 21) return sdRoundCone(p - vec3(0.0, -Height * 0.5, 0.0), s * 0.5, Radius, Height);
	if (Shape == 22) return sdPyramid(p / s + vec3(0.0, 0.5, 0.0), Height) * s;
	if (Shape == 23) return sdHexPrism(p, s * 0.7, Height * 0.5);
	if (Shape == 24) return sdTriPrism(p, vec2(s, Height * 0.5));
	if (Shape == 25) return sdOctPrism(p, s * 0.7, Height * 0.5);
	if (Shape == 26) return sdRhombus(p, s, s * 0.6, Height * 0.2, Radius * 0.3);
	if (Shape == 27) return sdOctahedron(p, s);
	if (Shape == 28) return sdIcosahedron(p, s);
	if (Shape == 29) return sdDodecahedron(p, s);
	if (Shape == 30) return sdRhombicDodecahedron(p, s);
	if (Shape == 31) return fGDF(p, s, Exponent, 3, 6);
	if (Shape == 32) return fGDF(p, s, Exponent, 13, 18);
	if (Shape == 33) return fGDF(p, s, Exponent, 3, 12);
	if (Shape == 34) return fGDF(p, s, Exponent, 0, 6);
	if (Shape == 35) return fGDF(p, s, Exponent, 3, 18);
	if (Shape == 36) return max(sdGyroid(p, 7.0 / s, Radius * 0.2, 0.0), sdSphere(p, s));
	if (Shape == 37) return max(sdSchwarzP(p, 5.0 / s, Radius * 0.3), sdSphere(p, s));
	if (Shape == 38) return sdGyroidTorus(p * 6.0 / s, 6.0, 2.0, 0.3) * s / 6.0;
	if (Shape == 39) return sdStar(p / (s * 8.0)) * s * 8.0;
	if (Shape == 40) return sdTwistedTube(p, s, Radius * 0.3);
	return max(sdCross(p, Radius), sdSphere(p, s * 1.5));
}

float DE(vec3 p) {
	return shape(spin * p) - Rounding;
}

#preset Default
FOV = 0.4
Eye = 2.6,2.2,-3.4
Target = 0,0,0
Up = 0,1,0
Shape = 29
Size = 1
Radius = 0.3
Height = 0.8
Exponent = 16
Rounding = 0
Rotation = 20,-30,0
Detail = -2.8
DetailAO = -1.2
BaseColor = 0.85,0.85,0.85
OrbitStrength = 0
BackgroundColor = 0.35,0.4,0.5
GradientBackground = 0.3
#endpreset
