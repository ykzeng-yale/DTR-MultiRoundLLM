#!/bin/bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
test ! -e source
test ! -e build
test ! -e build-complete.txt
python3 - <<'PY'
import hashlib,json,pathlib
p=json.loads(pathlib.Path('build-plan.json').read_bytes())
for name,expected in p['files'].items():
    if hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()!=expected:raise SystemExit('frozen file mismatch: '+name)
if hashlib.sha256(pathlib.Path('llama-source.tar.gz').read_bytes()).hexdigest()!=p['source_archive_sha256']:raise SystemExit('source mismatch')
if not pathlib.Path('freeze.txt').read_text().strip():raise SystemExit('missing freeze')
PY
module purge
module load GCC/13.3.0 CMake/3.31.8-GCCcore-13.3.0 CUDA/12.8.0
module -t list > modules.txt 2>&1
mkdir source
tar -xzf llama-source.tar.gz --strip-components=1 -C source
cmake -S source -B build -DGGML_CUDA=ON '-DCMAKE_CUDA_ARCHITECTURES=86;89;90' -DGGML_NATIVE=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_APP=OFF -DLLAMA_BUILD_UI=OFF -DLLAMA_USE_PREBUILT_UI=OFF -DLLAMA_OPENSSL=OFF -DLLAMA_BUILD_NUMBER=1 -DLLAMA_BUILD_COMMIT=4fea119
cmake --build build --target llama-server -j 4
find build/bin -type f -exec sha256sum '{}' \; | LC_ALL=C sort > build-sha256.txt
du -sb source build > build-sizes.txt
python3 - <<'PY'
import json,pathlib,hashlib,os
sizes=[int(x.split()[0]) for x in pathlib.Path('build-sizes.txt').read_text().splitlines()]
if sum(sizes)>5*1024**3:raise SystemExit('build artifact cap exceeded')
p={'job_id':os.environ['SLURM_JOB_ID'],'freeze':pathlib.Path('freeze.txt').read_text().strip(),'plan_sha256':hashlib.sha256(pathlib.Path('build-plan.json').read_bytes()).hexdigest(),'build_manifest_sha256':hashlib.sha256(pathlib.Path('build-sha256.txt').read_bytes()).hexdigest(),'source_and_build_bytes':sum(sizes),'architectures':[86,89,90],'source_commit':'4fea119','paid_usd':0,'classification':'receiver prerequisite; no model collection or candidate execution'}
pathlib.Path('build-summary.json').write_text(json.dumps(p,indent=2)+'\n')
PY
printf 'BUILD_COMPLETED\n' > build-complete.txt
