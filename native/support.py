"""Native benchmark process, host, and artifact support (stdlib only)."""
import hashlib
from pathlib import Path
import platform
import subprocess
import tarfile
import time


def command(args, **kwargs):
    result = subprocess.run([str(x) for x in args], capture_output=True, timeout=600, **kwargs)
    if result.returncode:
        raise RuntimeError(f'command failed ({result.returncode}): {args}\n'
                           + result.stdout.decode(errors='replace')
                           + result.stderr.decode(errors='replace'))
    return result.stdout


def host_info(out):
    system = (platform.system(), platform.machine())
    if system not in [('Darwin', 'arm64'), ('Linux', 'x86_64')]:
        raise RuntimeError(f'unsupported native acceptance host: {system}')
    # Verify the scalar libc clock ABI and conversion rather than assuming its rate.
    probe = out / 'clock_probe.c'
    probe.write_text('#include <stdio.h>\n#include <time.h>\n'
                     'int main(void) { printf("%zu %lld\\n", sizeof(clock_t), '
                     '(long long)CLOCKS_PER_SEC); return 0; }\n')
    binary = out / 'clock_probe'
    command(['cc', '-O2', probe, '-o', binary])
    width, frequency = map(int, command([binary]).split())
    if width != 8 or frequency <= 0:
        raise RuntimeError(f'unsupported clock_t ABI: {width} bytes / {frequency} Hz')
    return {'system': system[0], 'machine': system[1], 'platform': platform.platform(),
            'cpu': command(['sysctl', '-n', 'machdep.cpu.brand_string']).decode().strip()
            if system[0] == 'Darwin' else Path('/proc/cpuinfo').read_text().splitlines()[:25],
            'clock_ticks_per_second': frequency,
            'cc': command(['cc', '--version']).decode().splitlines()[0]}


def artifacts(executable, report, output, *, object_name):
    # Extract only the compiler's object bytes; never unpack arbitrary archive paths.
    with tarfile.open(report) as archive:
        objects = [m for m in archive.getmembers() if m.isfile() and Path(m.name).name == object_name]
        if len(objects) != 1:
            raise RuntimeError(f'expected one native object in {report}, found {len(objects)}')
        object_path = output / object_name
        object_path.write_bytes(archive.extractfile(objects[0]).read())
    started = time.perf_counter()
    command(['cc', object_path, '-o', output / 'relinked'])
    link_seconds = time.perf_counter() - started
    size_args = ['size', '-m', object_path] if platform.system() == 'Darwin' else ['size', '-A', object_path]
    size_text = command(size_args).decode()
    output.joinpath('size.txt').write_text(size_text)
    if platform.system() == 'Darwin':
        text_bytes = sum(int(line.split()[-1]) for line in size_text.splitlines()
                         if line.strip().startswith('Section ') and '__text' in line)
        assembly = command(['otool', '-tvV', object_path])
    else:
        text_bytes = sum(int(line.split()[1]) for line in size_text.splitlines()
                         if line.strip().startswith('.text'))
        assembly = command(['objdump', '-dr', object_path])
    if text_bytes <= 0:
        raise RuntimeError(f'failed to find native text size in {size_text}')
    output.joinpath('assembly.txt').write_bytes(assembly)
    return {'object_bytes': object_path.stat().st_size, 'text_bytes': text_bytes,
            'executable_bytes': executable.stat().st_size, 'relink_seconds': link_seconds,
            'executable_sha256': hashlib.sha256(executable.read_bytes()).hexdigest()}
