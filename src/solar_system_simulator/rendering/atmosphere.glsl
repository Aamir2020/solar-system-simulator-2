#version 330
in vec3 normal;
in vec3 view_pos;
out vec4 frag;
uniform vec3 atmosphere_color;
uniform vec3 light_dir;
uniform float strength;
uniform float opacity;
uniform float log_far;
uniform float exposure;
uniform bool shadows;
uniform vec3 sun_center;
uniform float sun_radius;
uniform int occluder_count;
uniform vec4 occluders[8];
const float PI = 3.141592653589793;

float circle_overlap(float a, float b, float distance) {
    if (distance >= a + b) return 0.;
    float smaller = min(a, b);
    if (distance <= abs(a - b)) return PI * smaller * smaller;
    float first = acos(clamp((distance*distance + a*a - b*b) / (2.*distance*a), -1., 1.));
    float second = acos(clamp((distance*distance + b*b - a*a) / (2.*distance*b), -1., 1.));
    float area = max((-distance+a+b)*(distance+a-b)*(distance-a+b)*(distance+a+b), 0.);
    return a*a*first + b*b*second - .5*sqrt(area);
}

float solar_visibility() {
    vec3 to_sun = sun_center - view_pos;
    float sun_distance = length(to_sun);
    float sun_angle = asin(clamp(sun_radius/sun_distance, 0., 1.));
    vec3 sun_direction = to_sun/sun_distance;
    float visibility = 1.;
    for (int i = 0; i < 8; ++i) {
        if (i >= occluder_count) break;
        vec3 to_occluder = occluders[i].xyz - view_pos;
        float occluder_distance = length(to_occluder);
        if (occluder_distance >= sun_distance || occluder_distance <= occluders[i].w) continue;
        float occluder_angle = asin(clamp(occluders[i].w/occluder_distance, 0., 1.));
        float separation = acos(clamp(dot(sun_direction, to_occluder/occluder_distance), -1., 1.));
        float hidden = circle_overlap(sun_angle, occluder_angle, separation) /
                       max(PI*sun_angle*sun_angle, 1e-12);
        visibility *= 1. - clamp(hidden, 0., 1.);
    }
    return visibility;
}

void main() {
    if (view_pos.z <= 0.) discard;
    vec3 n = normalize(normal);
    vec3 v = normalize(-view_pos);
    float facing = dot(n, v);
    if (facing <= 0.) discard;
    float limb = pow(1. - facing, 2.2);
    float visibility = shadows ? solar_visibility() : 1.;
    float direct = smoothstep(-.30, .45, dot(n, normalize(light_dir))) * visibility;
    float daylight = .18 + .82*direct;
    float alpha = limb * daylight * strength * opacity;
    alpha = 1. - exp(-alpha * exposure * 1.45);
    if (alpha < .004) discard;
    frag = vec4(atmosphere_color, min(alpha, .85));
    gl_FragDepth = log2(1. + view_pos.z) / log_far;
}
