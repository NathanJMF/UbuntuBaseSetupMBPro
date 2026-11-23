"""Exercise fresh, repeated and replayed installs using local Git repos and mock hardware."""
import contextlib
import os
from pathlib import Path
import json
import runpy
import subprocess
import sys
import tempfile
from unittest.mock import patch

source = Path(__file__).resolve().parents[1]
main = runpy.run_path(str(source/'setup'))['main']
ns = main.__globals__
base_script = """#!/bin/sh
set -eu
printf '%s\\n' "$@" > "$XDG_STATE_HOME/flags"
dir="$XDG_STATE_HOME/ubuntu-desktop-setup"
mkdir -p "$dir"
for component in resources keeper nightfall; do
    printf '%040d\\n' 1 > "$dir/$component-revision"
done
"""
def git(repo, *args):
    return subprocess.check_output(['git','-C',repo,*args],text=True).strip()


def commit(repo, message):
    git(repo,'add','.')
    git(repo,'-c','user.name=Fixture','-c','user.email=fixture@localhost','commit','-qm',message)
    return git(repo,'rev-parse','HEAD')


with tempfile.TemporaryDirectory() as temp, contextlib.ExitStack() as stack:
    scratch = Path(temp)
    state = scratch/'state'
    state.mkdir()
    for name,entry,body in [('macbook','README.md','Fixture'),('UbuntuThermals','install','#!/bin/sh\nexit 0\n'),
                            ('UbuntuBaseSetup','setup',base_script)]:
        repo=scratch/name
        repo.mkdir()
        git(repo,'init','-q','-b','main')
        file=repo/entry
        file.write_text(body)
        file.chmod(0o755)
        commit(repo,'initial')
    old_read=Path.read_text
    model=Path('/sys/class/dmi/id/product_name')
    stack.enter_context(patch.object(Path,'read_text',lambda self,*a,**k:'MacBookPro15,4' if self==model else old_read(self,*a,**k)))
    stack.enter_context(patch.dict(os.environ,{'XDG_STATE_HOME':str(state),'DBUS_SESSION_BUS_ADDRESS':'fixture',
        'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_COUNT':'1',
        'GIT_CONFIG_KEY_0':'url.'+scratch.as_uri()+'/.insteadOf',
        'GIT_CONFIG_VALUE_0':'https://github.com/NathanJMF/'}))
    # The real checkout helper fetches only these local fixture repositories.
    for name in ('UbuntuThermals','UbuntuBaseSetup'):
        (scratch/(name+'.git')).symlink_to(scratch/name,target_is_directory=True)
    seen=[]
    real=ns['run']
    def safe_run(*cmd,**options):
        if cmd[0]=='sudo':
            assert cmd[1:3]==('/usr/bin/python3','-I') and cmd[-1] in ('kernel','wireless')
            seen.append(cmd[-1])
            return
        assert cmd[0]=='git' or (isinstance(cmd[0],Path) and cmd[0].name in ('setup','install') and cmd[0].parent.parent == Path(tempfile.gettempdir()))
        return real(*cmd,**options)
    stack.enter_context(patch.dict(ns,ROOT=scratch/'macbook',STATE=state/'ubuntu-mbpro',SCROLL_UNIT=scratch/'scroll.conf',
                                  run=safe_run,scroll=lambda pct:seen.append(pct)))
    stack.enter_context(patch.object(ns['platform'],'freedesktop_os_release',return_value={'ID':'ubuntu','VERSION_ID':'26.04','VERSION_CODENAME':'resolute'}))
    stack.enter_context(patch.object(os,'getuid',return_value=1000))
    def invoke(*args):
        with patch.object(sys,'argv',['setup',*args]):
            main()
        return json.loads((state/'ubuntu-mbpro/manifest.json').read_text())
    initial=invoke()
    assert (state/'flags').read_text().strip()=='' and 'nightfall' not in initial['commits']
    assert seen==['kernel','wireless']
    configured=invoke('--nightfall','--lock-after-15-minutes','--scroll','15')
    assert (state/'flags').read_text().splitlines()==['--nightfall','--lock-after-15-minutes']
    assert seen[-1]==15
    saved=scratch/'record.json'
    saved.write_text(json.dumps(configured))
    (scratch/'UbuntuBaseSetup/change').write_text('New upstream revision')
    newer=commit(scratch/'UbuntuBaseSetup','second revision')
    assert invoke()['commits']['base']==newer
    rebuilt=invoke('--replay',str(saved))
    assert rebuilt==configured and rebuilt['commits']['base']!=newer
    print('PASS: default and explicit options, latest base, pinned replay, separate thermal install and hardware steps')
