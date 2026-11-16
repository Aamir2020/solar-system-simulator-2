#version 330
in vec2 uv;
out vec4 frag;
uniform sampler2D sky_map;
uniform vec3 camera_right;
uniform vec3 camera_up;
uniform vec3 camera_back;
uniform vec2 field_of_view;
uniform bool stars;
uniform float brightness;
uniform vec3 background_color;
const float PI = 3.141592653589793;
void main() {
    vec3 color = background_color;
    if (stars) {
        vec3 direction = normalize(camera_right*uv.x*field_of_view.x + camera_up*uv.y*field_of_view.y - camera_back);
        // Fixed presentation orientation; the sky remains anchored to world directions.
        direction = mat3(0., -1., 0., .507538, 0., .861629, -.861629, 0., .507538) * direction;
        direction = mat3(1., 0., 0., 0., .866025, .5, 0., -.5, .866025) * direction;
        vec2 coord = vec2(.5 - atan(direction.y, direction.x)/(2.*PI), .5 - asin(clamp(direction.z, -1., 1.))/PI);
        color += texture(sky_map, coord).rgb * brightness;
    }
    frag = vec4(color, 1.);
}
