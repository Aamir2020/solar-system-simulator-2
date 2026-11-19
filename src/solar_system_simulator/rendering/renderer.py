"""ModernGL sphere renderer, with a direction-sampled sky and logarithmic depth."""
import math
from importlib.resources import files

import moderngl
import numpy as np

from ..data.catalog import BODIES
from ..theme import COLORS
from .appearance import POINT_COLORS
from .geometry import axial_rotation, ring_mesh, sphere_mesh
from .scene import body_layout, orbit_trail, trail_vertices
from .textures import load_texture


def shader(name):
    return files('solar_system_simulator').joinpath(f'rendering/{name}.glsl').read_text()


def rgb(color):
    return tuple(int(color[i:i+2], 16)/255 for i in (1, 3, 5))


class SceneRenderer:
    def __init__(self, context):
        self.ctx = context
        self.resources = []
        try:
            self.body = self.own(context.program(vertex_shader=shader('sphere_vertex'), fragment_shader=shader('body')))
            self.background = self.own(context.program(vertex_shader=shader('background_vertex'), fragment_shader=shader('background')))
            self.trail = self.own(context.program(vertex_shader=shader('trail_vertex'), fragment_shader=shader('trail_fragment')))
            self.glow = self.own(context.program(vertex_shader=shader('quad'), fragment_shader=shader('glow')))
            self.sphere = self.mesh(self.body, sphere_mesh())
            self.rings = self.mesh(self.body, ring_mesh())
            quad = np.array([[-1,-1], [1,-1], [-1,1], [-1,1], [1,-1], [1,1]], dtype='f4')
            buffer = self.own(context.buffer(quad.tobytes()))
            self.background_vao = self.own(context.simple_vertex_array(self.background, buffer, 'in_pos'))
            self.glow_vao = self.own(context.simple_vertex_array(self.glow, buffer, 'in_pos'))
            self.trail_buffer = self.own(context.buffer(reserve=1500*6*6*4, dynamic=True))
            self.trail_vao = self.own(context.vertex_array(self.trail,
                [(self.trail_buffer, '3f 2f 1f', 'in_pos', 'in_offset', 'in_age')]))
            self.textures = [self.own(load_texture(context, body.name)) for body in BODIES]
            self.sky = self.own(load_texture(context, 'Sky', max_size=4096))
            self.night = self.own(load_texture(context, 'Earth night'))
            self.clouds = self.own(load_texture(context, 'Earth clouds'))
            self.ring_texture = self.own(load_texture(context, 'Saturn rings'))
            self.body['surface_map'].value = 0
            self.body['night_map'].value = 1
            self.body['cloud_map'].value = 2
            self.background['sky_map'].value = 0
        except Exception:
            self.release()
            raise

    def own(self, resource):
        self.resources.append(resource)
        return resource

    def mesh(self, program, geometry):
        vertices, indices = geometry
        vertex_buffer = self.own(self.ctx.buffer(vertices.tobytes()))
        index_buffer = self.own(self.ctx.buffer(indices.tobytes()))
        return self.own(self.ctx.vertex_array(program,
            [(vertex_buffer, '3f 2f', 'in_pos', 'in_uv')], index_buffer=index_buffer))

    def release(self):
        for resource in reversed(self.resources):
            resource.release()
        self.resources.clear()

    def draw(self, camera, positions, width, height, *, physical=False, effects=True,
             stars=True, sky_brightness=.45, history=None):
        ctx = self.ctx
        ctx.fbo.depth_mask = True
        ctx.clear(*rgb(COLORS['space']), 1., depth=1.)
        ctx.disable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
        ctx.enable(moderngl.BLEND)
        # Blend translucency inside the scene while preserving its opaque Qt backing.
        # Applying the RGB source factor to alpha would punch holes in the widget.
        ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA,
                          moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA)
        right, up, back = camera.basis
        tangent = math.tan(camera.fov/2)
        field = (tangent*width/height, tangent)
        bg = self.background
        bg['camera_right'].value = tuple(right)
        bg['camera_up'].value = tuple(up)
        bg['camera_back'].value = tuple(back)
        bg['field_of_view'].value = field
        bg['background_color'].value = rgb(COLORS['space'])
        bg['stars'].value = stars
        bg['brightness'].value = sky_brightness
        self.sky.use(0)
        self.background_vao.render()
        if positions is None:
            return
        layout = body_layout(camera, positions, width, height, physical)
        centers = camera.to_view(positions)/camera.distance
        far = max(100., float(np.linalg.norm(centers, axis=1).max())*2 + 2)
        if history is not None and len(history):
            far = max(far, float(np.linalg.norm(history-camera.center, axis=-1).max())/camera.distance*2 + 2)
        log_far = math.log2(1 + far)
        focal = (1/field[0], 1/field[1])
        program = self.body
        program['focal'].value = focal
        program['log_far'].value = log_far
        program['effects'].value = effects
        self.night.use(1)
        self.clouds.use(2)
        ctx.enable(moderngl.DEPTH_TEST)
        ctx.depth_func = '<='

        def body_uniforms(index, kind):
            rotation = axial_rotation(index)
            program['center'].value = tuple(centers[index])
            program['radius'].value = float(layout.world_radii[index]/camera.distance)
            program['rotation'].write((camera.view_rotation @ rotation).T.astype('f4').tobytes())
            light = positions[0] - positions[index]
            length = np.linalg.norm(light)
            light = light/length if length else np.array([0., 0., 1.])
            program['light_dir'].value = tuple(camera.view_rotation @ light)
            program['light_local'].value = tuple(rotation.T @ light)
            program['kind'].value = kind
            program['opacity'].value = float(1 - layout.point_weights[index])

        for index in range(len(BODIES)):
            if layout.point_weights[index] >= 1:
                continue
            if centers[index, 2] + layout.world_radii[index]/camera.distance <= 0:
                continue
            body_uniforms(index, index)
            self.textures[index].use(0)
            self.sphere.render()
        ctx.fbo.depth_mask = False
        if history is not None and len(history) >= 2:
            self.trail['viewport'].value = (width, height)
            self.trail['focal'].value = focal
            self.trail['log_far'].value = log_far
            for index, body in enumerate(BODIES):
                path = history[:, index]
                if index:
                    path = orbit_trail(path, history[:, 0])
                vertices = trail_vertices(camera, path, width, height)
                if not len(vertices):
                    continue
                self.trail_buffer.write(vertices.tobytes())
                self.trail['color'].value = rgb(body.color)
                self.trail_vao.render(vertices=len(vertices))
        if effects:
            body_uniforms(6, 9)
            self.ring_texture.use(0)
            self.rings.render()
        self.glow['viewport'].value = (width, height)
        self.glow['log_far'].value = log_far
        self.glow['effects'].value = effects
        # Composite distant points back-to-front, with depth testing against the
        # resolved bodies. The point pass also runs with decorative effects off.
        for index in np.argsort(layout.depths)[::-1]:
            weight = float(layout.point_weights[index])
            if not layout.visible[index] or (weight == 0 and (index != 0 or not effects)):
                continue
            self.glow['center'].value = tuple(layout.points[index])
            self.glow['extent'].value = float(max(layout.disc_radii[index]*3.5,
                                                  layout.light_radii[index]*4))
            depth = centers[index, 2]
            if weight > 0:
                depth -= layout.world_radii[index]/camera.distance
            self.glow['sun_depth'].value = float(max(depth, 1e-8))
            self.glow['light_color'].value = rgb(POINT_COLORS[index])
            self.glow['point_weight'].value = weight
            self.glow['core_radius'].value = float(layout.light_radii[index])
            self.glow['is_sun'].value = bool(index == 0)
            self.glow_vao.render()
        ctx.fbo.depth_mask = True
