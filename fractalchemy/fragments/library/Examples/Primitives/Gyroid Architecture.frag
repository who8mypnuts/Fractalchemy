#info A gyroid shell carved into a twisted box, with onion layers (Primitives.frag)
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Primitives.frag"

#group Gyroid
uniform float Frequency; slider[1,6,20]
uniform float Thickness; slider[0.005,0.03,0.2]
uniform float Bias; slider[-1,0,1]
uniform float Twist; slider[-3,0.6,3]
uniform vec3 BoxSize; slider[(0.1,0.1,0.1),(1,1.4,1),(3,3,3)]
// Hollow the box first (0 = solid)
uniform float Shell; slider[0,0,0.5]

float DE(vec3 p) {
	vec3 q = opTwist(p, Twist);
	float box = sdBox(p, BoxSize);
	if (Shell > 0.0) box = opOnion(box, Shell);
	float g = sdGyroid(q, Frequency, Thickness, Bias);
	return max(box, g);
}

#preset Default
FOV = 0.4
Eye = 3.0,2.6,-4.2
Target = 0,0,0
Up = 0,1,0
Detail = -3.2
DetailAO = -1.4
BaseColor = 0.9,0.9,0.85
OrbitStrength = 0
BackgroundColor = 0.3,0.33,0.4
GradientBackground = 0.3
#endpreset
