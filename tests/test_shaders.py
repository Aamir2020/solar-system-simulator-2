"""Compile the actual production shaders on Mesa/EGL, without a desktop session.

Optional on hosts without EGL; compilation failures on a working context fail the test.
Qt/ModernGL integration is exercised separately on a desktop-capable installation.
"""
import ctypes as C
import ctypes.util
from pathlib import Path
import unittest


class ShaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ctypes.util.find_library('EGL') or not ctypes.util.find_library('GL'):
            raise unittest.SkipTest('EGL/OpenGL libraries are unavailable')
        cls.egl=C.CDLL(ctypes.util.find_library('EGL'))
        cls.gl=C.CDLL(ctypes.util.find_library('GL'))
        E=cls.egl
        signatures={
            'eglGetPlatformDisplay':(C.c_void_p,[C.c_uint,C.c_void_p,C.POINTER(C.c_int)]),
            'eglInitialize':(C.c_uint,[C.c_void_p,C.POINTER(C.c_int),C.POINTER(C.c_int)]),
            'eglChooseConfig':(C.c_uint,[C.c_void_p,C.POINTER(C.c_int),C.POINTER(C.c_void_p),C.c_int,C.POINTER(C.c_int)]),
            'eglBindAPI':(C.c_uint,[C.c_uint]),
            'eglCreateContext':(C.c_void_p,[C.c_void_p,C.c_void_p,C.c_void_p,C.POINTER(C.c_int)]),
            'eglCreatePbufferSurface':(C.c_void_p,[C.c_void_p,C.c_void_p,C.POINTER(C.c_int)]),
            'eglMakeCurrent':(C.c_uint,[C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p]),
            'eglDestroyContext':(C.c_uint,[C.c_void_p,C.c_void_p]),
            'eglDestroySurface':(C.c_uint,[C.c_void_p,C.c_void_p]),
            'eglTerminate':(C.c_uint,[C.c_void_p]),
        }
        for name,(result,args) in signatures.items():
            if not hasattr(E,name):raise unittest.SkipTest(f'{name} is unavailable')
            fn=getattr(E,name);fn.restype=result;fn.argtypes=args
        cls.display=E.eglGetPlatformDisplay(0x31DD,None,None)
        major,minor=C.c_int(),C.c_int()
        if not E.eglInitialize(cls.display,C.byref(major),C.byref(minor)):
            raise unittest.SkipTest('Surfaceless EGL is unavailable')
        attributes=(C.c_int*13)(0x3024,8,0x3023,8,0x3022,8,0x3021,8,0x3033,1,0x3040,8,0x3038)
        config,count=C.c_void_p(),C.c_int()
        E.eglChooseConfig(cls.display,attributes,C.byref(config),1,C.byref(count))
        if not count.value:
            E.eglTerminate(cls.display)
            raise unittest.SkipTest('No EGL OpenGL pbuffer config')
        E.eglBindAPI(0x30A2)
        context_attrs=(C.c_int*7)(0x3098,3,0x30FB,3,0x30FD,1,0x3038)
        cls.context=E.eglCreateContext(cls.display,config,None,context_attrs)
        surface_attrs=(C.c_int*5)(0x3057,64,0x3056,64,0x3038)
        cls.surface=E.eglCreatePbufferSurface(cls.display,config,surface_attrs)
        if not cls.context or not cls.surface or not E.eglMakeCurrent(
                cls.display,cls.surface,cls.surface,cls.context):
            if cls.context:E.eglDestroyContext(cls.display,cls.context)
            if cls.surface:E.eglDestroySurface(cls.display,cls.surface)
            E.eglTerminate(cls.display)
            raise unittest.SkipTest('Could not create an OpenGL 3.3 context')
        for name,result,args in (
            ('glCreateShader',C.c_uint,[C.c_uint]),
            ('glShaderSource',None,[C.c_uint,C.c_int,C.POINTER(C.c_char_p),C.POINTER(C.c_int)]),
            ('glCompileShader',None,[C.c_uint]),
            ('glGetShaderiv',None,[C.c_uint,C.c_uint,C.POINTER(C.c_int)]),
            ('glGetShaderInfoLog',None,[C.c_uint,C.c_int,C.POINTER(C.c_int),C.c_void_p]),
            ('glCreateProgram',C.c_uint,[]),
            ('glAttachShader',None,[C.c_uint,C.c_uint]),
            ('glLinkProgram',None,[C.c_uint]),
            ('glGetProgramiv',None,[C.c_uint,C.c_uint,C.POINTER(C.c_int)]),
            ('glGetProgramInfoLog',None,[C.c_uint,C.c_int,C.POINTER(C.c_int),C.c_void_p]),
            ('glDeleteShader',None,[C.c_uint]),
            ('glDeleteProgram',None,[C.c_uint]),
        ):
            fn=getattr(cls.gl,name);fn.restype=result;fn.argtypes=args

    @classmethod
    def tearDownClass(cls):
        cls.egl.eglMakeCurrent(cls.display,None,None,None)
        cls.egl.eglDestroyContext(cls.display,cls.context)
        cls.egl.eglDestroySurface(cls.display,cls.surface)
        cls.egl.eglTerminate(cls.display)

    def compile(self,name,kind):
        root=Path(__file__).parents[1]/'src/solar_system_simulator/rendering'
        source=(root/f'{name}.glsl').read_bytes()
        handle=self.gl.glCreateShader(kind)
        pointer=C.c_char_p(source)
        self.gl.glShaderSource(handle,1,C.byref(pointer),None)
        self.gl.glCompileShader(handle)
        ok=C.c_int()
        self.gl.glGetShaderiv(handle,0x8B81,C.byref(ok))
        log=C.create_string_buffer(8192)
        self.gl.glGetShaderInfoLog(handle,8192,None,log)
        self.assertTrue(ok.value,f'{name}: {log.value.decode()}')
        return handle

    def test_production_shader_programs_compile_and_link(self):
        for vertex,fragment in [('quad','body'),('quad','background'),('trail_vertex','trail_fragment')]:
            with self.subTest(program=fragment):
                handles=[];program=None
                try:
                    handles=[self.compile(vertex,0x8B31),self.compile(fragment,0x8B30)]
                    program=self.gl.glCreateProgram()
                    for handle in handles:self.gl.glAttachShader(program,handle)
                    self.gl.glLinkProgram(program)
                    ok=C.c_int()
                    self.gl.glGetProgramiv(program,0x8B82,C.byref(ok))
                    log=C.create_string_buffer(8192)
                    self.gl.glGetProgramInfoLog(program,8192,None,log)
                    self.assertTrue(ok.value,log.value.decode())
                finally:
                    for handle in handles:self.gl.glDeleteShader(handle)
                    if program:self.gl.glDeleteProgram(program)
