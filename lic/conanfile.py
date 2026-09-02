from conan import ConanFile
from conan.tools.files import save
import os

class LicConan(ConanFile):
    # an independent package that ALSO requires
    # "leaf", providing a second path to it that does not
    # go through "wrapper".
    name = "lic"
    version = "1.0"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("leaf/1.0")

    def package(self):
        save(self, os.path.join(self.package_folder, "lib", "liblic.a"), "")

    def package_info(self):
        self.cpp_info.set_property("cmake_target_name", "lic::lic")
        self.cpp_info.libs = ["lic"]
