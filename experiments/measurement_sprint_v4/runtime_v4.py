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
import stat
import struct
import subprocess
import sys
import time

VERSION = 'stdio-sprint-existing-stdlib-runtime-v4'
MAX_RUNTIME_BYTES = 256 << 20
MAX_DEPENDENCY_BYTES = 128 << 20
MAX_FILES = 10000
MAX_ELF_METADATA_BYTES = 1 << 20


def elf_interpreter(binary):
    """Read the trusted ELF PT_INTERP path without executing the binary.

    Linux requires execute permission on this interpreter, in addition to the
    CPython executable. Ordinary shared objects need read permission only.
    Metadata reads are bounded; the path must remain in the library namespace.
    """
    with Path(binary).open('rb') as stream:
        header = stream.read(64)
        if len(header) < 52 or header[:4] != b'\x7fELF' or header[4] not in (1, 2) or header[5] not in (1, 2):
            raise ValueError('trusted ELF interpreter header required')
        endian = '<' if header[5] == 1 else '>'
        if header[4] == 2:
            if len(header) < 64:
                raise ValueError('truncated ELF64 header')
            phoff = struct.unpack_from(endian+'Q', header, 32)[0]
            entsize, count = struct.unpack_from(endian+'HH', header, 54)
            minimum = 56
        else:
            phoff = struct.unpack_from(endian+'I', header, 28)[0]
            entsize, count = struct.unpack_from(endian+'HH', header, 42)
            minimum = 32
        if not 0 < count <= 128 or not minimum <= entsize <= 256 or phoff+entsize*count > MAX_ELF_METADATA_BYTES:
            raise ValueError('ELF program header metadata cap')
        paths = []
        for index in range(count):
            stream.seek(phoff+index*entsize)
            entry = stream.read(entsize)
            if len(entry) != entsize:
                raise ValueError('truncated ELF program header')
            if struct.unpack_from(endian+'I', entry, 0)[0] != 3:
                continue
            offset = struct.unpack_from(endian+('Q' if header[4] == 2 else 'I'), entry, 8 if header[4] == 2 else 4)[0]
            length = struct.unpack_from(endian+('Q' if header[4] == 2 else 'I'), entry, 32 if header[4] == 2 else 16)[0]
            if not 2 <= length <= 512 or offset+length > MAX_ELF_METADATA_BYTES:
                raise ValueError('ELF interpreter metadata cap')
            stream.seek(offset)
            raw = stream.read(length)
            if len(raw) != length or raw[-1:] != b'\x00' or b'\x00' in raw[:-1]:
                raise ValueError('ELF interpreter framing')
            path = raw[:-1].decode('ascii', 'strict')
            if '..' in Path(path).parts or not any(path.startswith(p+'/') for p in ('/lib', '/lib64', '/usr/lib', '/usr/lib64')):
                raise ValueError('ELF interpreter library path required')
            paths.append(path)
    if len(paths) != 1:
        raise ValueError('one dynamically linked CPython ELF interpreter required')
    return paths[0]


def filesystem_execution(path):
    """Record this allocation's mount flag; never change host mount options."""
    flags = os.statvfs(path).f_flag
    noexec_flag = getattr(os, 'ST_NOEXEC', 8)
    return {'f_flag': flags, 'st_noexec_mask': noexec_flag,
            'noexec': bool(flags & noexec_flag)}


