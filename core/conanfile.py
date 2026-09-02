from conan import ConanFile
from conan.tools.cmake import cmake_layout


class CoreConan(ConanFile):
    # an editable workspace member.
    name = "core"
    version = "4.6.0"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("lic/1.0")

    def layout(self):
        cmake_layout(self)
