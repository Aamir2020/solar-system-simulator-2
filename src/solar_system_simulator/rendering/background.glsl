#version 330
in vec2 uv;
out vec4 frag;
uniform vec2 viewport;
uniform bool stars;
uniform vec3 background_outer;
uniform vec3 background_inner;
uniform vec3 star_color;
float hash(vec2 p) { return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453); }
void main() {
    vec2 p=(uv*.5+.5)*viewport;
    float vignette=1.-clamp(length(uv)*.48,0.,1.);
    vec3 c=mix(background_outer,background_inner,vignette);
    if(stars) {
        vec2 cell=floor(p/39.);
        vec2 star=(cell+vec2(hash(cell),hash(cell+31.)))*39.;
        float d=length(p-star);
        float bright=pow(hash(cell+91.),5.);
        c+=star_color*exp(-d*d*1.8)*bright*.8;
    }
    frag=vec4(c,1.);
}
