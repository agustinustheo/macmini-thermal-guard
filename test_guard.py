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
        for floor in [1800,2349,4301,float('nan')]:
            with self.assertRaises(guard.Unsafe):guard.desired_rpm(sample(),floor)
            with self.assertRaises(guard.Unsafe):guard.control(FakeHardware(),floor)
    def test_lower_manual_speed_still_detects_stall(self):
        s=sample();s.update(manual=1,target=3000,rpm=2980)
        guard.check(s)
        s['rpm']=2000
        with self.assertRaises(guard.Unsafe):guard.check(s)
    def test_quieter_manual_floor_keeps_tracking_tolerance(self):
        s=sample();s.update(manual=1,target=2350,rpm=2330)
        guard.check(s)
        s['rpm']=2099
        with self.assertRaises(guard.Unsafe):guard.check(s)
        s.update(target=5500,rpm=2330)
        guard.check(s)  # physical acceleration is checked by the control loop
    def test_quieter_curve_is_bounded_monotonic_and_rejoins_maximum(self):
        for group in ('CPU','GPU','PSU'):
            previous=0
            for step in range(101):
                fraction=step/100
                s=sample()
                if group=='CPU':s['independent']['coretemp/temp2_input']=45+10*fraction
                elif group=='GPU':s['independent']['nouveau/temp1_input']=48+8*fraction
                else:s['temps']['Tp0C']=56+2*fraction
                original=guard.desired_rpm(s,3000)
                quieter=guard.desired_rpm(s,2350)
                with self.subTest(group=group,step=step):
                    self.assertGreaterEqual(quieter,previous)
                    self.assertGreaterEqual(quieter,2350)
                    self.assertLessEqual(quieter,original)
                    self.assertLessEqual(original-quieter,650)
                previous=quieter
            self.assertEqual(previous,5500)
    def test_quieter_curve_examples(self):
        self.assertEqual(guard.desired_rpm(sample(),2350),2350)
        for temperature,expected in [(48,2350),(49,2750),(50,3150),(52,3925),(54,4725),(56,5500)]:
            s=sample();s['independent']['nouveau/temp1_input']=temperature
            self.assertEqual(guard.desired_rpm(s,2350),expected)
    def test_all_components_retain_maximum_with_quieter_floor(self):
        for key,limit in guard.LIMITS.items():
            s=sample();s['temps'][key]=limit-2
            self.assertEqual(guard.desired_rpm(s,2350),5500)
        for key in sample()['independent']:
            s=sample();s['independent'][key]=56
            self.assertEqual(guard.desired_rpm(s,2350),5500)
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
            s['temps'][key]=limit-(2.75 if key=='Tp0C' else 3)
            self.assertEqual(p.decide(s,20),'auto')
            s=sample()
            self.assertEqual(p.decide(s,30),'auto')
            self.assertEqual(p.decide(s,59),'auto')
            self.assertEqual(p.decide(s,60),'manual')

    def test_psu_warm_entry_still_requires_cooldown_and_cooling_demand(self):
        p=guard.Policy();s=sample();s['temps']['Tp0C']=57
        self.assertEqual(p.decide(s,0),'auto')
        self.assertEqual(p.decide(s,29),'auto')
        self.assertEqual(p.decide(s,30),'manual')
        self.assertEqual(guard.desired_rpm(s,2350),3925)
        p=guard.Policy();s['temps']['Tp0C']=57.25
        self.assertEqual(p.decide(s,0),'auto')
        self.assertEqual(p.decide(s,31),'auto')

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
        for sensor,value,floor in [(sensor,value,floor) for sensor,value in [('TM0P',48),('Tp0C',58),('TH0P',40)] for floor in (2350,3000)]:
            h=FakeHardware();clock=[0.0];outputs=[]
            def sleep(seconds):
                clock[0]+=seconds;h.value['rpm']=h.value['target']
                h.value['temps'][sensor]=value if 121<=clock[0]<124 else 30
                if clock[0]>210:raise guard.StopRequested('done')
            original=h.write
            def write(name,value):
                if name=='fan1_output':outputs.append((clock[0],value))
                original(name,value)
            h.write=write
            def restore():
                h.write('fan1_output',5500);h.write('fan1_manual',0)
            with patch('guard.time.sleep',side_effect=sleep),patch('guard.time.monotonic',side_effect=lambda:clock[0]),patch('guard.restore',side_effect=restore) as rollback,patch('guard.emit') as events:
                with self.assertRaises(guard.StopRequested):guard.control(h,floor)
            points=dict(outputs)
            self.assertEqual(points[120],floor)
            self.assertEqual(points[121],5500)
            self.assertEqual(points[124],5450)
            self.assertEqual(points[210],floor)
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

    @patch.dict('os.environ',{'INVOCATION_ID':'test','WATCHDOG_USEC':'8000000'})
    @patch('os.geteuid',return_value=0)
    @patch('guard.signal.signal')
    @patch('guard.notify')
    @patch('guard.emit')
    @patch('guard.restore')
    def test_acceleration_from_quiet_floor_has_time_to_reach_target(self,restore,*_):
        h=FakeHardware();clock=[0]
        def sleep(seconds):
            clock[0]+=seconds
            h.value['rpm'] += max(-500,min(400,h.value['target']-h.value['rpm']))
            if clock[0]>=121:h.value['temps']['TM0P']=48
            if clock[0]>145:raise guard.StopRequested('done')
        with patch('guard.time.sleep',side_effect=sleep),patch('guard.time.monotonic',side_effect=lambda:clock[0]):
            with self.assertRaises(guard.StopRequested):guard.control(h,2350)
        self.assertEqual(h.value['target'],5500)
        self.assertEqual(h.value['rpm'],5500)
        restore.assert_called_once()

    @patch.dict('os.environ',{'INVOCATION_ID':'test','WATCHDOG_USEC':'8000000'})
    @patch('os.geteuid',return_value=0)
    @patch('guard.signal.signal')
    @patch('guard.notify')
    @patch('guard.emit')
    @patch('guard.restore')
    def test_fan_that_never_accelerates_still_fails_tracking(self,restore,*_):
        h=FakeHardware();clock=[0]
        def sleep(seconds):
            clock[0]+=seconds
            h.value['rpm']=h.value['target'] if clock[0]<121 else 2350
            if clock[0]>=121:h.value['temps']['TM0P']=48
            if clock[0]>145:raise AssertionError('fan tracking did not fail')
        with patch('guard.time.sleep',side_effect=sleep),patch('guard.time.monotonic',side_effect=lambda:clock[0]):
            with self.assertRaisesRegex(guard.Unsafe,'Fan not keeping up'):guard.control(h,2350)
        restore.assert_called_once()


