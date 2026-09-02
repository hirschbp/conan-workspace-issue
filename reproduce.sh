#!/usr/bin/env bash
# Reproduces the CMakeConfigDeps / Conan Workspace transitive dependency drop.
#
# Expected (correct) output for `wrapper-Targets-release.cmake` would include:
#     # Requirement wrapper::wrapper -> leaf::leaf (Full link: True)
#     set_property(TARGET wrapper::wrapper APPEND PROPERTY INTERFACE_LINK_LIBRARIES
#                  "$<$<CONFIG:RELEASE>:leaf::leaf>")
#
# Actual (buggy) output: no such block is generated at all, i.e. "wrapper"
# silently loses its "leaf" link requirement.
set -euo pipefail
cd "$(dirname "$0")"

echo "== Creating leaf, wrapper, lic packages =="
conan create leaf -s build_type=Release
conan create wrapper -s build_type=Release
conan create lic -s build_type=Release

echo
echo "== Running 'conan workspace super-install' (core + app are editable workspace members) =="
rm -f ./*Targets*.cmake ./*-config*.cmake ./*Targets.cmake ./CMakePresets.json ./conan_toolchain.cmake \
      ./sbom.cdx.json ./conanbuild.sh ./conanrun.sh ./conan_cmakedeps_paths.cmake \
      ./conanbuildenv-*.sh ./conanrunenv-*.sh ./deactivate_*.sh
conan workspace super-install -s build_type=Release

echo
echo "== Generated wrapper-Targets-release.cmake =="
cat wrapper-Targets-release.cmake
echo
if grep -q "leaf::leaf" wrapper-Targets-release.cmake; then
    echo "OK: wrapper::wrapper correctly links leaf::leaf (bug NOT reproduced)"
else
    echo "BUG REPRODUCED: wrapper::wrapper is missing its 'leaf::leaf' INTERFACE_LINK_LIBRARIES entry!"
fi
