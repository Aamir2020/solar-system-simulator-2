import json
from pathlib import Path
import unittest
import numpy as np
from solar_system_simulator.physics.system import G, State, accelerations, energy, step
from solar_system_simulator.physics.runner import StepBudget


class PhysicsTests(unittest.TestCase):
    def two_body(self):
        m = np.array([1.989e30,5.972e24])
        distance = 149597870700.
        omega = np.sqrt(G*m.sum()/distance**3)
        fraction = m[1]/m.sum()
        x = np.array([-fraction*distance,(1-fraction)*distance])
        return State(np.column_stack((x,[0.,0.])),
                     np.column_stack(([0.,0.],omega*x)),m), 2*np.pi/omega

    def test_original_solver_regression(self):
        data=json.loads((Path(__file__).parent/'fixtures/original_solver.json').read_text())
        state=State(**data['initial'])
        for _ in range(data['steps']):step(state,data['dt'])
        np.testing.assert_allclose(state.positions,data['positions'],rtol=2e-14,atol=.002)
        np.testing.assert_allclose(state.velocities,data['velocities'],rtol=2e-14,atol=1e-8)

    def test_circular_orbit_energy_and_momentum(self):
        state,period=self.two_body()
        initial=state.copy(); initial_energy=energy(state)
        momentum0=np.sum(state.masses[:,None]*state.velocities,axis=0)
        errors=[]
        for _ in range(2000):
            step(state,period/2000)
            errors.append(abs((energy(state)-initial_energy)/initial_energy))
        self.assertLess(max(errors),3e-10)
        np.testing.assert_allclose(state.positions,initial.positions,rtol=0,atol=3.2e6)
        momentum=np.sum(state.masses[:,None]*state.velocities,axis=0)
        scale=np.linalg.norm(initial.velocities[1])*initial.masses[1]
        self.assertLess(np.linalg.norm(momentum-momentum0)/scale,1e-13)

    def test_second_order_convergence(self):
        state,period=self.two_body()
        start=state.positions.copy()
        errors=[]
        for n in (100,200,400):
            trial=state.copy()
            for _ in range(n):step(trial,period/n)
            errors.append(np.linalg.norm(trial.positions-start))
        self.assertGreater(errors[0]/errors[1],3.8)
        self.assertGreater(errors[1]/errors[2],3.8)

    def test_force_symmetry(self):
        state,_=self.two_body()
        force=accelerations(state.positions,state.masses)*state.masses[:,None]
        np.testing.assert_allclose(force[0],-force[1],rtol=1e-15)

    def test_invalid_states_and_collisions(self):
        with self.assertRaises(ValueError):State([[0,0]],[[0,0]],[-1])
        with self.assertRaises(ValueError):State([[float('nan'),0]],[[0,0]],[1])
        s=State([[0,0],[0,0]],[[0,0],[0,0]],[1,1])
        with self.assertRaisesRegex(ValueError,'collisions'):step(s,1)
        for dt in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):step(s,dt)

    def test_render_rate_does_not_change_trajectory(self):
        trajectories=[]
        for fps in (30,60,144):
            state,_=self.two_body()
            budget=StepBudget()
            for _ in range(20*fps):
                for _ in range(budget.consume(1/fps,10*86400,86400)):
                    step(state,86400)
            self.assertEqual(state.elapsed,200*86400)
            trajectories.append(state.positions)
        for positions in trajectories[1:]:
            np.testing.assert_array_equal(positions,trajectories[0])

    def test_work_is_bounded_after_stall(self):
        budget=StepBudget()
        self.assertLessEqual(budget.consume(1000,1e12,3600),256)
        self.assertLessEqual(budget.debt,256*3600)


if __name__=='__main__':unittest.main()
