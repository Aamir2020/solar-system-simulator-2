#version 330
in vec3 in_pos;
in vec2 in_offset;
in float in_age;
out float side;
out float age;
out float depth;
uniform vec2 viewport;
uniform vec2 focal;
uniform float log_far;
void main() {
    float sides[6] = float[6](-1., 1., -1., -1., 1., 1.);
    side = sides[gl_VertexID % 6];
    age = in_age;
    depth = in_pos.z;
    float z = 2. * log2(1. + depth) / log_far - 1.;
    gl_Position = vec4(in_pos.xy*focal + in_offset*vec2(2., -2.)/viewport*depth, z*depth, depth);
}
