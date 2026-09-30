"""Stage an existing trusted CPython stdlib and its dynamic dependencies.

No installation or download. Only the dedicated, hash-manifested snapshot is
mounted into the child; the host's home/project and entire /usr are not mounted.
The resulting manifest is capability evidence, not a universal security proof.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

VERSION = 'stdio-sprint-existing-stdlib-runtime-v1'
MAX_RUNTIME_BYTES = 256 << 20
MAX_DEPENDENCY_BYTES = 128 << 20
MAX_FILES = 10000


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode()


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def _system_file(path):
    path = Path(path).resolve(strict=True)
    if not path.is_file() or not any(path.is_relative_to(Path(p))
                                    for p in ('/usr', '/lib', '/lib64')):
        raise ValueError('trusted existing system runtime files only')
    return path


def _dependencies(binary):
    p = subprocess.run(['/usr/bin/ldd', str(binary)], capture_output=True,
                       timeout=5, env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
    text = (p.stdout + p.stderr).decode('utf-8', 'strict')
    if 'not found' in text:
        raise RuntimeError('unresolved runtime dependency')
    if p.returncode and 'not a dynamic executable' not in text and 'statically linked' not in text:
        raise RuntimeError('trusted ldd failed')
    result = {}
    for line in text.splitlines():
        match = re.search(r'(?:=>\s*)?(/[^\s]+)\s+\(0x[0-9a-fA-F]+\)', line)
        if match:
            guest = match.group(1)
            if '..' in Path(guest).parts or not any(guest.startswith(p + '/')
                                                   for p in ('/lib', '/lib64', '/usr/lib', '/usr/lib64')):
                raise ValueError('dependency guest path outside system library namespace')
            result[guest] = str(_system_file(guest))
    return result


def stage_runtime(destination, python='/usr/bin/python3'):
    """Trusted setup only, fresh destination, bounded copy of installed stdlib.

    The caller freezes this source and the allowed interpreter before setup.
    The emitted exact runtime/dependency hashes are subsequently bound into the
    qualification attestation and every instrument. No benchmark code executes.
    """
    if sys.platform != 'linux':
        raise RuntimeError('Linux runtime staging only')
    started = time.monotonic()
    binary = _system_file(python)
    if not binary.name.startswith('python3'):
        raise ValueError('CPython3 interpreter required')
    probe = ('import json,sys,sysconfig;print(json.dumps({"version":sys.version,'
             '"stdlib":sysconfig.get_path("stdlib"),"minor":"%s.%s"%sys.version_info[:2]}))')
    p = subprocess.run([str(binary), '-I', '-S', '-c', probe], capture_output=True,
                       timeout=5, env={'PATH': '/usr/bin:/bin'})
    if p.returncode:
        raise RuntimeError('existing interpreter metadata probe failed')
    info = json.loads(p.stdout)
    stdlib = Path(info['stdlib']).resolve(strict=True)
    if not stdlib.is_dir() or not stdlib.is_relative_to(Path('/usr')):
        raise ValueError('system standard-library source required')
    target = Path(destination).absolute()
    target.mkdir(mode=0o700, parents=False, exist_ok=False)
    files, total, extension_sources = [], 0, [binary]
    try:
        (target / 'bin').mkdir()
        guest_python = target / 'bin/python3'
        shutil.copyfile(binary, guest_python)
        guest_python.chmod(0o500)
        files.append({'path': 'bin/python3', 'bytes': guest_python.stat().st_size,
                      'sha256': file_hash(guest_python)})
        total += files[-1]['bytes']
        lib_target = target / ('lib/python' + info['minor'])
        lib_target.mkdir(parents=True)
        for root, directories, names in os.walk(stdlib, followlinks=False):
            directories[:] = sorted(d for d in directories
                                    if d not in ('site-packages', 'dist-packages', '__pycache__')
                                    and not (Path(root) / d).is_symlink())
            for name in sorted(names):
                if name.endswith(('.pyc', '.pyo')):
                    continue
                source = Path(root) / name
                if not source.is_file():
                    continue
                resolved = source.resolve(strict=True)
                if not resolved.is_relative_to(stdlib):
                    raise ValueError('stdlib symlink escapes its source tree')
                relative = Path('lib/python' + info['minor']) / source.relative_to(stdlib)
                dest = target / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                size = source.stat().st_size
                if total + size > MAX_RUNTIME_BYTES or len(files) >= MAX_FILES:
                    raise RuntimeError('runtime snapshot cap')
                shutil.copyfile(source, dest)
                dest.chmod(0o400)
                total += size
                files.append({'path': relative.as_posix(), 'bytes': size, 'sha256': file_hash(dest)})
                if name.endswith('.so'):
                    extension_sources.append(resolved)
        # CPython stdlib ctypes loads libseccomp only in the trusted bootstrap.
        # Read its actual loaded system path, then pin it just like dependencies.
        seccomp_probe = ('import ctypes;ctypes.CDLL("libseccomp.so.2");'
                         'print(next(x.split()[-1] for x in open("/proc/self/maps") '
                         'if "/libseccomp.so" in x))')
        p = subprocess.run([str(binary), '-I', '-S', '-c', seccomp_probe],
                           capture_output=True, timeout=5, env={'PATH': '/usr/bin:/bin'})
        if p.returncode:
            raise RuntimeError('existing libseccomp unavailable')
        seccomp = _system_file(p.stdout.decode().strip())
        dependencies = {}
        for source in extension_sources + [seccomp]:
            if time.monotonic() - started > 45:
                raise TimeoutError('runtime setup wall cap')
            dependencies.update(_dependencies(source))
        # SONAME lookup needs an original conventional system-library guest path.
        if seccomp.as_posix().startswith('/usr/lib64/'):
            seccomp_guest = '/lib64/libseccomp.so.2'
        elif seccomp.is_relative_to('/usr/lib'):
            seccomp_guest = str(Path('/lib') / seccomp.relative_to('/usr/lib').parent / 'libseccomp.so.2')
        else:
            seccomp_guest = str(seccomp.parent / 'libseccomp.so.2')
        dependencies[seccomp_guest] = str(seccomp)
        dep_records, dep_total = [], 0
        dep_dir = target / 'dependencies'
        dep_dir.mkdir()
        for index, (guest, source) in enumerate(sorted(dependencies.items())):
            source = _system_file(source)
            size = source.stat().st_size
            dep_total += size
            if dep_total > MAX_DEPENDENCY_BYTES or index >= 256:
                raise RuntimeError('dynamic dependency cap')
            relative = f'dependencies/{index:03d}-{source.name}'
            dest = target / relative
            shutil.copyfile(source, dest)
            dest.chmod(0o400)
            entry = {'path': relative, 'guest_path': guest, 'bytes': size,
                     'sha256': file_hash(dest)}
            dep_records.append(entry)
            files.append({k: v for k, v in entry.items() if k != 'guest_path'})
        manifest = {'version': VERSION, 'python': '/runtime/bin/python3',
                    'python_version': info['version'], 'minor': info['minor'],
                    'files': sorted(files, key=lambda r: r['path']),
                    'dependencies': dep_records, 'runtime_bytes': total,
                    'dependency_bytes': dep_total,
                    'source_python_sha256': file_hash(binary),
                    'classification': 'existing trusted CPython stdlib, no site/dist packages or install'}
        (target / 'manifest.json').write_bytes(canonical(manifest) + b'\n')
        (target / 'manifest.json').chmod(0o400)
        for directory in sorted((p for p in target.rglob('*') if p.is_dir()), reverse=True):
            directory.chmod(0o500)
        target.chmod(0o500)
        return manifest
    except BaseException:
        # Owned fresh snapshot only; preserve diagnostics with caller, not partial runtime.
        for directory in (target, *(p for p in target.rglob('*') if p.is_dir())):
            directory.chmod(0o700)
        shutil.rmtree(target)
        raise


def verify_runtime(directory, expected_manifest_sha256):
    directory = Path(directory).resolve(strict=True)
    raw = (directory / 'manifest.json').read_bytes()
    if sha256(raw) != expected_manifest_sha256:
        raise ValueError('runtime manifest drift')
    manifest = json.loads(raw)
    if manifest.get('version') != VERSION or len(manifest.get('files', [])) > MAX_FILES:
        raise ValueError('runtime schema/cap')
    expected = {'manifest.json'}
    for record in manifest['files']:
        relative = Path(record['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('runtime relative path required')
        path = directory / relative
        if path.is_symlink() or not path.resolve().is_relative_to(directory):
            raise ValueError('runtime links forbidden')
        if path.stat().st_size != record['bytes'] or file_hash(path) != record['sha256']:
            raise ValueError('runtime file drift')
        expected.add(relative.as_posix())
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
    if actual != expected or any(p.is_symlink() for p in directory.rglob('*')):
        raise ValueError('unexpected runtime contents')
    for dependency in manifest['dependencies']:
        guest = dependency['guest_path']
        if not any(guest.startswith(p + '/') for p in ('/lib', '/lib64', '/usr/lib', '/usr/lib64')):
            raise ValueError('invalid dependency mount')
    return manifest
