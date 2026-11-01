#info Tutorial 4: animate with time, keyframes and easing curves, then render to files
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Primitives.frag"

#group Animation
// STEP 1: `time` is the animation clock in seconds; switch the toolbar to Animation mode and press Play (F11) to see it run.
uniform float time;
uniform float Speed; slider[0,1,5]
uniform float Orbit; slider[0,1.2,3]
// STEP 2: Any slider can also follow an easing curve: select it, press F7, choose start and end values and frames.
uniform float Spin; slider[-360,0,360]

float DE(vec3 p) {
	float a = time * Speed;
	vec3 q = rot3(vec3(0.0, 1.0, 0.0), radians(Spin)) * p;
	float ring = sdTorus(q, 1.0, 0.15);
	vec3 ball = vec3(cos(a), 0.3 * sin(2.0 * a), sin(a)) * Orbit;
	return min(ring, sdSphere(q - ball, 0.3));
}

// STEP 3: Keyframes: fly somewhere and press F8 — a KeyFrame.nnnn preset is written; two or more make a camera path.
// STEP 4: Camera ▸ Record camera path samples the camera while you fly and writes the keyframes for you.
// STEP 5: Render ▸ Render… (Ctrl+R): tick Animation, set the frame range, choose a format (and a video with ffmpeg).
#preset Default
FOV = 0.4
Eye = 3.0,2.0,-4.0
Target = 0,0,0
Up = 0,1,0
Speed = 1
Orbit = 1.2
Spin = 0
Detail = -2.8
BaseColor = 0.9,0.8,0.6
OrbitStrength = 0
BackgroundColor = 0.3,0.35,0.45
GradientBackground = 0.3
#endpreset

#preset KeyFrame.0001
FOV = 0.4
Eye = 3.0,2.0,-4.0
Target = 0,0,0
Up = 0,1,0
#endpreset

#preset KeyFrame.0002
FOV = 0.4
Eye = -3.5,1.0,-3.0
Target = 0,0,0
Up = 0,1,0
#endpreset

#preset KeyFrame.0003
FOV = 0.4
Eye = -1.0,3.5,3.5
Target = 0,0,0
Up = 0,1,0
#endpreset
