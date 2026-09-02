from conan import ConanFile
from conan.tools.cmake import cmake_layout


class AppConan(ConanFile):
    # an editable workspace member that depends on "core".
    name = "app"
    version = "4.6.0"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # Editable-to-editable dependency
        self.requires("core/[^4.6]", transitive_headers=True, transitive_libs=True)
        # requires "wrapper" AND "leaf" directly, in the SAME requirements() method,
        # while "wrapper" also transitively requires "leaf" itself.
        self.requires("wrapper/1.0")
        self.requires("leaf/1.0")

    def build_requirements(self):
        # THE KEY FACTOR: ALSO tool_requires
        # core (its own editable dependency) as a build-context
        # requirement, in addition to the regular host-context requires()
        # above.
        self.tool_requires("core/[^4.6]")

    def layout(self):
        cmake_layout(self)
