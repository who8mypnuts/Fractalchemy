#info Snowflake by Lewpen (fractals.com): spheres offset along the dominant axis. From the Distance Estimator Compendium, CC BY-NC-SA 3.0.
#include "MathUtils.frag"
#include "DE-Raytracer.frag"

#group Snowflake
uniform int Iterations; slider[1,20,40]
// Offset distance for each iteration of spheres
uniform float Distance; slider[0.5,1.1428,2]
// Scale factor for each iteration of spheres
uniform float Scale; slider[0.2,0.3868138,0.8]

float DE(vec3 pos) {
	float r = length(pos) - 1.0;
	float e = 1.0;
	float oScale = 1.0 / Scale;
	for (int i = 0; i < Iterations; i++) {
		vec3 v;
		if (abs(pos.x) > abs(pos.y)) v = abs(pos.x) > abs(pos.z) ? vec3(1.0, 0.0, 0.0) : vec3(0.0, 0.0, 1.0);
		else v = abs(pos.y) > abs(pos.z) ? vec3(0.0, 1.0, 0.0) : vec3(0.0, 0.0, 1.0);
		pos = abs(abs(pos) - Distance * v);
		pos *= oScale;
		e *= Scale;
		r = min(r, e * (length(pos) - 1.0));
	}
	return r;
}

#preset Default
FOV = 0.4
Eye = 2.4,2.0,-3.2
Target = 0,0,0
Up = 0,1,0
Detail = -3.4
DetailAO = -1.5
BaseColor = 0.95,0.97,1
OrbitStrength = 0
BackgroundColor = 0.3,0.35,0.45
GradientBackground = 0.3
#endpreset
