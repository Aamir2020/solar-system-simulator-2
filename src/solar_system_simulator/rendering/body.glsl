#version 330
in vec2 uv;
in vec3 normal;
in vec3 view_pos;
in vec3 local_pos;
out vec4 frag;
uniform sampler2D surface_map;
uniform sampler2D night_map;
uniform sampler2D cloud_map;
uniform int kind;
uniform bool effects;
uniform vec3 light_dir;
uniform vec3 light_local;
uniform float log_far;
uniform float opacity;
void main() {
    if (view_pos.z <= 0.) discard;
    vec4 sample_color = texture(surface_map, uv);
    vec3 base = pow(sample_color.rgb, vec3(2.2));
    vec3 n = normalize(normal);
    vec3 v = normalize(-view_pos);
    float sun = dot(n, normalize(light_dir));
    float alpha = 1.;
    vec3 color;
    if (kind == 9) {
        float t = -dot(local_pos, light_local);
        float shadow = t > 0. ? mix(.15, 1., smoothstep(.9, 1.1, dot(local_pos, local_pos)-t*t)) : 1.;
        float lighting = effects ? (.12 + .88*abs(sun))*shadow : .85;
        color = base * lighting;
        alpha = sample_color.a * .92;
    } else if (kind == 0) {
        color = base * 1.5;
    } else {
        float diffuse = effects ? .018 + 1.15*max(sun, 0.) : .6 + .4*max(dot(n, v), 0.);
        float cloud = 0.;
        if (kind == 3 && effects) {
            cloud = pow(texture(cloud_map, uv).r, 1.5) * .72;
            base = mix(base, vec3(.88), cloud);
        }
        color = base * diffuse;
        if (kind == 3 && effects) {
            float night = 1. - smoothstep(-.18, .12, sun);
            color += pow(texture(night_map, uv).rgb, vec3(2.2)) * night * (1.-cloud) * 1.4;
            float ocean = smoothstep(base.r*1.2, base.r*1.2+.07, base.b) * (1.-cloud);
            color += vec3(.25) * ocean * pow(max(dot(n, normalize(normalize(light_dir)+v)), 0.), 48.) * max(sun, 0.);
            float rim = pow(1. - max(dot(n, v), 0.), 5.) * smoothstep(-.3, .5, sun);
            color += vec3(.025, .09, .22) * rim;
        }
    }
    alpha *= opacity;
    if (alpha < .005) discard;
    frag = vec4(pow(max(color, vec3(0)), vec3(1./2.2)), alpha);
    gl_FragDepth = log2(1. + view_pos.z) / log_far;
}
