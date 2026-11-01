#info The Marble Marcher levels by michael0884 (CodeParade): one fold-and-scale formula, eleven parameter sets as presets. CC BY-NC-SA 3.0 via the Distance Estimator Compendium.
#define providesColor
#include "MathUtils.frag"
#include "DE-Raytracer.frag"

#group Level
uniform int Iterations; slider[1,11,20]
uniform float Scale; slider[1,1.8,3]
uniform float Angle1; slider[-10,-0.12,10]
uniform float Angle2; slider[-10,0.5,10]
uniform vec3 Shift; slider[(-12,-12,-12),(-2.12,-2.75,0.49),(12,12,12)]
uniform vec3 LevelColor; color[0.42,0.38,0.19]
uniform float BoxSize; slider[1,6,10]

vec3 orbitColor;

float DE(vec3 p) {
	vec2 a1 = vec2(sin(Angle1), cos(Angle1));
	vec2 a2 = vec2(sin(Angle2), cos(Angle2));
	mat2 rmZ = mat2(a1.y, a1.x, -a1.x, a1.y);
	mat2 rmX = mat2(a2.y, a2.x, -a2.x, a2.y);
	float s = 1.0;
	orbitColor = vec3(0.0);
	for (int i = 0; i < Iterations; ++i) {
		p = abs(p);
		p.xy *= rmZ;
		p.xy += min(p.x - p.y, 0.0) * vec2(-1.0, 1.0);
		p.xz += min(p.x - p.z, 0.0) * vec2(-1.0, 1.0);
		p.yz += min(p.y - p.z, 0.0) * vec2(-1.0, 1.0);
		p.yz *= rmX;
		p *= Scale;
		s *= Scale;
		p += Shift;
		orbitColor = max(orbitColor, p * LevelColor);
	}
	vec3 d = abs(p) - vec3(BoxSize);
	return (min(max(d.x, max(d.y, d.z)), 0.0) + length(max(d, 0.0))) / s;
}

vec3 baseColor(vec3 point, vec3 normal) {
	DE(point);
	return clamp(orbitColor, 0.0, 1.0);
}

#preset Default
FOV = 0.5
Eye = 4.5,3.2,-6.0
Target = 0,0,0
Up = 0,1,0
Iterations = 11
Scale = 1.8
Angle1 = -0.12
Angle2 = 0.5
Shift = -2.12,-2.75,0.49
LevelColor = 0.42,0.38,0.19
BoxSize = 6
Detail = -3.2
DetailAO = -1.4
OrbitStrength = 1
BackgroundColor = 0.3,0.35,0.45
GradientBackground = 0.3
#endpreset

#preset Too many trees
Scale = 1.9073
Angle1 = -9.83
Angle2 = -1.16
Shift = -3.508,-3.593,3.295
LevelColor = 0,0.12,0
#endpreset

#preset Hole in one
Scale = 2.02
Angle1 = -1.57
Angle2 = 1.62
Shift = -3.31,6.19,1.53
LevelColor = 0.12,0,0
#endpreset

#preset Around the world
Scale = 1.65
Angle1 = 0.37
Angle2 = 5.26
Shift = -1.41,-0.22,-0.77
LevelColor = 0.14,0,0.31
#endpreset

#preset Beware of bumps
Scale = 1.66
Angle1 = 1.52
Angle2 = 0.19
Shift = -3.83,-1.94,-1.09
LevelColor = 0.42,0.38,0.19
#endpreset

#preset Mountain climbing
Scale = 1.58
Angle1 = -1.45
Angle2 = 3.95
Shift = -1.55,-0.13,-2.52
LevelColor = 0,0,0
#endpreset

#preset Mind the gap
Scale = 1.81
Angle1 = -4.84
Angle2 = -2.99
Shift = -2.905,0.765,-4.165
LevelColor = 0.251,0.337,0.161
#endpreset

#preset The Sponge
Scale = 1.88
Angle1 = 1.52
Angle2 = 4.91
Shift = -4.54,-1.26,0.1
LevelColor = 0,0.3,0
#endpreset

#preset Around the Citadel
Scale = 2.0773
Angle1 = -9.66
Angle2 = -1.34
Shift = -1.238,-1.533,1.085
LevelColor = 0.42,0.38,0.19
#endpreset

#preset Mega Citadel
Scale = 1.4731
Angle1 = 0
Angle2 = 0
Shift = -10.27,3.28,-1.9
LevelColor = 1,0.07,1
#endpreset

#preset Build up speed
Scale = 2.08
Angle1 = -4.79
Angle2 = 3.16
Shift = -7.43,5.96,-6.23
LevelColor = 0.16,0.38,0.15
#endpreset
