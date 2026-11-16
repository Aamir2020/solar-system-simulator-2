#version 330
in float side;
in float age;
in float depth;
out vec4 frag;
uniform vec3 color;
uniform float log_far;
void main() {
    float alpha = (1. - smoothstep(.45, 1., abs(side))) * age * .68;
    if (alpha < .005) discard;
    frag = vec4(color, alpha);
    gl_FragDepth = log2(1. + depth) / log_far;
}
