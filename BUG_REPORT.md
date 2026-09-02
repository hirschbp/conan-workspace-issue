# CMakeConfigDeps drops transitive `INTERFACE_LINK_LIBRARIES` for a dependency inside a `conan workspace` when that dependency is reachable via two different paths from an editable package

## Summary

Inside a `conan workspace` (the experimental multi-package workspace feature),
when using the `CMakeConfigDeps` generator, a regular (non-editable, cached)
package can silently lose the `INTERFACE_LINK_LIBRARIES` entry for one of its
own dependencies in the generated `<pkg>-Targets-<config>.cmake` file.

Concretely: package `wrapper` `requires()` package `leaf`. Conan correctly
resolves this dependency (`leaf` is installed and part of the graph), but the
generated `wrapper-Targets-release.cmake` never emits the
`set_property(TARGET wrapper::wrapper APPEND PROPERTY INTERFACE_LINK_LIBRARIES ... leaf::leaf ...)`
block for it. Any consumer that only links against `wrapper::wrapper` (CMake's
`find_package(wrapper)` + `target_link_libraries(... wrapper::wrapper)`) will
fail to link with undefined symbol errors coming from `leaf`, because CMake
never learns that `wrapper` needs `leaf`.

This is **not** a simple "forgot to add `cpp_info.requires`" recipe bug -
`wrapper`'s recipe is correct and relies on Conan's normal *implicit
requires* mechanism (i.e. `cpp_info.requires` is automatically derived from
`self.requires()` when not set explicitly). The bug is in the workspace + `CMakeConfigDeps`
plumbing, not in the dependency's recipe.

We discovered this in a large (~100 package) real-world `conan workspace`
project where `cpr` (which transitively depends on `openssl`) was losing its
link to `openssl`, causing undefined-reference linker errors for OpenSSL
symbols (`BIO_new_mem_buf`, `SSL_CTX_get_cert_store`, etc.) in the final
executable/shared library, even though `openssl` was present and correctly
resolved in the dependency graph. We were able to reduce this down to the
minimal, fully self-contained reproduction included in this directory.

## Environment

- Conan version: 2.32.0 (also fails for 2.31.2) 
- OS: Ubuntu Linux
- Generator: `CMakeConfigDeps` (the new, still-experimental generator)
- Feature: `conan workspace` (`conanws.py`, experimental)

## Root cause (as far as we could determine)

`CMakeConfigDeps` decides which of a dependency's own requirements to expose
as `INTERFACE_LINK_LIBRARIES` on that dependency's generated CMake target by
calling `get_transitive_requires(consumer, dependency)`
(`conan/internal/model/dependencies.py`). That function does:

```python
def get_transitive_requires(consumer, dependency):
    pkg_deps = dependency.dependencies.filter({"direct": True, "build": False})
    result = consumer.dependencies.filter({"skip": False})
    result = result.transitive_requires(pkg_deps)
    return result
```

`consumer` is always the single conanfile that owns the `CMakeConfigDeps(self)`
call - in a workspace, that is the *workspace root* conanfile (`MyWs` in
`conanws.py`), which is the same object for the whole `generate()` run,
regardless of which dependency's target file is currently being generated.

Crucially, `transitive_requires()` (in `ConanFileDependencies`) matches
requirements between `dependency`'s own direct deps and `consumer`'s full
transitive deps **by Python object identity** of the wrapped
`ConanFileInterface`/`ConanFile` objects (`v == otherv`, and
`ConanFileInterface.__eq__`/`__hash__` are identity-based), not by package
reference/revision/package_id.

In a normal (non-workspace) install, there is only ever one graph, so the
`leaf` node reached from `wrapper` and the `leaf` node reached from the
workspace root are the exact same Python object, and everything matches.

Inside `conan workspace super-install`, the graph is affected by the
"collapsing" of the editable workspace member packages (see `core`/`app`
below): when one editable package (`app`) both:

1. depends on another editable package (`core`) as a normal host
   requirement (`self.requires("core/...")`), **and**
2. also depends on the very same editable package as a build-context
   requirement (`self.tool_requires("core/...")`),

...combined with a second, independent package (`lic`) that is only
reachable through `core`'s own `requires()` and that itself requires the
*same* leaf dependency (`leaf`) that is *also* reached completely
independently through `wrapper` - the final "collapsed" graph ends up with
two different Python objects representing what should be the same `leaf`
package node: one used by the (correctly deduplicated) *consumer* view, and
a different, stale one still referenced from `wrapper`'s own
`dependencies` collection.

