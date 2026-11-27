#version 330
in vec2 uv;
in vec3 normal;
in vec3 view_pos;
in vec3 local_pos;
out vec4 frag;
uniform sampler2D surface_map;
uniform sampler2D night_map;
uniform sampler2D cloud_map;
uniform sampler2D ring_map;
uniform int kind;
uniform bool effects;
uniform bool shadows;
uniform vec3 light_dir;
uniform vec3 light_local;
uniform float log_far;
uniform float opacity;
uniform float cloud_offset;
uniform float exposure;
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
    vec4 sample_color = texture(surface_map, uv);
    vec3 base = pow(sample_color.rgb, vec3(2.2));
    vec3 n = normalize(normal);
    vec3 v = normalize(-view_pos);
    float sun = dot(n, normalize(light_dir));
    float visibility = effects && shadows && kind != 0 ? solar_visibility() : 1.;
    if (effects && shadows && kind == 6 && abs(light_local.z) > 1e-5) {
        float distance_to_plane = -local_pos.z/light_local.z;
        vec3 ring_hit = local_pos + light_local*distance_to_plane;
        float ring_radius = length(ring_hit.xy);
        if (distance_to_plane > 0. && ring_radius >= 1.24 && ring_radius <= 2.32) {
            float ring_alpha = texture(ring_map, vec2((ring_radius-1.24)/(2.32-1.24), .5)).a;
            visibility *= 1. - .88*ring_alpha;
        }
    }
    float alpha = 1.;
    vec3 color;
    if (kind == 9) {
        float lighting = effects ? .12 + .88*abs(sun)*visibility : .85;
        color = base * lighting;
        alpha = sample_color.a * .92;
    } else if (kind == 0) {
        color = base * 1.5;
    } else {
        float diffuse = effects ? .018 + 1.15*max(sun, 0.)*visibility : .6 + .4*max(dot(n, v), 0.);
        float cloud = 0.;
        if (kind == 3 && effects) {
            vec2 cloud_uv = vec2(fract(uv.x - cloud_offset), uv.y);
            cloud = pow(texture(cloud_map, cloud_uv).r, 1.5) * .72;
            base = mix(base, vec3(.88), cloud);
        }
        color = base * diffuse;
        if (kind == 3 && effects) {
            float night = max(1. - smoothstep(-.18, .12, sun),
                              (1.-visibility)*smoothstep(0., .2, sun));
            color += pow(texture(night_map, uv).rgb, vec3(2.2)) * night * (1.-cloud) * 1.4;
            float ocean = smoothstep(base.r*1.2, base.r*1.2+.07, base.b) * (1.-cloud);
            color += vec3(.25) * ocean * pow(max(dot(n, normalize(normalize(light_dir)+v)), 0.), 48.) * max(sun, 0.) * visibility;
            float rim = pow(1. - max(dot(n, v), 0.), 5.) * smoothstep(-.3, .5, sun);
            color += vec3(.025, .09, .22) * rim;
        }
    }
    alpha *= opacity;
    if (alpha < .005) discard;
    color = 1. - exp(-max(color, vec3(0)) * exposure * 1.45);
    frag = vec4(pow(color, vec3(1./2.2)), alpha);
    gl_FragDepth = log2(1. + view_pos.z) / log_far;
}
