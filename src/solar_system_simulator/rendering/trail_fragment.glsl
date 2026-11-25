#version 330
noperspective in float side;
in float age;
in float depth;
out vec4 frag;
uniform vec3 color;
uniform float log_far;
uniform float exposure;
void main() {
    float alpha = (1. - smoothstep(.45, 1., abs(side))) * smoothstep(0., 1., age) * .68;
    alpha = 1. - exp(-alpha * exposure * 1.45);
    if (alpha < .005) discard;
    frag = vec4(color, alpha);
    gl_FragDepth = log2(1. + depth) / log_far;
}
