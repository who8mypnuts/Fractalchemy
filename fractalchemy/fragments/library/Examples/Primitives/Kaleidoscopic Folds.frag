#info Kaleidoscopic IFS from the folds of Primitives.frag: fold, scale, offset, repeat; a primitive at the end
#define providesInit
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Primitives.frag"

#group IFS
uniform int Iterations; slider[1,8,20]
// The fold applied every iteration
uniform int Fold; menu[0, Menger (octahedral);Sierpinski (tetrahedral);Kaleido 5;Kaleido 7;Mirror (abs)]
uniform float Scale; slider[1.0,2.0,4.0]
uniform vec3 Offset; slider[(-3,-3,-3),(1,1,1),(3,3,3)]
uniform vec3 Rotation; slider[(-180,-180,-180),(0,0,0),(180,180,180)]
// Knighty's Menger trick: wrap z back up after the scaling (needed for the sponge, not for Sierpinski)
uniform bool MengerShift; checkbox[true]
// What is placed at the end of the folds
uniform int Shape; menu[0, Box;Sphere;Octahedron;Torus]
uniform float ShapeSize; slider[0.01,1.0,3.0]

mat3 rot;
void init() { rot = rotationMatrixXYZ(Rotation); }

vec3 fold(vec3 p) {
	if (Fold == 0) return foldMenger(p);
	if (Fold == 1) return foldSierpinski(p);
	if (Fold == 2) { p.xz = foldKaleido(p.xz, 5.0); return p; }
	if (Fold == 3) { p.xz = foldKaleido(p.xz, 7.0); return p; }
	return abs(p);
}

float shape(vec3 p) {
	if (Shape == 0) return sdBox(p, vec3(ShapeSize));
	if (Shape == 1) return sdSphere(p, ShapeSize);
	if (Shape == 2) return sdOctahedron(p, ShapeSize);
	return sdTorus(p, ShapeSize, ShapeSize * 0.3);
}

float DE(vec3 p) {
	float s = 1.0;
	for (int i = 0; i < Iterations; i++) {
		p = fold(p);
		p = rot * p;
		p = p * Scale - Offset * (Scale - 1.0);
		if (MengerShift && p.z < -0.5 * Offset.z * (Scale - 1.0)) p.z += Offset.z * (Scale - 1.0);
		s *= Scale;
	}
	return shape(p) / s;
}

#preset Default
FOV = 0.4
Eye = 3.2,2.4,-3.6
Target = 0,0,0
Up = 0,1,0
Iterations = 6
Fold = 0
Scale = 3
Offset = 1,1,1
Rotation = 0,0,0
MengerShift = true
Shape = 0
ShapeSize = 1
Detail = -3.0
DetailAO = -1.3
BaseColor = 0.8,0.85,0.9
OrbitStrength = 0.6
X = 0.5,0.6,0.6,0.7
Y = 1,0.6,0,0.4
Z = 0.8,0.78,1,0.5
R = 0.4,0.7,1,0.12
BackgroundColor = 0.3,0.33,0.4
GradientBackground = 0.3
#endpreset

#preset Sierpinski
Iterations = 10
Fold = 1
Scale = 2
Offset = 1,1,1
MengerShift = false
Shape = 2
ShapeSize = 1
#endpreset

#preset Kaleido
Iterations = 8
Fold = 2
Scale = 2
Offset = 1.2,0.6,1
Rotation = 10,25,0
MengerShift = false
Shape = 3
ShapeSize = 0.6
#endpreset
