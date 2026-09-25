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
            self.assertEqual(guard.desired_rpm(s,10,3000),expected)
    def test_moderate_load_increases_cooling_before_handoff(self):
        self.assertEqual(guard.desired_rpm(sample(),20,3000),3000)
        self.assertEqual(guard.desired_rpm(sample(),35,3000),3500)
        self.assertEqual(guard.desired_rpm(sample(),50,3000),3900)
    def test_cpu_and_gpu_each_raise_cooling_at_low_load(self):
        s=sample();s['independent']['coretemp/temp2_input']=50
        self.assertEqual(guard.desired_rpm(s,0,3000),4250)
        s=sample();s['independent']['nouveau/temp1_input']=52
        self.assertEqual(guard.desired_rpm(s,0,3000),4250)
    def test_idle_floor_cannot_override_a_hot_sensor(self):
        for key,limit in guard.LIMITS.items():
            s=sample();s['temps'][key]=limit-2
            self.assertEqual(guard.desired_rpm(s,0,3000),5500)
    def test_unsupported_floors_and_load_fail_closed(self):
        for floor in [1800,2999,4301,float('nan')]:
            with self.assertRaises(guard.Unsafe):guard.desired_rpm(sample(),0,floor)
            with self.assertRaises(guard.Unsafe):guard.control(FakeHardware(),floor)
        for cpu in [-1,101,float('nan')]:
            with self.assertRaises(guard.Unsafe):guard.desired_rpm(sample(),cpu,3000)
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
    def test_cpu_steps_on_rising_load(self):
        curve=guard.CpuCooling()
        for cpu,rpm in [(0,3000),(34.9,3000),(35,3500),(49.9,3500),
                        (50,3900),(69.9,3900),(70,4300),(74.9,4300),(75,4800),(79.9,4800)]:
            self.assertEqual(curve.request(cpu,3000),rpm)
    def test_cpu_steps_do_not_chatter_near_boundaries(self):
        curve=guard.CpuCooling()
        self.assertEqual(curve.request(75,3000),4800)
        for cpu in [74,71,70,74,71]:
            self.assertEqual(curve.request(cpu,3000),4800)
        self.assertEqual(curve.request(69,3000),4300)
        self.assertEqual(curve.request(64,3000),3900)
        self.assertEqual(curve.request(44,3000),3500)
        self.assertEqual(curve.request(29,3000),3000)
    def test_previous_50_percent_trigger_keeps_manual_cooling(self):
        p=guard.Policy();p.mode='manual'
        for cpu in [50,60,70,75,79.9]:
            self.assertEqual(p.decide(sample(),cpu,cpu),'manual')
    def test_hot_sensors_demand_full_manual_cooling_below_80(self):
        for cpu in [0,50,70,79]:
            p=guard.Policy();p.mode='manual';s=sample();s['temps']['Tp0C']=58
            self.assertEqual(p.decide(s,cpu,0),'manual')
            self.assertEqual(guard.desired_rpm(s,cpu,3000),5500)
    def test_reentry_requires_continuously_below_65(self):
        p=guard.Policy();s=sample()
        p.decide(s,60,0);p.decide(s,65,20)
        self.assertEqual(p.decide(s,60,30),'auto')
        self.assertEqual(p.decide(s,60,59),'auto')
        self.assertEqual(p.decide(s,60,60),'manual')
    def test_temperature_demand_wins_over_low_cpu_step(self):
        s=sample();s['temps']['Tp0C']=57.5
        self.assertEqual(guard.desired_rpm(s,10,3000,3000),4875)
    def test_thermal_override_remains_full_above_experiment_cutoff(self):
        for label,value in [('Tp0C',65),('TC0D',85),('TN1D',80)]:
            s=sample();s['temps'][label]=value;p=guard.Policy();p.mode='manual'
            self.assertEqual(p.decide(s,70,0),'manual')
            self.assertEqual(guard.desired_rpm(s,70,3000),5500)
    def test_invalid_sensor_still_aborts_manual_thermal_override(self):
        for value in [float('nan'),128,None]:
            s=sample();s['temps']['Tp0C']=value
            with self.assertRaises(guard.Unsafe):guard.desired_rpm(s,10,3000)

    @patch.dict('os.environ',{'INVOCATION_ID':'test','WATCHDOG_USEC':'8000000'})
    @patch('os.geteuid',return_value=0)
    @patch('guard.signal.signal')
    @patch('guard.notify')
    def test_lower_floor_control_reaches_idle_then_responds_to_load(self,*_):
        h=FakeHardware();clock=[0.0]
        def sleep(seconds):
            clock[0]+=seconds;h.value['rpm']=h.value['target']
        def restore():
            h.write('fan1_output',5500);h.write('fan1_manual',0)
        with patch('guard.time.sleep',side_effect=sleep),patch('guard.time.monotonic',side_effect=lambda:clock[0]),patch('guard.restore',side_effect=restore),patch('guard.emit') as events,patch('guard.CpuMeter') as meter:
            meter.return_value.sample.side_effect=[10]*90+[35]*2+[80]+[guard.StopRequested('done')]
            with self.assertRaises(guard.StopRequested):guard.control(h,3000)
        self.assertIn(('fan1_output',3000),h.writes)
        last_idle=max(i for i,w in enumerate(h.writes) if w==('fan1_output',3000))
        self.assertEqual(h.writes[last_idle+1],('fan1_output',3500))
        self.assertIn('handoff',[c.args[0] for c in events.call_args_list])
        self.assertEqual(h.value['manual'],0)
        self.assertEqual(h.value['target'],5500)

    def test_cooldown_then_quiet(self):
        p=guard.Policy();s=sample()
        self.assertEqual(p.decide(s,10,0),'auto')
        self.assertEqual(p.decide(s,10,29),'auto')
        self.assertEqual(p.decide(s,10,30),'manual')
    def test_exact_80_percent_hands_back(self):
        p=guard.Policy();p.mode='manual'
        self.assertEqual(p.decide(sample(),80,0),'auto')
    def test_middle_band_does_not_chatter(self):
        p=guard.Policy();p.mode='manual'
        self.assertEqual(p.decide(sample(),70,0),'manual')
        p.mode='auto'
        self.assertEqual(p.decide(sample(),70,100),'auto')
    def test_cooldown_resets_on_load(self):
        p=guard.Policy();s=sample()
        p.decide(s,10,0);p.decide(s,70,20)
        self.assertEqual(p.decide(s,10,30),'auto')
        self.assertEqual(p.decide(s,10,59),'auto')
        self.assertEqual(p.decide(s,10,60),'manual')
    def test_cpu_temperature_independent_of_utilization(self):
        p=guard.Policy();p.mode='manual';s=sample();s['independent']['coretemp/temp2_input']=55
        self.assertEqual(p.decide(s,1,0),'manual')
        self.assertEqual(guard.desired_rpm(s,1,3000),5500)
    def test_psu_temperature_independent_of_cpu(self):
        p=guard.Policy();p.mode='manual';s=sample();s['temps']['Tp0C']=58
        self.assertEqual(p.decide(s,1,0),'manual')
        self.assertEqual(guard.desired_rpm(s,1,3000),5500)
    def test_gpu_temperature_independent_of_cpu(self):
        p=guard.Policy();p.mode='manual';s=sample();s['independent']['nouveau/temp1_input']=56
        self.assertEqual(p.decide(s,1,0),'manual')
        self.assertEqual(guard.desired_rpm(s,1,3000),5500)
    def test_hot_auto_remains_auto_then_recovers(self):
        p=guard.Policy();s=sample();s['temps']['Tp0C']=65
        self.assertEqual(p.decide(s,1,0),'auto')
        s['temps']['Tp0C']=55
        self.assertEqual(p.decide(s,1,5),'auto')
        self.assertEqual(p.decide(s,1,35),'manual')
    def test_leave_working_automatic_cooling_alone(self):
        p=guard.Policy();s=sample();s['target']=3000;s['rpm']=3000
        self.assertEqual(p.decide(s,1,0),'auto')
        self.assertEqual(p.decide(s,1,300),'auto')
    def test_invalid_stats_abort(self):
        for value in [float('nan'),-1,101]:
            with self.assertRaises(guard.Unsafe):guard.Policy().decide(sample(),value,0)
    def test_cpu_counter_math(self):
        self.assertEqual(guard.CpuMeter.utilization((100,50),(300,150)),50)
        self.assertEqual(guard.CpuMeter.utilization((100,50),(300,250)),0)
        self.assertEqual(guard.CpuMeter.utilization((100,50),(300,50)),100)
        with self.assertRaises(guard.Unsafe):guard.CpuMeter.utilization((100,50),(100,50))
    def test_cpu_rolling_window(self):
        with patch.object(guard.CpuMeter,'counters',side_effect=[(0,0),(100,100),(200,100),(300,100),(400,100),(500,100),(600,100)]):
            meter=guard.CpuMeter()
            values=[meter.sample() for _ in range(6)]
        self.assertEqual(values[0],0)
        self.assertEqual(values[1],50)
        self.assertEqual(values[-1],100)

    @patch.dict('os.environ',{'INVOCATION_ID':'test','WATCHDOG_USEC':'8000000'})
    @patch('os.geteuid',return_value=0)
    @patch('guard.signal.signal')
    @patch('guard.notify')
    def test_full_controller_handoff_and_recovery(self,*_):
        h=FakeHardware();clock=[0.0]
        def sleep(seconds):
            clock[0]+=seconds
            h.value['rpm']=h.value['target']
        def restore():
            h.write('fan1_output',5500);h.write('fan1_manual',0)
        with patch('guard.time.sleep',side_effect=sleep),patch('guard.time.monotonic',side_effect=lambda:clock[0]),patch('guard.restore',side_effect=restore) as rollback,patch('guard.emit') as events,patch('guard.CpuMeter') as meter:
            meter.return_value.sample.side_effect=[10]*31+[85]*2+[10]*32+[OSError('statistics unavailable')]
            with self.assertRaises(OSError):guard.control(h)
            names=[c.args[0] for c in events.call_args_list]
            self.assertEqual(names.count('quiet_mode'),2)
            self.assertEqual(names.count('handoff'),1)
            self.assertIn('handoff_verified',names)
            self.assertEqual(h.value['manual'],0)
            self.assertEqual(h.value['target'],5500)
            self.assertEqual(rollback.call_count,2)

    @patch.dict('os.environ',{'INVOCATION_ID':'test','WATCHDOG_USEC':'8000000'})
    @patch('os.geteuid',return_value=0)
    @patch('guard.signal.signal')
    @patch('guard.notify')
    def test_failed_manual_sensor_read_restores(self,*_):
        h=FakeHardware();clock=[0.0]
        original=h.snapshot
        def snapshot():
            if clock[0]>35:raise OSError('sensor unavailable')
            return original()
        h.snapshot=snapshot
        def sleep(seconds):
            clock[0]+=seconds;h.value['rpm']=h.value['target']
        def restore():
            h.write('fan1_output',5500);h.write('fan1_manual',0)
        with patch('guard.time.sleep',side_effect=sleep),patch('guard.time.monotonic',side_effect=lambda:clock[0]),patch('guard.restore',side_effect=restore) as rollback,patch('guard.emit'),patch('guard.CpuMeter') as meter:
            meter.return_value.sample.return_value=10
            with self.assertRaises(OSError):guard.control(h)
            self.assertIn(('fan1_manual',1),h.writes)
            self.assertEqual(h.value['manual'],0)
            rollback.assert_called_once()


if __name__=='__main__':unittest.main()