Because `get_transitive_requires` compares object identity, `wrapper`'s
`leaf` edge (object id `A`) is never found in `consumer`'s transitive deps
(which only contains `leaf` with object id `B`), so the result is empty and
`leaf::leaf` is silently dropped from `wrapper::wrapper`'s generated
`INTERFACE_LINK_LIBRARIES`.

We confirmed this with a one-line debug patch to
`get_transitive_requires()`, printing `id(v._conanfile)` for the `leaf`
entries reached from both `wrapper` and the workspace root - see
`identity-mismatch-evidence.txt` for the captured output from this exact
reproduction. The relevant lines are:

```
DEBUG dependency=wrapper/1.0 pkg_deps=[('leaf/1.0, ... build=False ...', 133158486305504)]
DEBUG consumer_all=[('leaf/1.0, ... build=True ...',  133158481813072),
                     ('leaf/1.0, ... build=False ...', 133158481813072)]
DEBUG RESULT=[]
```

`wrapper`'s own `leaf` node is `133158486305504`; the workspace root's two
`leaf` entries (host and build context) are correctly deduplicated to each
other (`133158481813072` == `133158481813072`), but that id never matches
`wrapper`'s node, so the intersection (`RESULT`) is empty.

## Minimal reproduction

This directory contains a self-contained, minimal Conan workspace using
**only self-written toy recipes** (no Conan Center / third-party packages
required), so it can be run standalone:

```
leaf/1.0     - shared library, package_id() cleared (mirrors a
               "wraps a system library" recipe)
wrapper/1.0  - static library, requires("leaf/1.0"); relies on Conan's
               *implicit* cpp_info.requires
lic/1.0      - static library, ALSO requires("leaf/1.0"); an independent,
               second path to "leaf"
core/4.6.0   - editable workspace member; requires("lic/1.0")
app/4.6.0    - editable workspace member; requires("core/[^4.6]"),
               requires("wrapper/1.0"), requires("leaf/1.0"); AND
               tool_requires("core/[^4.6]") in build_requirements()
               (the dual host+build context requirement on its own
               editable dependency is the second key ingredient)
```

`conanws.py` declares a workspace with `core` and `app` as editable members
and uses `CMakeConfigDeps` + `CMakeToolchain` in its `generate()`.

### Steps to reproduce

```bash
cd conan-workspace-issue
conan create leaf -s build_type=Release
conan create wrapper -s build_type=Release
conan create lic -s build_type=Release
conan workspace super-install -s build_type=Release
cat wrapper-Targets-release.cmake
```

Or simply run `./reproduce.sh`, which does all of the above and checks the
result.

### Expected result

`wrapper-Targets-release.cmake` should contain a block like:

```cmake
# Requirement wrapper::wrapper -> leaf::leaf (Full link: True)
set_property(TARGET wrapper::wrapper APPEND PROPERTY INTERFACE_LINK_LIBRARIES
             "$<$<CONFIG:RELEASE>:leaf::leaf>")
```

### Actual result

No such block is generated at all. `wrapper::wrapper`'s
`INTERFACE_LINK_LIBRARIES` property is never told about `leaf::leaf`, even
though `leaf` is present, correctly resolved, and installed in the graph.
Any target that links only `wrapper::wrapper` will fail to link with
undefined-symbol errors for anything defined in `leaf`.

### Removing either ingredient makes the bug disappear

Both of the following are necessary to trigger the bug; removing either one
on its own produces correct output:

1. Removing `lic`'s (or rather `core`'s) dependency on `lic`/`leaf` (i.e. the
   *second independent path* to `leaf`) - see the isolated ingredient
   analysis below.
2. Removing `app`'s `tool_requires("core/...")` in `build_requirements()`
   (i.e. the *dual host+build context requirement* on its own editable
   dependency `core`).

## Files in this directory

- `conanws.py` - the workspace definition (2 editable packages: `core`, `app`).
- `leaf/conanfile.py`, `wrapper/conanfile.py`, `lic/conanfile.py` - the three
  regular (non-editable) toy packages.
- `core/conanfile.py`, `app/conanfile.py` - the two editable workspace member
  packages.
- `reproduce.sh` - end-to-end script that creates the packages, runs
  `conan workspace super-install`, and checks whether the bug reproduced.
- `identity-mismatch-evidence.txt` - captured debug output showing the
  Python object identity mismatch inside `get_transitive_requires()` for
  this exact reproduction (see "Root cause" above for how it was obtained).
