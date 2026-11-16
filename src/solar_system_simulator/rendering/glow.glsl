#version 330
in vec2 uv;
out vec4 frag;
uniform float sun_depth;
uniform float log_far;
void main() {
    float r = length(uv);
    float alpha = exp(-r * 5.) * (1. - smoothstep(.7, 1., r)) * .5;
    if (alpha < .002) discard;
    frag = vec4(1., .58, .17, alpha);
    gl_FragDepth = log2(1. + sun_depth) / log_far;
}
