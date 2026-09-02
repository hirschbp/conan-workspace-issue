from conan import ConanFile
from conan.tools.files import save
import os

class WrapperConan(ConanFile):
    # depends on "leaf" transitively, relying on
    # Conan's automatic "implicit requires" (no explicit cpp_info.requires
    # set in package_info()).
    name = "wrapper"
    version = "1.0"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("leaf/1.0")

    def package(self):
        save(self, os.path.join(self.package_folder, "lib", "libwrapper.a"), "")

    def package_info(self):
        self.cpp_info.set_property("cmake_target_name", "wrapper::wrapper")
        self.cpp_info.libs = ["wrapper"]
