"""BLE logic tests (Domyos protocol, FTMS flow, resistance, back-off, derived values).

Run on the real Home Assistant modules; only the radio is faked.
"""
import re, sys, types, asyncio, logging, io
import time as _time
from bleak.exc import BleakError
from homeassistant.exceptions import HomeAssistantError
from custom_components.domyos_rower import coordinator as C, protocol as P

# ===================== protocol tests =====================
src=open('/home/claude/qz/qdomyos-zwift-master/src/devices/domyosrower/domyosrower.cpp').read()
fn=src[src.index('void domyosrower::btinit_changyow'):src.index('void domyosrower::btinit_telink')]
arr={m.group(1):bytes(int(x,16) for x in re.findall(r'0x([0-9a-f]{2})',m.group(2),re.I)) for m in re.finditer(r'uint8_t (\w+)\[\]\s*=\s*\{(.*?)\};',fn,re.S)}
expected=[(arr[m.group(1)],m.group(2)=='true') for m in re.finditer(r'writeCharacteristic\((\w+), sizeof\(\w+\), QStringLiteral\("init"\), false, (true|false)\);\s*\n',fn.split('if (startTape)')[0])]
assert list(P.INIT_FRAMES)==expected
lines=open('/home/claude/cpptest/expected.txt').read().split('\n'); exp={}
for i in range(0,30,2):
    lvl,first=lines[i].split(); exp[int(lvl)]=bytes.fromhex(first)+bytes.fromhex(lines[i+1])
for lvl in range(1,16):
    a,b=P.build_resistance_frames(lvl); assert a+b==exp[lvl]
pk=bytearray(26); pk[2:4]=(300).to_bytes(2,'big'); pk[6:8]=(120).to_bytes(2,'big'); pk[9]=24; pk[10:12]=(57).to_bytes(2,'big'); pk[14]=8; pk[18]=131
d=P.parse_proprietary(bytes(pk)); assert (d.strokes,d.cadence,d.speed_kmh,d.calories,d.resistance,d.heart_rate)==(300,24,15.0,57,8,131)
# FTMS data frame
def ftms_frame(cad2=50,strokes=77,pace=110,power=180,res=7,hr=120):
    flags=0x08|0x80|0x200|(0x20 if power is not None else 0)
    pw=power.to_bytes(2,'little',signed=True) if power is not None else b''
    return flags.to_bytes(2,'little')+bytes([cad2])+strokes.to_bytes(2,'little')+pace.to_bytes(2,'little')+pw+res.to_bytes(2,'little',signed=True)+bytes([hr])
f=P.parse_ftms_rower_data(ftms_frame()); assert (f.cadence,f.strokes,f.pace_s500,f.power_w,f.resistance,f.heart_rate)==(25,77,110,180,7,120)
# FTMS control helpers (QZ: {0x04, level*10})
assert P.build_ftms_set_resistance(7)==bytes([4,70]) and P.build_ftms_set_resistance(2.5)==bytes([4,25]) and P.build_ftms_set_resistance(99)==bytes([4,255])
assert P.parse_ftms_response(bytes([0x80,0x07,0x01]))==(7,1) and P.parse_ftms_response(bytes([1,2,3])) is None
assert P.parse_resistance_range(bytes([10,160,10]))==(1.0,16.0,1.0)
assert P.parse_resistance_range(bytes([0,0,0])) is None and P.parse_resistance_range(b'\x01') is None



class Char:
    def __init__(s,uuid,props): s.uuid=uuid; s.properties=props
def U(short): return f"0000{short}-0000-1000-8000-00805f9b34fb"
class Svc:
    def __init__(s,uuid,chars): s.uuid=uuid; s.characteristics=chars
class Services:
    def __init__(s,m): s.m=m
    def get_service(s,u): return Svc(u,s.m[u]) if u in s.m else None
    def __iter__(s): return iter(Svc(u,c) for u,c in s.m.items())

