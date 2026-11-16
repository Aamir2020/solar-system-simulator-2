#version 330
in vec3 in_pos;
in vec2 in_uv;
uniform vec3 center;
uniform float radius;
uniform mat3 rotation;
uniform vec2 focal;
uniform float log_far;
uniform int kind;
out vec2 uv;
out vec3 normal;
out vec3 view_pos;
out vec3 local_pos;
void main() {
    uv = in_uv;
    local_pos = in_pos;
    normal = rotation * (kind == 9 ? vec3(0, 0, 1) : in_pos);
    view_pos = center + rotation * in_pos * radius;
    float depth = view_pos.z;
    float z = 2. * log2(1. + max(depth, 0.)) / log_far - 1.;
    gl_Position = vec4(view_pos.xy * focal, z * depth, depth);
}
