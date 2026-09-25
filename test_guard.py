import copy
import unittest
from unittest.mock import patch
import guard


def sample():
    return dict(temps={k: min(30, v-8) for k,v in guard.LIMITS.items()},
                independent={'coretemp/temp2_input':40, 'coretemp/temp3_input':41,
                             'nouveau/temp1_input':45},
                rpm=5500,target=5500,manual=0,minimum=1800,maximum=5500)


class FakeHardware:
    def __init__(self):
        self.value=sample()
        self.writes=[]
    def snapshot(self): return copy.deepcopy(self.value)
    def faults(self): return {'SBF':0, 'MSSF':0,'SPHR':0,'SPHS':0}
    def read(self, name): return self.value[{'fan1_manual':'manual','fan1_output':'target'}[name]]
    def write(self, name, value):
        self.writes.append((name,value))
        if name=='fan1_manual':self.value['manual']=value
        if name=='fan1_output':self.value['target']=value


class Guards(unittest.TestCase):
    def test_baseline(self):guard.check(sample())
    def test_every_required_sensor_fails_closed(self):
        for key in guard.LIMITS:
            for bad in [None, -128, 0, 128, float('nan'), guard.LIMITS[key]]:
                s=sample();s['temps'][key]=bad
                with self.subTest(key=key,bad=bad), self.assertRaises(guard.Unsafe):guard.check(s)
    def test_all_missing_channels(self):
        for key in guard.LIMITS:
            s=sample();del s['temps'][key]
            with self.assertRaises(guard.Unsafe):guard.check(s)
    def test_rise(self):
        b=sample();s=copy.deepcopy(b);s['temps']['Tp0C']+=4
        with self.assertRaises(guard.Unsafe):guard.check(s,b)
    def test_small_cpu_fluctuation_allowed_but_large_rise_rejected(self):
        b=sample();s=copy.deepcopy(b);s['temps']['TC0D']+=5
        guard.check(s,b)
        s['temps']['TC0D']=b['temps']['TC0D']+12
        with self.assertRaises(guard.Unsafe):guard.check(s,b)
    def test_independent_sensor(self):
        for key in sample()['independent']:
            s=sample();s['independent'][key]=60
            with self.assertRaises(guard.Unsafe):guard.check(s)
    def test_fan_stall(self):
        s=sample();s['rpm']=0
        with self.assertRaises(guard.Unsafe):guard.check(s)
    def test_missing_independent(self):
        s=sample();s['independent'].pop('nouveau/temp1_input')
        with self.assertRaises(guard.Unsafe):guard.check(s)
    @patch.dict('os.environ',{'MACMINI_SUPERVISED_PROBE':'1','INVOCATION_ID':'test'})
    @patch('os.geteuid',return_value=0)
    @patch('guard.signal.signal')
    @patch('guard.emit')
    @patch('guard.restore')
    def test_failed_write_restores(self,restore,*_):
        h=FakeHardware();h.write=lambda *a: (_ for _ in ()).throw(OSError('failed'))
        with self.assertRaises(OSError):guard.probe(h,10,5000)
        restore.assert_called_once()
    @patch.dict('os.environ',{'MACMINI_SUPERVISED_PROBE':'1','INVOCATION_ID':'test'})
    @patch('os.geteuid',return_value=0)
    @patch('guard.emit')
    def test_fault_refuses_before_writes(self,*_):
        h=FakeHardware();h.faults=lambda:{'SBF':1}
        with self.assertRaises(guard.Unsafe):guard.probe(h,10,5000)
        self.assertEqual(h.writes,[])
    def test_unsupervised_refused(self):
        with patch.dict('os.environ',{},clear=True),self.assertRaises(guard.Unsafe):
            guard.probe(FakeHardware(),10,5000)
    def test_control_range_and_ramp(self):
        for temperature,expected in [(50,4300),(55,4300),(56,4300),(57,4900),(58,5500),(59.75,5500)]:
            s=sample();s['temps']['Tp0C']=temperature
            self.assertEqual(guard.desired_rpm(s),expected)
    def test_any_sensor_can_raise_fan(self):
        for key,limit in guard.LIMITS.items():
            s=sample();s['temps'][key]=limit-1
            self.assertEqual(guard.desired_rpm(s),5500)
    def test_lower_idle_floor_and_psu_ramp(self):
        for temp,expected in [(55,3000),(56,3000),(56.5,3625),(57,4250),(57.5,4875),(58,5500)]:
            s=sample();s['temps']['Tp0C']=temp
            self.assertEqual(guard.desired_rpm(s,3000),expected)
    def test_cpu_and_gpu_each_raise_cooling_at_low_load(self):
        s=sample();s['independent']['coretemp/temp2_input']=50
        self.assertEqual(guard.desired_rpm(s,3000),4250)
        s=sample();s['independent']['nouveau/temp1_input']=52
        self.assertEqual(guard.desired_rpm(s,3000),4250)
    def test_idle_floor_cannot_override_a_hot_sensor(self):
        for key,limit in guard.LIMITS.items():
            s=sample();s['temps'][key]=limit-2
            self.assertEqual(guard.desired_rpm(s,3000),5500)
    def test_unsupported_floors_fail_closed(self):
        for floor in [1800,2999,4301,float('nan')]:
            with self.assertRaises(guard.Unsafe):guard.desired_rpm(sample(),floor)
            with self.assertRaises(guard.Unsafe):guard.control(FakeHardware(),floor)
    def test_lower_manual_speed_still_detects_stall(self):
        s=sample();s.update(manual=1,target=3000,rpm=2980)
        guard.check(s)
        s['rpm']=2500
        with self.assertRaises(guard.Unsafe):guard.check(s)
    def test_controller_needs_watchdog(self):
        with patch.dict('os.environ',{'INVOCATION_ID':'test'},clear=True),patch('os.geteuid',return_value=0):
            with self.assertRaises(guard.Unsafe):guard.control(FakeHardware())
    @patch.dict('os.environ',{'INVOCATION_ID':'test','WATCHDOG_USEC':'8000000'})
    @patch('os.geteuid',return_value=0)
    @patch('guard.signal.signal')
    @patch('guard.emit')
    @patch('guard.restore')
    @patch('guard.notify',side_effect=OSError('notify failed'))
    def test_control_notify_failure_restores(self,notify,restore,*_):
        with self.assertRaises(OSError):guard.control(FakeHardware())
        restore.assert_called_once()


