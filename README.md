# Conan Workspace / CMakeConfigDeps transitive dependency drop

Minimal, fully self-contained reproduction of a bug where `CMakeConfigDeps`
silently drops a transitive `INTERFACE_LINK_LIBRARIES` entry for a package
inside a `conan workspace`.

See [BUG_REPORT.md](BUG_REPORT.md) for the full write-up (root cause,
environment, and detailed analysis) and
[identity-mismatch-evidence.txt](identity-mismatch-evidence.txt) for captured
debug evidence.

## Quick start

```bash
./reproduce.sh
```

This creates the `leaf`, `wrapper`, and `lic` packages, runs
`conan workspace super-install`, and checks whether
`wrapper-Targets-release.cmake` is missing its `leaf::leaf` link (it should
be there, but isn't).

## Layout

| Path | Role |
|---|---|
| `leaf/` | Toy dependency |
| `wrapper/` | Depends on `leaf` via implicit `cpp_info.requires` |
| `lic/` | Independent second path to `leaf` |
| `core/` | Editable workspace member, requires `lic` |
| `app/` | Editable workspace member, requires `core` + `wrapper` + `leaf`, and also `tool_requires` `core` |
| `conanws.py` | Workspace definition (`core` + `app` as editable members) |
