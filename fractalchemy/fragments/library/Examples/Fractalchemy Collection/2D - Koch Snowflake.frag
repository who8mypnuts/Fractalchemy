#info Koch snowflake by folding: mirror, fold about the generator's line, scale by three — with the generator angle as a slider
#include "MathUtils.frag"
#include "Progressive2D.frag"

#group Koch
uniform int Iterations; slider[0,5,12]
// The generator's angle: 120 degrees is the Koch curve; other angles give its relatives
uniform float Angle; slider[60,120,180]
// Three curves around a triangle (the snowflake) or one curve
uniform bool Snowflake; checkbox[true]
// Thickness of the drawn curve
uniform float Thickness; slider[0,0.01,0.2]
// Colour by the distance field (contour lines) instead of a plain curve
uniform bool ShowField; checkbox[true]
uniform float ContourScale; slider[1,20,200]
uniform vec3 CurveColor; color[1.0,1.0,1.0]
uniform vec3 FieldColor; color[0.2,0.5,1.0]

vec2 N(float angle) { return vec2(sin(angle), cos(angle)); }

float koch(vec2 uv) {
	float scale = 1.0;
	uv.x = abs(uv.x);
	if (Snowflake) {
		uv.y += tan(radians(150.0)) * 0.5;
		vec2 n0 = N(radians(150.0));
		float d0 = dot(uv - vec2(0.5, 0.0), n0);
		uv -= n0 * max(0.0, d0) * 2.0;
	}
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
	float d = length(uv - vec2(clamp(uv.x, -1.0, 1.0), 0.0));
	return d / scale;
}

vec3 color(vec2 c) {
	float d = koch(c);
	if (d < Thickness) return CurveColor;
	if (!ShowField) return vec3(0.0);
	float rings = 0.5 + 0.5 * cos(d * ContourScale * 6.2831853);
	return FieldColor * (0.25 + 0.75 * rings) * exp(-d * 2.0);
}

#preset Default
Center = 0,0.1
Zoom = 0.9
Iterations = 5
Angle = 120
Snowflake = true
Thickness = 0.01
ShowField = true
ContourScale = 20
#endpreset

#preset Koch curve
Center = 0,0
Zoom = 1.2
Iterations = 6
Angle = 120
Snowflake = false
#endpreset

#preset Cesàro
Iterations = 6
Angle = 95
Snowflake = true
#endpreset