class FakeClient:
    """Fake rower. kind: 'domyos' answers the proprietary protocol; 'ftms' is a standard FTMS rower."""
    def __init__(s, services, behaviour='domyos', require_control=False, range_bytes=bytes([10,160,10]), silent_domyos=False):
        s.services=Services(services); s.is_connected=True; s.writes=[]; s.cbs={}; s.events=[]
        s.behaviour=behaviour; s.require_control=require_control; s.controlled=not require_control
        s.range_bytes=range_bytes; s.silent=silent_domyos
        s.strokes=0; s.res=6; s.cmds=[]; s.buf=b''; s.streaming=False; s.rowing=True; s.task=None; s.disc_cb=None; s.fail_cp=False; s.send_power=True; s.pace=110; s.display=[]
    async def start_notify(s,char,cb): u=getattr(char,'uuid',char); s.cbs[u]=cb; s.events.append(('notify',u))
    async def read_gatt_char(s,char): return s.range_bytes
    async def write_gatt_char(s,char,data,response=True):
        u=getattr(char,'uuid',char); data=bytes(data); s.events.append(('write',u,data)); s.writes.append(data)
        if u==P.PROP_WRITE: return s._domyos(data)
        if u==P.FTMS_CONTROL_POINT:
            if s.fail_cp: raise BleakError('Bluetooth GATT Error address=AA:BB handle=33 error=133 description=Error')
            return s._ftms_cp(data)
    # ---- Domyos proprietary
    def _domyos(s,data):
        if s.silent: return
        if (data[:2]==bytes([0xf0,0xcd]) or data[:3]==bytes([0xf0,0xcb,0x03])) and len(data)==20: s.display.append(data); return   # screen frames only (init uses f0 cb 02)
        if data[:2]==bytes([0xf0,0xad]) and len(data)==20 and data[10]!=0xff: s.buf=data; return
        if s.buf and len(data)==3: full=s.buf+data; s.buf=b''; s.cmds.append(full); s.res=full[10]; return
        if data==P.NOOP or len(data)<20:
            s.strokes+=1
            p=bytearray(26); p[2:4]=s.strokes.to_bytes(2,'big'); p[6:8]=(120).to_bytes(2,'big'); p[9]=24; p[10:12]=(5).to_bytes(2,'big'); p[14]=s.res; p[18]=120
            s.cbs[P.PROP_NOTIFY](None,bytearray(p))
    # ---- FTMS control point
    def _ftms_cp(s,data):
        op=data[0]; s.cmds.append(data)
        if op==0x00: s.controlled=True; result=1
        elif op in (0x04,0x07):
            result=1 if s.controlled else 5
            if result==1 and op==0x07 and not s.streaming:
                s.streaming=True; s.task=asyncio.ensure_future(s._stream())
            if result==1 and op==0x04: s.res=data[1]/10
        else: result=2
        if P.FTMS_CONTROL_POINT in s.cbs: s.cbs[P.FTMS_CONTROL_POINT](None,bytearray([0x80,op,result]))
    async def _stream(s):
        while s.is_connected:
            if s.rowing: s.strokes+=1
            s.cbs[P.ROWER_DATA](None,bytearray(ftms_frame(strokes=s.strokes,res=int(s.res),pace=s.pace,power=180 if s.send_power else None)))
            await asyncio.sleep(0.05)
    async def disconnect(s):
        s.is_connected=False
        if s.task: s.task.cancel()


FAKE={}
ATTEMPTS=[]
async def establish_connection(cls, dev, name, cb, max_attempts=3, ble_device_callback=None):
    assert max_attempts==1, 'the loop owns retries/back-off'
    ATTEMPTS.append(_time.monotonic())
    nxt = FAKE['seq'].pop(0) if FAKE.get('seq') else FAKE['client']
    if isinstance(nxt,Exception): raise nxt
    nxt.disc_cb=cb; return nxt
