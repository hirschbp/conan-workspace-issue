from conan import ConanFile
from conan.tools.files import save
import os

class LeafConan(ConanFile):
    # a "wraps an already-installed system library"
    # style recipe that clears its package_id so the exact same binary is
    # reused for every settings/options combination and across contexts.
    name = "leaf"
    version = "1.0"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def package_id(self):
        self.info.clear()

    def package(self):
        save(self, os.path.join(self.package_folder, "lib", "libleaf.so"), "")

    def package_info(self):
        self.cpp_info.set_property("cmake_target_name", "leaf::leaf")
        self.cpp_info.libs = ["leaf"]