class ShutdownTests(unittest.TestCase):
    @staticmethod
    def hot(key, value):
        s=sample()
        if key=='CPU':s['independent']['coretemp/temp2_input']=value
        elif key=='GPU':s['independent']['nouveau/temp1_input']=value
        else:s['temps'][key]=value
        return s

    def test_every_monitored_component_has_a_later_shutdown_limit(self):
        self.assertEqual(set(guard.SHUTDOWN_LIMITS),set(guard.LIMITS)|{'CPU','GPU'})
        for key,value in guard.LIMITS.items():
            self.assertGreater(guard.SHUTDOWN_LIMITS[key],value-2)

    def test_every_shutdown_channel_requires_ten_continuous_seconds(self):
        for key,limit in guard.SHUTDOWN_LIMITS.items():
            p=guard.ThermalShutdown();s=self.hot(key,limit)
            with self.subTest(sensor=key):
                self.assertFalse(p.update(s,0))
                self.assertFalse(p.update(s,9.9))
                self.assertTrue(p.update(s,10))
                self.assertTrue(p.update(sample(),11))  # latched even if it cools

    def test_short_spike_and_alternating_hot_sensors_do_not_accumulate(self):
        p=guard.ThermalShutdown()
        self.assertFalse(p.update(self.hot('CPU',70),0))
        self.assertFalse(p.update(sample(),9))
        self.assertFalse(p.update(self.hot('CPU',70),10))
        self.assertFalse(p.update(self.hot('GPU',75),19))
        self.assertFalse(p.update(self.hot('CPU',70),20))
        self.assertFalse(p.update(self.hot('CPU',70),29))
        self.assertTrue(p.update(self.hot('CPU',70),30))

    def test_emergency_readings_trigger_without_delay(self):
        for key,limit in guard.EMERGENCY_LIMITS.items():
            self.assertTrue(guard.ThermalShutdown().update(self.hot(key,limit),0))

    def test_hot_reading_with_stalled_fan_does_not_wait(self):
        s=self.hot('CPU',70);s['rpm']=0
        self.assertTrue(guard.ThermalShutdown().update(s,0))

    def test_invalid_sensors_are_not_treated_as_a_valid_thermal_event(self):
        for value in [None,float('nan'),0,128]:
            with self.assertRaises(guard.Unsafe):
                guard.ThermalShutdown().update(self.hot('Tp0C',value),0)

    @patch('guard.emit')
    @patch('guard.subprocess.run')
    def test_poweroff_is_controlled_nonblocking_and_never_reboot(self,run,emit):
        self.assertTrue(guard.request_poweroff(['CPU']))
        run.assert_called_once_with(['/usr/bin/systemctl','--no-block','poweroff'],
            check=True,timeout=3,capture_output=True,text=True)

    @patch('guard.emit')
    @patch('guard.subprocess.run',side_effect=OSError('unavailable'))
    def test_failed_poweroff_is_reported_for_retry(self,run,emit):
        self.assertFalse(guard.request_poweroff(['GPU']))
        self.assertIn('poweroff_request_failed',[c.args[0] for c in emit.call_args_list])

    @patch.dict('os.environ',{'INVOCATION_ID':'test','WATCHDOG_USEC':'8000000'})
    @patch('os.geteuid',return_value=0)
    @patch('guard.signal.signal')
    @patch('guard.notify')
    @patch('guard.emit')
    @patch('guard.restore')
    @patch('guard.request_poweroff',side_effect=[False,True])
    def test_critical_loop_retries_shutdown_even_when_fan_write_fails(self,poweroff,restore,*_):
        h=FakeHardware();clock=[0];writes=[];original=h.write
        original_snapshot=h.snapshot
        def snapshot():
            if clock[0]>131:raise OSError('sensor read failed after shutdown latch')
            return original_snapshot()
        h.snapshot=snapshot
        def sleep(seconds):
            clock[0]+=seconds;h.value['rpm']=h.value['target']
            h.value['independent']['coretemp/temp2_input']=70 if 121<=clock[0]<135 else 40
            if clock[0]>155:raise guard.StopRequested('done')
        def write(name,value):
            writes.append((clock[0],name,value))
            if clock[0]>=131:raise OSError('SMC write failed')
            original(name,value)
        h.write=write
        with patch('guard.time.sleep',side_effect=sleep),patch('guard.time.monotonic',side_effect=lambda:clock[0]):
            with self.assertRaises(guard.StopRequested):guard.control(h,2350)
        self.assertEqual(poweroff.call_count,2)
        self.assertTrue(all(value==5500 for t,name,value in writes if t>=131 and name=='fan1_output'))
        restore.assert_called_once()


if __name__=='__main__':unittest.main()
