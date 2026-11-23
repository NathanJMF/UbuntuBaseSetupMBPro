"""Apply and roll back the Mac-specific system files from a desktop session."""
from base64 import b64decode, b64encode
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ABI = '7.3.5-1-t2-resolute'
PACKAGE = 'linux-image-' + ABI
SHA = '888617ed1b635c797f233b1dc578a80e8cb76f8f4406b341d03274ed3c0905e8'
URL = ('https://github.com/AdityaGarg8/t2-ubuntu-repo/releases/download/resolute/'
       + PACKAGE + '_7.3.5-1_amd64.deb')
STATE = Path('/var/lib/ubuntu-mbpro')
UNIT = 'macbook-bcm4377-recovery.service'
WIRELESS = {
    **{p: '/etc/systemd/system/systemd-suspend.service.d/' + p.name
       for p in (HERE/'wireless').glob('*.conf')},
    HERE/'wireless'/UNIT: '/etc/systemd/system/' + UNIT,
    HERE/'wireless/wifi-recovery': '/usr/local/libexec/macbook-bcm4377-recovery',
    HERE/'wireless/macbook-bcm4377-bluetooth': '/usr/local/libexec/macbook-bcm4377-bluetooth',
}


def run(*args, **options):
    return subprocess.run(args, check=True, text=True, **options)


def installed():
    proc = subprocess.run(['dpkg-query','-W','-f=${db:Status-Status}', PACKAGE],
                          text=True, capture_output=True)
    return proc.stdout == 'installed'


class Hardware:
    def __init__(self, group):
        self.path = STATE / (group + '.json')
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {'files': {}}

    def save(self):
        STATE.mkdir(mode=0o700, exist_ok=True)
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.data))
        tmp.replace(self.path)

    def copy(self, source, destination, mode):
        dest = Path(destination)
        if dest.is_symlink():
            raise RuntimeError(f'Refusing to replace symbolic link {dest}')
        files = self.data['files']
        if destination not in files:
            files[destination] = {'old': b64encode(dest.read_bytes()).decode() if dest.exists() else None,
                                  'mode': dest.stat().st_mode & 0o777 if dest.exists() else mode}
        entry = files[destination]
        if 'hash' in entry and dest.exists() and sha256(dest.read_bytes()).hexdigest() != entry['hash']:
            if entry['old'] is None or dest.read_bytes() != b64decode(entry['old']):
                raise RuntimeError(f'Preserving locally edited file {dest}')
        entry['hash'] = sha256(source.read_bytes()).hexdigest()
        self.save()
        run('install','-D','-m', format(mode,'o'),source,dest)

    def restore(self):
        for name, entry in self.data['files'].items():
            if Path(name).is_symlink() or (Path(name).exists() and sha256(Path(name).read_bytes()).hexdigest() != entry['hash']):
                raise RuntimeError(f'Preserving locally edited file {name}')
        for name, entry in list(self.data['files'].items()):
            path = Path(name)
            if entry['old'] is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(b64decode(entry['old']))
                path.chmod(entry['mode'])
            del self.data['files'][name]
            self.save()


def wireless(rollback):
    state = Hardware('wireless')
    if rollback:
        if not state.path.exists():
            return
        run('systemctl','disable','--now', UNIT)
        state.restore()
        run('systemctl','daemon-reload')
        if state.data.get('enabled'):
            run('systemctl','enable',UNIT)
        if state.data.get('active'):
            run('systemctl','start',UNIT)
        state.path.unlink()
        return
    if 'enabled' not in state.data:
        for key, cmd in [('enabled','is-enabled'),('active','is-active')]:
            state.data[key] = subprocess.run(['systemctl',cmd,'--quiet',UNIT]).returncode == 0
        state.save()
    run('apt-get','install','-y','iw','bluez','network-manager')
    for src, dest in WIRELESS.items():
        state.copy(src,dest,0o755 if '/libexec/' in dest else 0o644)
    run('systemctl','daemon-reload')
    run('systemctl','enable','--now',UNIT)


def kernel(rollback):
    state = Hardware('kernel')
    if rollback:
        if not state.path.exists():
            return
        if not state.data['preinstalled'] and installed():
            if os.uname().release == ABI:
                raise RuntimeError('Boot a generic kernel from Advanced options before removing this T2 kernel.')
            run('dpkg','--remove',PACKAGE)
        state.restore()
        run('update-grub')
        state.path.unlink()
        return
    boot = Path('/boot')
    if not any((boot / p.name.replace('vmlinuz-', 'initrd.img-')).is_file() for p in boot.glob('vmlinuz-*-generic')):
        raise RuntimeError('Install and verify an Ubuntu generic kernel and initramfs as a fallback first.')
    if 'preinstalled' not in state.data:
        state.data['preinstalled'] = installed()
        state.save()
    dracut = Path('/etc/kernel/postinst.d/dracut').is_file()
    if dracut:
        state.copy(HERE/'kernel/early-drivers.conf','/etc/dracut.conf.d/75-ubuntu-mbpro.conf',0o644)
    elif Path('/usr/share/initramfs-tools/hook-functions').is_file():
        state.copy(HERE/'kernel/initramfs-hook','/etc/initramfs-tools/hooks/ubuntu-mbpro',0o755)
    else:
        raise RuntimeError('Install the Ubuntu initramfs tooling before proceeding.')
    if not installed():
        with tempfile.TemporaryDirectory() as temp:
            deb = Path(temp) / (PACKAGE + '.deb')
            run('curl','--proto','=https','--proto-redir','=https','-fLsS','--retry','3',URL,'-o',deb)
            with deb.open('rb') as stream:
                import hashlib
                if hashlib.file_digest(stream,'sha256').hexdigest() != SHA:
                    raise RuntimeError('T2 kernel checksum mismatch')
            run('dpkg','--install',deb)
    initrd = boot / ('initrd.img-' + ABI)
    if dracut:
        run('dracut','--force',initrd,ABI)
        listing = run('lsinitrd',initrd,capture_output=True).stdout
    else:
        run('update-initramfs','-u','-k',ABI)
        listing = run('lsinitramfs',initrd,capture_output=True).stdout
    if not all(module+'.ko' in listing for module in ('t2bce_dma','t2bce_core','t2bce_vhci')):
        raise RuntimeError('T2 drivers missing from initramfs. Check the image before rebooting.')
    state.copy(HERE/'kernel/prefer-t2.cfg','/etc/default/grub.d/85-ubuntu-mbpro.cfg',0o644)
    run('update-grub')


if __name__ == '__main__':
    import argparse
    import fcntl
    parser = argparse.ArgumentParser()
    parser.add_argument('group',choices=['wireless','kernel'])
    parser.add_argument('--rollback',action='store_true')
    args = parser.parse_args()
    if os.geteuid() or Path('/sys/class/dmi/id/product_name').read_text().strip() != 'MacBookPro15,4':
        parser.exit(1,'The hardware installer requires root on MacBookPro15,4.\n')
    with open('/run/ubuntu-mbpro-hardware.lock','a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        {'wireless':wireless,'kernel':kernel}[args.group](args.rollback)
