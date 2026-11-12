import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import unittest
import numpy as np
import requests
from solar_system_simulator.data.catalog import BODIES
from solar_system_simulator.data.horizons import (
    Cancelled,HorizonsClient,HorizonsError,normalize_epoch,parameters,parse_vectors,
)
from solar_system_simulator.data.scenario import demo_scenario


def payload(jd=2461041.5):
    return {'signature':{'version':'1.3','source':'NASA/JPL Horizons API'},
            'result':f'Header\n$$SOE\n{jd}, A.D. 2026-Jan-01 00:00:00.0000, 1.0E+08, -2.0E+07, 9.0E+03, 3.0E+01, -4.0E+00, 5.0E-01,\n$$EOE\nFooter'}


class Response:
    def __init__(self,data):self.data=data
    def raise_for_status(self):pass
    def json(self):return self.data


class Session:
    def __init__(self):self.calls=[];self.fail=False
    def get(self,url,params,timeout):
        self.calls.append(dict(params))
        if self.fail:raise requests.Timeout('test timeout')
        return Response(payload(float(params['TLIST'])))
    def close(self):pass


class DataTests(unittest.TestCase):
    def test_vector_units_and_projection(self):
        position,velocity=parse_vectors(payload(),2461041.5)
        np.testing.assert_array_equal(position,[1e11,-2e10])
        np.testing.assert_array_equal(velocity,[30000,-4000])

    def test_errors_and_malformed_data(self):
        cases=[None,{}, {'error':'no such body'}, {'signature':{'version':'1.3'},'result':'No data'}]
        for case in cases:
            with self.subTest(case=case),self.assertRaises(HorizonsError):parse_vectors(case)
        bad=payload();bad['result']=bad['result'].replace('1.0E+08','NaN')
        with self.assertRaises(HorizonsError):parse_vectors(bad)
        with self.assertRaisesRegex(HorizonsError,'different epoch'):parse_vectors(payload(),1)

    def test_explicit_frame_epoch_and_timescale(self):
        params=parameters(399,'2000-01-01T12:00:00')
        self.assertEqual(float(params['TLIST']),2451545)
        for key,value in {'CENTER':'500@0','OUT_UNITS':'KM-S','REF_PLANE':'ECLIPTIC',
                          'REF_SYSTEM':'ICRF','VEC_CORR':'NONE','TIME_TYPE':'TDB'}.items():
            self.assertEqual(params[key],value)
        for value in ('nonsense','2026-01-01T00:00:00Z','1800-01-01'):
            with self.assertRaises(HorizonsError):normalize_epoch(value)

    def test_cache_isolation_by_epoch_and_body(self):
        with TemporaryDirectory() as directory:
            session=Session()
            client=HorizonsClient(directory,session)
            client.load('2026-01-01')
            self.assertEqual(len(session.calls),9)
            self.assertEqual(len({r['TLIST'] for r in session.calls}),1)
            self.assertEqual({r['COMMAND'] for r in session.calls},{str(b.horizons_id) for b in BODIES})
            client.load('2026-01-01')
            self.assertEqual(len(session.calls),9)
            client.load('2026-01-02')
            self.assertEqual(len(session.calls),18)
            self.assertEqual(len(list(Path(directory).glob('*.json'))),18)

    def test_corrupt_cache_recovered(self):
        with TemporaryDirectory() as directory:
            session=Session();client=HorizonsClient(directory,session)
            client.load('2026-01-01')
            for path in Path(directory).glob('*.json'):path.write_text('{broken')
            client.load('2026-01-01')
            self.assertEqual(len(session.calls),18)

    def test_cancel_and_timeout(self):
        with TemporaryDirectory() as directory:
            session=Session();client=HorizonsClient(directory,session,retries=0)
            cancel=Event();cancel.set()
            with self.assertRaises(Cancelled):client.load('2026-01-01',cancel=cancel)
            self.assertEqual(session.calls,[])
            session.fail=True
            with self.assertRaisesRegex(HorizonsError,'Unable to load'):client.load('2026-01-01')

    def test_demo_is_explicit_and_barycentric(self):
        demo=demo_scenario()
        self.assertIn('NOT NASA',demo.source)
        state=demo.state
        total=state.masses.sum()
        np.testing.assert_allclose(np.sum(state.positions*state.masses[:,None],axis=0)/total,0,atol=1e-6)
        self.assertEqual(demo.date_at(86400),'2026-01-02 00:00 TDB')


if __name__=='__main__':unittest.main()
