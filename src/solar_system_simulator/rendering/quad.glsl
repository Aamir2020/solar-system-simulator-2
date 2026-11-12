#version 330
in vec2 in_pos;
out vec2 uv;
uniform vec2 viewport;
uniform vec2 center;
uniform float extent;
void main() {
    uv = in_pos;
    vec2 p = center + in_pos * extent;
    gl_Position = vec4(p.x / viewport.x * 2.0 - 1.0, 1.0 - p.y / viewport.y * 2.0, 0, 1);
}