class PolicyTests(unittest.TestCase):
    def test_cooldown_then_quiet(self):
        p=guard.Policy();s=sample()
        self.assertEqual(p.decide(s,0),'auto')
        self.assertEqual(p.decide(s,29),'auto')
        self.assertEqual(p.decide(s,30),'manual')

    def test_cooldown_restarts_for_every_warm_smc_sensor(self):
        for key,limit in guard.LIMITS.items():
            p=guard.Policy();s=sample();p.decide(s,0)
            s['temps'][key]=limit-3
            self.assertEqual(p.decide(s,20),'auto')
            s=sample()
            self.assertEqual(p.decide(s,30),'auto')
            self.assertEqual(p.decide(s,59),'auto')
            self.assertEqual(p.decide(s,60),'manual')

    def test_each_independent_sensor_prevents_warm_takeover(self):
        for key in sample()['independent']:
            p=guard.Policy();s=sample();s['independent'][key]=55
            self.assertEqual(p.decide(s,0),'auto')
            self.assertEqual(p.decide(s,31),'auto')

    def test_each_component_demands_full_cooling_on_its_own(self):
        for key,limit in guard.LIMITS.items():
            for value in [limit-2,limit,limit+10]:
                s=sample();s['temps'][key]=value
                p=guard.Policy();p.mode='manual'
                with self.subTest(sensor=key,value=value):
                    self.assertEqual(p.decide(s,0),'manual')
                    rpm,drivers=guard.thermal_demand(s,3000)
                    self.assertEqual(rpm,5500)
                    self.assertIn(key,drivers)

    def test_each_core_and_gpu_can_override_all_cool_components(self):
        for key in sample()['independent']:
            s=sample();s['independent'][key]=56
            p=guard.Policy();p.mode='manual'
            self.assertEqual(p.decide(s,0),'manual')
            self.assertEqual(guard.desired_rpm(s,3000),5500)

    def test_component_relative_demand_wins_not_highest_temperature(self):
        s=sample();s['temps']['TM0P']=48;s['temps']['Tp0C']=55
        self.assertEqual(guard.thermal_demand(s,3000),(5500,['TM0P']))
        s['temps']['Tp0C']=57
        self.assertEqual(guard.thermal_demand(s,3000),(5500,['TM0P']))
        s['temps']['TM0P']=35
        self.assertEqual(guard.thermal_demand(s,3000),(4250,['Tp0C']))

    def test_combined_demands_take_maximum_and_report_ties(self):
        s=sample();s['temps']['TM0P']=47;s['temps']['Tp0C']=57
        s['independent']['coretemp/temp3_input']=50
        self.assertEqual(guard.thermal_demand(s,3000),(4250,['CPU','TM0P','Tp0C']))
        s['independent']['nouveau/temp1_input']=54
        self.assertEqual(guard.thermal_demand(s,3000),(4875,['GPU']))

    def test_idle_floor_and_rounding(self):
        self.assertEqual(guard.thermal_demand(sample(),3000),(3000,['idle floor']))
        s=sample();s['temps']['Tp0C']=56.01
        self.assertEqual(guard.desired_rpm(s,3000),3025)

    def test_unknown_constant_channels_do_not_drive_cooling(self):
        s=sample();s['temps'].update(TM0G=75,TN1G=90,TCPG=73)
        self.assertEqual(guard.desired_rpm(s,3000),3000)

    def test_invalid_smc_sensor_aborts_runtime_control(self):
        for key in guard.LIMITS:
            for value in [None,float('nan'),float('inf'),0,128]:
                s=sample();s['temps'][key]=value
                with self.subTest(key=key,value=value),self.assertRaises(guard.Unsafe):
                    guard.desired_rpm(s,3000)

    def test_invalid_independent_sensor_aborts_runtime_control(self):
        for key in sample()['independent']:
            for value in [float('nan'),float('inf'),0,128]:
                s=sample();s['independent'][key]=value
                with self.assertRaises(guard.Unsafe):guard.desired_rpm(s,3000)

    def test_hot_auto_remains_auto_then_recovers(self):
        p=guard.Policy();s=sample();s['temps']['Tp0C']=65
        self.assertEqual(p.decide(s,0),'auto')
        s['temps']['Tp0C']=55
        self.assertEqual(p.decide(s,5),'auto')
        self.assertEqual(p.decide(s,35),'manual')

    def test_leave_working_automatic_cooling_alone(self):
        p=guard.Policy();s=sample();s['target']=3000;s['rpm']=3000
        self.assertEqual(p.decide(s,0),'auto')
        self.assertEqual(p.decide(s,300),'auto')

    @patch.dict('os.environ',{'INVOCATION_ID':'test','WATCHDOG_USEC':'8000000'})
    @patch('os.geteuid',return_value=0)
    @patch('guard.signal.signal')
    @patch('guard.notify')
    def test_controller_peripheral_heat_recovery_and_shutdown_restore(self,*_):
        for sensor,value in [('TM0P',48),('Tp0C',58),('TH0P',40)]:
            h=FakeHardware();clock=[0.0];outputs=[]
            def sleep(seconds):
                clock[0]+=seconds;h.value['rpm']=h.value['target']
                h.value['temps'][sensor]=value if 91<=clock[0]<94 else 30
                if clock[0]>150:raise guard.StopRequested('done')
            original=h.write
            def write(name,value):
                if name=='fan1_output':outputs.append((clock[0],value))
                original(name,value)
            h.write=write
            def restore():
                h.write('fan1_output',5500);h.write('fan1_manual',0)
            with patch('guard.time.sleep',side_effect=sleep),patch('guard.time.monotonic',side_effect=lambda:clock[0]),patch('guard.restore',side_effect=restore) as rollback,patch('guard.emit') as events:
                with self.assertRaises(guard.StopRequested):guard.control(h,3000)
            points=dict(outputs)
            self.assertEqual(points[90],3000)
            self.assertEqual(points[91],5500)
            self.assertEqual(points[94],5450)
            self.assertEqual(points[150],3000)
            self.assertEqual([c.args[0] for c in events.call_args_list].count('quiet_mode'),1)
            self.assertEqual(h.value['manual'],0)
            self.assertEqual(h.value['target'],5500)
            rollback.assert_called_once()

    @patch.dict('os.environ',{'INVOCATION_ID':'test','WATCHDOG_USEC':'8000000'})
    @patch('os.geteuid',return_value=0)
    @patch('guard.signal.signal')
    @patch('guard.notify')
    def test_failed_manual_sensor_read_restores(self,*_):
        h=FakeHardware();clock=[0.0];original=h.snapshot
        def snapshot():
            if clock[0]>35:raise OSError('sensor unavailable')
            return original()
        h.snapshot=snapshot
        def sleep(seconds):
            clock[0]+=seconds;h.value['rpm']=h.value['target']
        def restore():
            h.write('fan1_output',5500);h.write('fan1_manual',0)
        with patch('guard.time.sleep',side_effect=sleep),patch('guard.time.monotonic',side_effect=lambda:clock[0]),patch('guard.restore',side_effect=restore) as rollback,patch('guard.emit'):
            with self.assertRaises(OSError):guard.control(h)
            self.assertIn(('fan1_manual',1),h.writes)
            self.assertEqual(h.value['manual'],0)
            rollback.assert_called_once()


if __name__=='__main__':unittest.main()
