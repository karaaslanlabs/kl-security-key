#!/usr/bin/env python3
"""Read-only local source pin check; no device/USB access."""
import argparse
from pathlib import Path
import subprocess
import sys

PINS = {
    'sdk': '50699e53e8ada214c27f6c9b66ea3b6f127fc655',
    'pico': '079c6f39023649b154152db30f1d781e884879bc',
    'tinyusb': '86ad6e56c1700e85f1c5678607a762cfe3aa2f47',
    'mbedtls': '068ff080b369adfac81509f9b57b2afabaf82dc5',
    'tinycbor': 'c0aad2fb2137a31b9845fbaae3653540c410f215',
    'picotool': '6f6458d792b93685a11423b244a585eaa99eafcf',
}
COMPILER = 'arm-none-eabi-gcc (xPack GNU Arm Embedded GCC x86_64) 15.2.1 20251203'

def run(argv):
    q = subprocess.run(argv, capture_output=True, text=True)
    if q.returncode:
        raise ValueError(f'Command failed: {argv[:2]}: {q.stderr[:150]}')
    return q.stdout.strip()

def git(path, *args):
    return run(['git', '-C', str(path), *args])

def check(name, path, allowed_untracked=()):
    if not path.is_dir():
        raise ValueError(f'{name}: source checkout missing')
    head = git(path, 'rev-parse', 'HEAD')
    if head != PINS[name]:
        raise ValueError(f'{name}: expected {PINS[name]}, found {head}')
    dirty = git(path, 'status', '--porcelain').splitlines()
    extras = [line for line in dirty if not (line.startswith('?? ') and line[3:] in allowed_untracked)]
    if extras:
        raise ValueError(f'{name}: unapproved file modifications: {extras[:3]}')
    print(f'PIN_PASS {name} {head}')

def verify(args):
    check('sdk', args.sdk, ('third-party/',))
    check('pico', args.pico)
    check('tinyusb', args.pico / 'lib/tinyusb')
    check('mbedtls', args.third_party / 'mbedtls', ('.picokeys_dep_source',))
    check('tinycbor', args.third_party / 'tinycbor', ('.picokeys_dep_source',))
    picotool_tag = git(args.picotool, 'rev-parse', '2.3.0^{commit}')
    if picotool_tag != PINS['picotool']:
        raise ValueError(f'picotool 2.3.0 points to unexpected commit {picotool_tag}')
    print(f'PIN_PASS picotool {picotool_tag}')
    compiler = args.toolchain_bin / 'arm-none-eabi-gcc'
    if not compiler.is_file():
        raise ValueError('ARM compiler not found')
    version = run([str(compiler), '--version']).splitlines()[0]
    if version != COMPILER:
        raise ValueError(f'ARM compiler version drift: {version}')
    print('PIN_PASS ARM compiler')
    print('LOCAL_OFFDEVICE_SOURCE_PROVENANCE_PASS')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('sdk', 'pico', 'third_party', 'picotool', 'toolchain_bin'):
        parser.add_argument('--' + field.replace('_','-'), type=Path, required=True)
    try:
        verify(parser.parse_args())
        return 0
    except (OSError, ValueError) as err:
        print(f'LOCAL_OFFDEVICE_SOURCE_PROVENANCE_FAIL: {err}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
