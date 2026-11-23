"""Check the firmware-specific trigger without scanning or resetting any radio."""
from pathlib import Path
import runpy

evidence=runpy.run_path(str(Path(__file__).resolve().parents[1]/'wireless/wifi-recovery'))['Evidence']
scan='ieee80211 phy0: brcmf_cfg80211_scan: scan error (-5)'
fault='ieee80211 phy0: brcmf_msgbuf_query_dcmd: Timeout on response for query command'
for messages in [
    ['association failed: incorrect password',scan,scan],
    [fault,scan],
    [fault,scan,scan.replace('phy0','phy1')],
]:
    events=evidence()
    assert not any(events.feed(msg,t) for t,msg in enumerate(messages))
events=evidence()
assert events.feed(fault,0) is None and events.feed(scan,1) is None
assert events.feed(scan,4)=='phy0'
events=evidence()
assert events.feed(fault,0) is None and events.feed(scan,91) is None and events.feed(scan,93) is None
print('PASS: password rejection, isolated scan failures, stale evidence and other radios never trigger recovery')
