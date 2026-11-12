#version 330
in vec2 uv;
out vec4 frag;
uniform vec3 color;
uniform int kind;
uniform bool effects;
uniform vec2 light_dir;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453); }
float noise(vec2 p) {
    vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f);
    return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),
               mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y);
}
void main() {
    vec2 q=uv*2.25;
    float r=length(q);
    float aa=max(fwidth(r), .002);
    vec3 c=color;
    float alpha=0.;
    if (kind==0) {
        float surface=1.-smoothstep(1.-aa,1.+aa,r);
        float glow=effects ? exp(-r*r*1.7)*.38 : 0.;
        c=mix(color,vec3(1.,.95,.76),max(0.,1.-r));
        alpha=max(surface,glow);
    } else {
        // Saturn rings are decorative, tilted discs rather than additional physics bodies.
        if (kind==6 && effects) {
            vec2 ring=vec2(q.x*.92+q.y*.38, -q.x*.38+q.y*.92);
            float ringR=length(vec2(ring.x,ring.y*2.9));
            float band=smoothstep(1.3,1.36,ringR)*(1.-smoothstep(1.95,2.02,ringR));
            float gap=1.-.65*exp(-pow((ringR-1.75)/.035,2.));
            alpha=band*gap*.7;
            c=color*mix(.65,1.,noise(vec2(ringR*80.,1.)));
        }
        if (r<1.+aa) {
            vec3 n=vec3(q.x,-q.y,sqrt(max(0.,1.-r*r)));
            vec2 tex=vec2(atan(n.x,n.z)*3.,asin(clamp(n.y,-1.,1.))*4.);
            float f=noise(tex*3.)*.6+noise(tex*8.)*.3+noise(tex*19.)*.1;
            vec3 base=color;
            if (kind==3) {
                float land=smoothstep(.49,.56,f);
                base=mix(vec3(.055,.25,.48),vec3(.25,.43,.24),land);
                base=mix(base,vec3(.9,.95,.96),smoothstep(.82,.98,abs(n.y)));
                base=mix(base,vec3(.9),smoothstep(.64,.73,noise(tex*5.+vec2(4,2)))*.55);
            } else if (kind==5 || kind==6) {
                float bands=sin(tex.y*9.+f*2.)*.5+.5;
                base*=.7+bands*.35;
                if (kind==5) base=mix(base,vec3(.64,.31,.18),
                    exp(-dot((tex-vec2(.5,-.9))*vec2(2.,4.),(tex-vec2(.5,-.9))*vec2(2.,4.))));
            } else { base*=.7+f*.5; }
            vec3 light=normalize(vec3(light_dir,.6));
            float diffuse=effects ? .15+.85*max(0.,dot(n,light)) : .6+.4*n.z;
            c=base*diffuse;
            alpha=1.-smoothstep(1.-aa,1.+aa,r);
        }
    }
    if(alpha<.002) discard;
    frag=vec4(c,alpha);
}
