#version 330
in vec2 uv;
out vec4 frag;
uniform vec3 color;
uniform int kind;
uniform bool effects;
uniform vec2 light_dir;
uniform sampler2D surface_map;
const float PI = 3.141592653589793;
void main() {
    vec2 q = uv * 2.25;
    float r = length(q);
    float aa = max(fwidth(r), .002);
    vec3 c = color;
    float alpha = 0.;
    // Decorative Saturn rings surround the image-mapped planetary disc.
    if (kind == 6 && effects) {
        vec2 ring = vec2(q.x*.92 + q.y*.38, -q.x*.38 + q.y*.92);
        float ringR = length(vec2(ring.x, ring.y*2.9));
        float band = smoothstep(1.3, 1.36, ringR) * (1. - smoothstep(1.95, 2.02, ringR));
        float gap = 1. - .65 * exp(-pow((ringR-1.75)/.035, 2.));
        alpha = band * gap * .7;
        c = color * (.82 + .1 * sin(ringR*190.));
    }
    if (kind == 0 && effects) {
        alpha = exp(-r*r*1.7) * .38;
    }
    if (r < 1. + aa) {
        vec3 n = vec3(q.x, -q.y, sqrt(max(0., 1.-r*r)));
        // Bundled equirectangular maps arrive top-row first from QImage.
        vec2 tex_uv = vec2(.5 + atan(n.x, n.z)/(2.*PI),
                           .5 - asin(clamp(n.y, -1., 1.))/PI);
        vec3 base = texture(surface_map, tex_uv).rgb;
        float diffuse = kind == 0 ? 1. :
            (effects ? .16 + .84*max(0., dot(n, normalize(vec3(light_dir, .6))))
                     : .65 + .35*n.z);
        c = base * diffuse;
        alpha = 1. - smoothstep(1.-aa, 1.+aa, r);
    }
    if (alpha < .002) discard;
    frag = vec4(c, alpha);
}
