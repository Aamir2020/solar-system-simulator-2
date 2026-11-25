#version 330
in vec2 uv;
out vec4 frag;
uniform float sun_depth;
uniform float log_far;
uniform vec3 light_color;
uniform float extent;
uniform float core_radius;
uniform float point_weight;
uniform bool effects;
uniform bool is_sun;
uniform float brightness;
uniform float exposure;
void main() {
    float r = length(uv);
    float distance_px = r * extent;
    float core = exp(-2. * pow(distance_px / core_radius, 2.));
    float halo = exp(-distance_px / core_radius * 1.3);
    float alpha = point_weight * (core + (effects ? halo * (is_sun ? .45 : .12) : 0.));
    if (effects && is_sun) {
        alpha += (1. - point_weight) * exp(-r * 5.) * .5;
    }
    alpha *= 1. - smoothstep(.7, 1., r);
    alpha *= brightness;
    alpha = 1. - exp(-alpha * exposure * 1.45);
    if (alpha < .002) discard;
    frag = vec4(light_color, min(alpha, 1.));
    gl_FragDepth = log2(1. + sun_depth) / log_far;
}
