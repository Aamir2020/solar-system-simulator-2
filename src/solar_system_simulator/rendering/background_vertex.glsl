#version 330
in vec2 in_pos;
out vec2 uv;
void main() {
    uv = in_pos;
    gl_Position = vec4(in_pos, 1., 1.);
}
