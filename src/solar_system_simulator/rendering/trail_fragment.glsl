#version 330
in float side;
in float age;
out vec4 frag;
uniform vec3 color;
void main() {
    float edge=1.-smoothstep(.35,1.,abs(side));
    frag=vec4(color,edge*pow(age,1.7)*.65);
}
