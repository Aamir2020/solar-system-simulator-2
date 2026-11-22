#version 330
in vec3 normal;
in vec3 view_pos;
out vec4 frag;
uniform vec3 atmosphere_color;
uniform vec3 light_dir;
uniform float strength;
uniform float opacity;
uniform float log_far;
void main() {
    if (view_pos.z <= 0.) discard;
    vec3 n = normalize(normal);
    vec3 v = normalize(-view_pos);
    float facing = dot(n, v);
    if (facing <= 0.) discard;
    float limb = pow(1. - facing, 2.2);
    float daylight = .18 + .82 * smoothstep(-.30, .45, dot(n, normalize(light_dir)));
    float alpha = limb * daylight * strength * opacity;
    if (alpha < .004) discard;
    frag = vec4(atmosphere_color, min(alpha, .85));
    gl_FragDepth = log2(1. + view_pos.z) / log_far;
}
