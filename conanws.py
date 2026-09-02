from conan import ConanFile, Workspace
from conan.tools.cmake import CMakeConfigDeps, CMakeToolchain

class MyWs(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def generate(self):
        deps = CMakeConfigDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

class MyWorkspace(Workspace):
    def name(self):
        return "repro11"

    def root_conanfile(self):
        return MyWs

    def packages(self):
        return [
            {"path": "core", "ref": "core/4.6.0"},
            {"path": "app", "ref": "app/4.6.0"},
        ]