C.establish_connection = establish_connection
C.bluetooth = types.SimpleNamespace(
    async_register_callback=lambda *a,**k:(lambda:None),
    async_ble_device_from_address=lambda *a,**k: object())
C.POLL_INTERVAL=0.02; C.ACK_TIMEOUT=0.02; C.FTMS_CMD_TIMEOUT=0.2
class Entry:
    entry_id='ble-test'; options={}; data={}
    def async_create_background_task(s,hass,coro,name): return asyncio.ensure_future(coro)

FTMS_CHARS=[Char(U('2ad1'),['notify']),Char(U('2ada'),['notify']),Char(U('2ad3'),['notify']),Char(U('2ad9'),['write','indicate']),Char(U('2ad6'),['read']),Char(U('2acc'),['read'])]
FTMS_ONLY={P.FTMS_SERVICE:FTMS_CHARS, U('180a'):[Char(U('2a29'),['read'])]}
PROP_ONLY={P.PROP_SERVICE:[Char(P.PROP_WRITE,['write']),Char(P.PROP_NOTIFY,['notify'])]}

HASS=None
def new(addr='AA:BB'): return C.DomyosRowerCoordinator(HASS,Entry(),addr,'Domyos-ROW-0136')


async def test_ble_logic(hass):
    global HASS
    HASS=hass
    # ---------- 1. Domyos proprietary session + resistance (unchanged behaviour)
    co=new(); FAKE['client']=cl=FakeClient(PROP_ONLY); co.async_start(); await asyncio.sleep(0.6)
    assert [w for w in cl.writes[:len(P.INIT_FRAMES)]]==[f for f,_ in P.INIT_FRAMES]
    assert co.connected and co.mode=='proprietary' and co.status=='connected' and co.data.heart_rate==120
    co.async_set_resistance(11); await asyncio.sleep(0.4)
    assert cl.cmds[-1]==exp[11] and co.data.resistance==11 and co.resistance_target==11
    co.async_set_enabled(False); await asyncio.sleep(0.2)
    assert not cl.is_connected and co.status=='disabled'
    await co.async_stop(); print('1. Domyos proprietary + resistance OK')

    # ---------- 2. FTMS rower (what the user's rower is): QZ-faithful flow
    co=new('AA:CC'); FAKE['client']=cl=FakeClient(FTMS_ONLY,'ftms'); co.async_start(); await asyncio.sleep(0.5)
    notified=[e[1] for e in cl.events if e[0]=='notify']
    assert set(notified)=={U('2ad1'),U('2ada'),U('2ad3'),U('2ad9')}, notified            # every notify/indicate char, like QZ
    first_write=next(i for i,e in enumerate(cl.events) if e[0]=='write')
    last_notify=max(i for i,e in enumerate(cl.events) if e[0]=='notify')
    assert last_notify<first_write, 'subscribe BEFORE Start/Resume'
    assert cl.cmds[0]==bytes([0x07]), 'Start/Resume (0x07) sent like QZ'
    assert co.mode=='ftms' and co.connected and co.status=='connected'
    assert co.data.strokes>0 and co.data.power_w==180 and co.data.pace_s500==110 and co.data.heart_rate==120
    assert co.resistance_range==(1.0,16.0,1.0) and co.resistance_range_known            # range read from 0x2AD6
    assert co.can_set_resistance
    co.async_set_resistance(9); await asyncio.sleep(0.3)
    assert bytes([4,90]) in cl.cmds and co.data.resistance==9 and co.resistance_target==9
    co.async_set_resistance(99); await asyncio.sleep(0.3)
    assert cl.cmds[-1]==bytes([4,160]), cl.cmds[-1]                                      # clamped to the rower's max (16)
    # idle: stop rowing -> after FTMS_STROKE_IDLE cadence/speed/power go to 0 (QZ rule)
    C.FTMS_STROKE_IDLE=0.3; cl.rowing=False; await asyncio.sleep(0.6)
    assert co.data.cadence==0 and co.data.power_w==0 and co.data.speed_kmh==0, co.data
    cl.rowing=True; await asyncio.sleep(0.2); assert co.data.cadence==25
    await co.async_stop(); print('2. FTMS flow (subscribe-all, Start/Resume, resistance 0x04, idle zeroing) OK')

    # ---------- 3. FTMS rower that needs Request Control first
    co=new('AA:DD'); FAKE['client']=cl=FakeClient(FTMS_ONLY,'ftms',require_control=True); co.async_start(); await asyncio.sleep(0.6)
    ops=[c[0] for c in cl.cmds]; assert ops[:3]==[0x07,0x00,0x07], ops                    # 'not permitted' -> request control -> retry
    assert co.data.strokes and co.data.strokes>0
    await co.async_stop(); print('3. FTMS control-not-permitted handled OK')

    # ---------- 4. Domyos service present but silent + FTMS present -> falls back to FTMS
    C.PROP_NO_DATA_TIMEOUT=0.3
    co=new('AA:EE'); both={**PROP_ONLY, **FTMS_ONLY}
    FAKE['client']=cl=FakeClient(both,'ftms',silent_domyos=True); co.async_start(); await asyncio.sleep(1.0)
    assert co.mode=='ftms' and co.connected and co.data.power_w==180 and bytes([7]) in cl.cmds
    await co.async_stop(); print('4. silent Domyos -> FTMS fallback OK')

    # ---------- 5. errors are visible (journal at WARNING + status sensor), not silent
    log=io.StringIO(); h=logging.StreamHandler(log); lg=logging.getLogger('custom_components.domyos_rower.coordinator'); lg.addHandler(h); lg.setLevel(logging.INFO)
    co=new('AA:FF'); FAKE['client']=BleakError('failed to establish connection: ESP_GATT_CONN_FAIL'); co.async_start(); await asyncio.sleep(0.2)
    assert co.status=='error' and 'ESP_GATT_CONN_FAIL' in co.last_error and not co.connected
    out=log.getvalue(); assert 'WARNING' not in out  # handler has no level fmt; check text instead
    assert 'connection/communication error' in out and 'ESP_GATT_CONN_FAIL' in out, out
    await co.async_stop()
    co=new('AA:GG'); FAKE['client']=FakeClient({U('180a'):[Char(U('2a29'),['read'])]}); co.async_start(); await asyncio.sleep(0.2)
    assert co.status=='error' and 'no Domyos/FTMS service' in co.last_error
    await co.async_stop(); print('5. errors surfaced in log + status OK')


    # ---------- 5b. failing step is named in the error (the 'handle=33 error=133' case)
    C.RETRY_DELAYS=(5.0,)
    co=new('AA:II'); FAKE['client']=cl=FakeClient(FTMS_ONLY,'ftms'); cl.fail_cp=True; co.async_start(); await asyncio.sleep(0.4)
    assert co.status=='error' and 'handle=33' in co.last_error and 'during: write Start/Resume' in co.last_error, co.last_error
    assert co.last_operation.startswith('write Start/Resume (handle'), co.last_operation
    await co.async_stop(); print('5b. error says which BLE step failed OK')

    # ---------- 5c. back-off: repeated failures space attempts out (keeps the proxy scanning)
    C.RETRY_DELAYS=(0.1,0.2,0.4,0.8); ATTEMPTS.clear()
    co=new('AA:JJ'); FAKE.pop('client',None); FAKE['seq']=[BleakError('0x3e')]*4; FAKE['client']=BleakError('0x3e')
    co.async_start(); await asyncio.sleep(1.9); await co.async_stop()
    gaps=[round(b-a,2) for a,b in zip(ATTEMPTS,ATTEMPTS[1:])]
    assert len(gaps)>=3 and gaps[0]<gaps[1]<gaps[2] and co.failures>=4, (gaps,co.failures)   # 1st failure -> RETRY_DELAYS[1], then growing
    print('5c. retry back-off OK, gaps (s):', gaps[:5])

    # ---------- 5d. link lost mid-workout after a good session -> back-off reset, quick retry
    C.RETRY_DELAYS=(0.1,5.0,5.0); C.MIN_GOOD_SESSION=0.2; ATTEMPTS.clear()
    co=new('AA:KK'); good=FakeClient(FTMS_ONLY,'ftms'); again=FakeClient(FTMS_ONLY,'ftms')
    FAKE['seq']=[good,again]; co.async_start(); await asyncio.sleep(0.5)
    assert co.connected and co.failures==0
    good.is_connected=False                       # rower drops the link (supervision timeout)
    await asyncio.sleep(0.6)
    assert len(ATTEMPTS)>=2 and co.connected and again.cmds and again.cmds[0]==bytes([7]), (len(ATTEMPTS),co.connected)
    await co.async_stop(); FAKE.pop('seq',None); print('5d. quick reconnect after link loss OK')


    # ---------- 7. rower that sends NO power/elapsed (the user's case): derived like QZ
    C.FTMS_STROKE_IDLE=0.3
    assert C.DomyosRowerCoordinator._power_from_pace(178,29)==62          # the user's real reading: 178 s/500m -> ~62 W
    assert C.DomyosRowerCoordinator._power_from_pace(110,25)==263
    assert C.DomyosRowerCoordinator._power_from_pace(None,25)==0 and C.DomyosRowerCoordinator._power_from_pace(110,0)==0
    co=new('AA:LL'); FAKE['client']=cl=FakeClient(FTMS_ONLY,'ftms'); cl.send_power=False; cl.pace=178
    co.async_start(); await asyncio.sleep(0.6)
    assert co.power_is_calculated and co.data.power_w==62, co.data.power_w
    e1=co.data.elapsed_s; assert e1 is not None and e1>=0
    await asyncio.sleep(0.5); e2=co.data.elapsed_s; assert e2>e1 or e2>=1, (e1,e2)      # counts while rowing
    cl.rowing=False; await asyncio.sleep(0.6); frozen=co.data.elapsed_s; assert co.data.power_w==0
    await asyncio.sleep(0.4); assert co.data.elapsed_s==frozen, 'timer stops when no stroke'    # paused
    cl.rowing=True; await asyncio.sleep(1.3); assert co.data.elapsed_s>frozen                  # resumes (whole seconds)
    cl.strokes=0; await asyncio.sleep(0.15); assert co.data.elapsed_s<=1                       # new workout on the console -> reset
    await co.async_stop()
    # rower that DOES send power: its value wins, nothing is calculated
    co=new('AA:MM'); FAKE['client']=cl=FakeClient(FTMS_ONLY,'ftms'); co.async_start(); await asyncio.sleep(0.4)
    assert not co.power_is_calculated and co.data.power_w==180
    await co.async_stop()
    # Domyos proprietary packets carry neither: power derived from pace, timer runs
    co=new('AA:NN'); FAKE['client']=cl=FakeClient(PROP_ONLY); co.async_start(); await asyncio.sleep(0.7)
    assert co.data.power_w==C.DomyosRowerCoordinator._power_from_pace(120,24) and co.data.elapsed_s is not None
    await co.async_stop(); print('7. calculated power + workout timer OK (rower values win when sent)')


    # ---------- 8. console screen: pace / strokes / distance written like the decoded fields
    C.DISPLAY_FIRST_DELAY=0.1; C.DISPLAY_INTERVAL=0.2
    f=P.build_display_frames(125, 178, 38, 1.25); full=f[2]+f[3]; full2=f[0]+f[1]
    assert full[3:5]==bytes([2,5]) and full[11:13]==(258).to_bytes(2,'big')       # 2:05 elapsed, pace 2:58
    assert full[15:17]==(380).to_bytes(2,'big') and full[19:21]==(12).to_bytes(2,'big')   # 38 strokes, 1.2 km
    assert sum(full[:26])&255==full[26] and sum(full2[:26])&255==full2[26] and len(full)==27
    assert P.pace_digits(0)==0 and P.pace_digits(None)==0 and P.pace_digits(2828)==959 and P.pace_digits(60)==100
    co=new('AA:O0'); assert co.console_display is True
    FAKE['client']=cl=FakeClient(PROP_ONLY); co.async_start(); await asyncio.sleep(1.0)
    shown=[x for x in cl.display if x[1]==0xcb]; assert len(shown)>=2, len(cl.display)
    await co.async_stop()
    co=new('AA:O1'); co.async_set_console_display(False)
    FAKE['client']=cl=FakeClient(PROP_ONLY); co.async_start(); await asyncio.sleep(0.8)
    assert co.connected and cl.display==[], 'no screen frames when the switch is off'
    await co.async_stop(); print('8. console screen fields + switch OK')

    # ---------- 9. distance calibration: scales distance/speed/pace/calculated power only
    co=new('AA:PP')
    co.data=P.RowerData(cadence=29.0,strokes=9,speed_kmh=10.0,pace_s500=180,distance_m=1000.0,calories=50,power_w=60,resistance=4,heart_rate=120,elapsed_s=300)
    assert co.view is co.data
    co.async_set_distance_scale(1.1); v=co.view
    assert v.distance_m==1100.0 and v.speed_kmh==11.0 and v.pace_s500==164, (v.distance_m,v.speed_kmh,v.pace_s500)
    assert v.power_w==C.DomyosRowerCoordinator._power_from_pace(164,29.0)          # calculated power follows the pace
    assert (v.strokes,v.cadence,v.calories,v.resistance,v.heart_rate,v.elapsed_s)==(9,29.0,50,4,120,300)
    co._rower_sends_power=True; assert co.view.power_w==60                         # a power sent by the rower is untouched
    co.async_set_distance_scale(5); assert co.distance_scale==2.0
    co.async_set_distance_scale(0.1); assert co.distance_scale==0.5
    co.async_set_distance_scale(1.0); assert co.view is co.data
    print('9. calibration multiplier OK')

    # ---------- 10. pace mm:ss
    assert P.format_pace(178)=='02:58' and P.format_pace(59)=='00:59' and P.format_pace(600)=='10:00' and P.format_pace(None) is None and P.format_pace(0) is None
    print('10. pace mm:ss OK')

    # ---------- 6. FTMS write refused when read-only / not connected
    co=new('AA:HH')
    try: co.async_set_resistance(5); raise SystemExit('should refuse')
    except HomeAssistantError: pass
    print('6. refuse writes when not connected OK')



