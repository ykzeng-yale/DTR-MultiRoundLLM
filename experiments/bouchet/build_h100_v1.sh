#!/bin/bash
set -euo pipefail
module purge
module load GCC/13.3.0 CMake/3.31.8-GCCcore-13.3.0 CUDA/12.8.0
printf '%s  %s\n' 3b83853db981c2aa0dcff7e4711cfb1640b694465407fe668675154f0fe67bdb llama-source.tar.gz | sha256sum -c -
test ! -e source
test ! -e build
mkdir source
tar -xzf llama-source.tar.gz --strip-components=1 -C source
module -t list > modules.txt 2>&1
cmake -S source -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=90 -DGGML_NATIVE=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_APP=OFF -DLLAMA_BUILD_UI=OFF -DLLAMA_USE_PREBUILT_UI=OFF -DLLAMA_OPENSSL=OFF -DLLAMA_BUILD_NUMBER=1 -DLLAMA_BUILD_COMMIT=4fea119
cmake --build build --target llama-server -j 4
find build/bin -type f -exec sha256sum '{}' \; > build-sha256.txt
du -sb source build > build-sizes.txt
printf 'BUILD_COMPLETED\n' > build-complete.txt
