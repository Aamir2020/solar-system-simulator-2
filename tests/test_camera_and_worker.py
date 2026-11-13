from time import monotonic, sleep
import unittest
import numpy as np
from solar_system_simulator.data.catalog import AU, BODIES
from solar_system_simulator.data.scenario import demo_scenario
from solar_system_simulator.physics.runner import SimulationRunner
from solar_system_simulator.rendering.camera import Camera,display_radii,pick_body


class CameraTests(unittest.TestCase):
    def test_roundtrip_and_cursor_anchored_zoom(self):
        camera=Camera();point=np.array([123.,432.])
        before=camera.to_world(point,1200,800)
        camera.zoom(point,.3,1200,800)
        camera.animate(1/60)
        np.testing.assert_allclose(camera.to_world(point,1200,800),before,rtol=1e-15)
        np.testing.assert_allclose(camera.to_screen(before,1200,800),point,atol=1e-12)

    def test_free_zoom_keeps_cursor_anchor_for_every_animation_frame(self):
        camera = Camera()
        point = np.array([173., 627.])
        anchor = camera.to_world(point, 1200, 800)
        initial_span = camera.span
        camera.zoom(point, .3, 1200, 800)
        self.assertEqual(camera.span, initial_span)  # No wheel-event jump.
        previous = camera.span
        for _ in range(120):
            camera.animate(1/60)
            self.assertLessEqual(camera.span, previous)
            np.testing.assert_allclose(camera.to_screen(anchor, 1200, 800), point, atol=1e-10)
            previous = camera.span
        self.assertAlmostEqual(camera.span / initial_span, .3)
        camera.zoom(point, 2, 1200, 800)
        for _ in range(120):
            camera.animate(1/60)
            np.testing.assert_allclose(camera.to_screen(anchor, 1200, 800), point, atol=1e-10)

    def test_follow_zoom_does_not_pull_toward_an_off_center_cursor(self):
        camera = Camera()
        target = np.array([3*AU, -AU])
        camera.animate(1/60, target)
        for factor in (.8, .8, 1.2, 1.2):
            camera.zoom([100, 650], factor, 1200, 800, following=True)
            for _ in range(10):
                target = target + [1e8, -2e8]
                camera.animate(1/60, target)
                np.testing.assert_array_equal(camera.to_screen(target, 1200, 800), [600, 400])

    def test_zoom_reversal_and_animation_rate_independence(self):
        camera = Camera()
        camera.zoom([200, 300], .1, 1200, 800)
        camera.animate(1/60)
        span = camera.span
        camera.zoom([200, 300], 1.2, 1200, 800)
        camera.animate(1/60)
        self.assertGreater(camera.span, span)
        results = []
        for fps in (30, 60, 144):
            camera = Camera()
            camera.zoom([200, 300], .2, 1200, 800)
            for _ in range(fps//2):
                camera.animate(1/fps)
            results.append(camera.span)
        np.testing.assert_allclose(results, results[0], rtol=1e-13)

    def test_pick_uses_y_and_nearest_body(self):
        points=np.array([[100,100],[100,200],[105,200]])
        self.assertEqual(pick_body(points,np.array([5,5,5]),[101,202]),1)
        self.assertIsNone(pick_body(points,np.array([5,5,5]),[100,150]))

    def test_display_size_does_not_mutate_physics(self):
        state=demo_scenario().state
        initial=state.positions.copy()
        camera=Camera();camera.pan(100,100,800);camera.zoom([400,300],.1,800,600)
        exaggerated=display_radii(BODIES,camera.span,600)
        physical=display_radii(BODIES,camera.span,600,True)
        self.assertTrue(np.all(exaggerated>=physical))
        np.testing.assert_array_equal(state.positions,initial)


class WorkerTests(unittest.TestCase):
    def wait_for(self,runner,predicate):
        until=monotonic()+2
        while monotonic()<until:
            snapshot=runner.latest()
            if snapshot is not None and predicate(snapshot):return snapshot
            sleep(.005)
        self.fail('Simulation worker did not publish the expected state')

    def test_step_reset_generation_and_readonly_snapshots(self):
        state=demo_scenario().state
        runner=SimulationRunner(state)
        try:
            initial=runner.latest()
            with self.assertRaises(ValueError):initial.positions[0,0]=1
            runner.single_step()
            advanced=self.wait_for(runner,lambda s:s.elapsed==86400)
            self.assertEqual(advanced.generation,0)
            generation=runner.reset(state)
            reset=self.wait_for(runner,lambda s:s.generation==generation)
            self.assertEqual(reset.elapsed,0)
            self.assertEqual(len(reset.trails),1)
            np.testing.assert_array_equal(reset.positions,state.positions)
        finally:runner.close()
        self.assertFalse(runner.thread.is_alive())

    def test_bounded_history_and_pause(self):
        runner=SimulationRunner(demo_scenario().state,trail_limit=3)
        try:
            runner.latest()
            runner.configure(paused=False,rate=10000*86400)
            snap=self.wait_for(runner,lambda s:s.elapsed>=10*86400)
            runner.configure(paused=True)
            self.assertLessEqual(len(snap.trails),3)
            self.assertLessEqual(runner.output.qsize(),2)
            self.assertTrue(runner.errors.empty())
        finally:runner.close()


if __name__=='__main__':unittest.main()