def staged_mode(relative, interpreter_guest_path=None, guest_path=None):
    return 0o500 if relative == 'bin/python3' or guest_path == interpreter_guest_path and guest_path is not None else 0o400


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
    interpreter_guest = elf_interpreter(binary)
    probe = ('import json,sys,sysconfig;print(json.dumps({"version":sys.version,'
             '"stdlib":sysconfig.get_path("stdlib"),"platlibdir":sys.platlibdir,'
             '"minor":"%s.%s"%sys.version_info[:2]}))')
    p = subprocess.run([str(binary), '-I', '-S', '-c', probe], capture_output=True,
                       timeout=5, env={'PATH': '/usr/bin:/bin'})
    if p.returncode:
        raise RuntimeError('existing interpreter metadata probe failed')
    info = json.loads(p.stdout)
    stdlib = Path(info['stdlib']).resolve(strict=True)
    if not stdlib.is_dir() or not stdlib.is_relative_to(Path('/usr')):
        raise ValueError('system standard-library source required')
    if info['platlibdir'] not in ('lib', 'lib64'):
        raise ValueError('pinned CPython platform-library directory required')
    stdlib_relative = Path(info['platlibdir'])/('python'+info['minor'])
    stdlib_guest = str(stdlib)
    target = Path(destination).absolute()
    filesystem = filesystem_execution(target.parent)
    if filesystem['noexec']:
        raise RuntimeError('runtime destination filesystem is noexec; no mount relaxation')
    target.mkdir(mode=0o700, parents=False, exist_ok=False)
    files, total, extension_sources = [], 0, [binary]
    try:
        (target / 'bin').mkdir()
        guest_python = target / 'bin/python3'
        shutil.copyfile(binary, guest_python)
        guest_python.chmod(0o500)
        files.append({'path': 'bin/python3', 'bytes': guest_python.stat().st_size,
                      'sha256': file_hash(guest_python), 'mode': 0o500})
        total += files[-1]['bytes']
        lib_target = target / stdlib_relative
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
                relative = stdlib_relative / source.relative_to(stdlib)
                dest = target / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                size = source.stat().st_size
                if total + size > MAX_RUNTIME_BYTES or len(files) >= MAX_FILES:
                    raise RuntimeError('runtime snapshot cap')
                shutil.copyfile(source, dest)
                dest.chmod(0o400)
                total += size
                files.append({'path': relative.as_posix(), 'bytes': size, 'sha256': file_hash(dest), 'mode': 0o400})
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
        dependencies[interpreter_guest] = str(_system_file(interpreter_guest))
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
            mode = staged_mode(relative, interpreter_guest, guest)
            dest.chmod(mode)
            entry = {'path': relative, 'guest_path': guest, 'bytes': size,
                     'sha256': file_hash(dest), 'mode': mode}
            dep_records.append(entry)
            files.append({k: v for k, v in entry.items() if k != 'guest_path'})
        manifest = {'version': VERSION, 'python': '/runtime/bin/python3',
                    'python_version': info['version'], 'minor': info['minor'],
                    'platlibdir': info['platlibdir'],
                    'stdlib_mounts': [{'path': stdlib_relative.as_posix(), 'guest_path': stdlib_guest}],
                    'files': sorted(files, key=lambda r: r['path']),
                    'dependencies': dep_records, 'runtime_bytes': total,
                    'dependency_bytes': dep_total,
                    'elf_interpreter_guest_path': interpreter_guest,
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
        mode = record.get('mode')
        guest = next((d['guest_path'] for d in manifest['dependencies'] if d['path'] == record['path']), None)
        if mode != staged_mode(record['path'], manifest.get('elf_interpreter_guest_path'), guest) or stat.S_IMODE(path.stat().st_mode) != mode:
            raise ValueError('runtime file executable/read-only mode drift')
        expected.add(relative.as_posix())
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
    if actual != expected or any(p.is_symlink() for p in directory.rglob('*')):
        raise ValueError('unexpected runtime contents')
    for dependency in manifest['dependencies']:
        guest = dependency['guest_path']
        if not any(guest.startswith(p + '/') for p in ('/lib', '/lib64', '/usr/lib', '/usr/lib64')):
            raise ValueError('invalid dependency mount')
    interpreter = manifest.get('elf_interpreter_guest_path')
    if not interpreter or sum(d['guest_path'] == interpreter for d in manifest['dependencies']) != 1:
        raise ValueError('one pinned ELF interpreter mount required')
    if elf_interpreter(directory/'bin/python3') != interpreter:
        raise ValueError('ELF interpreter differs from its pinned mount')
    mounts = manifest.get('stdlib_mounts')
    if type(mounts) is not list or len(mounts) != 1 or manifest.get('platlibdir') not in ('lib', 'lib64'):
        raise ValueError('one source-bound stdlib subtree mount required')
    mount = mounts[0]
    relative = f"{manifest['platlibdir']}/python{manifest['minor']}"
    guest = mount.get('guest_path')
    if set(mount) != {'path', 'guest_path'} or mount['path'] != relative or type(guest) is not str or guest != '/usr/'+relative or '..' in Path(guest).parts:
        raise ValueError('stdlib exact platform subtree mapping required')
    if not (directory/relative/'encodings/__init__.py').is_file() or not (directory/relative/'lib-dynload').is_dir():
        raise ValueError('isolated CPython stdlib/extension landmarks missing')
    if filesystem_execution(directory)['noexec']:
        raise ValueError('runtime filesystem lost execute capability')
    return manifest