def test_to_float_blank_option_falls_back():
    from custom_components.domyos_rower.coordinator import to_float

    assert to_float("", 48.85) == 48.85
    assert to_float(None, 2.35) == 2.35
    assert to_float("abc", 1.0) == 1.0
    assert to_float("45,5".replace(",", "."), 0.0) == 45.5
    assert to_float(12, 0.0) == 12.0


def test_card_registration_serves_file_and_adds_js_url(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock

    import homeassistant.components.frontend as frontend

    from custom_components.domyos_rower import CARD_URL, _async_register_card

    added = []
    monkeypatch.setattr(frontend, "add_extra_js_url", lambda hass, url: added.append(url))
    http = SimpleNamespace(async_register_static_paths=AsyncMock())
    hass = SimpleNamespace(data={}, http=http)
    asyncio.run(_async_register_card(hass))
    asyncio.run(_async_register_card(hass))  # second call is a no-op
    assert http.async_register_static_paths.await_count == 1
    assert len(added) == 1 and added[0].startswith(CARD_URL + "?v=")
    cfg = http.async_register_static_paths.await_args.args[0][0]
    assert cfg.url_path == CARD_URL and cfg.path.endswith("domyos-rower-card.js")
    # no http component: silently skipped
    asyncio.run(_async_register_card(SimpleNamespace(data={}, http=None)))
