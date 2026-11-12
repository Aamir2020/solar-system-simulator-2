#version 330
in vec2 in_pos;
in float in_side;
in float in_age;
out float side;
out float age;
uniform vec2 viewport;
void main() {
    side=in_side;
    age=in_age;
    gl_Position=vec4(in_pos.x/viewport.x*2.-1.,1.-in_pos.y/viewport.y*2.,0,1);
}
