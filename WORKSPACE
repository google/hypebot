# Copyright 2018 The Hypebot Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
workspace(name = "hypebot")

# === Abseil Integration ===
http_archive(
    name = "io_abseil_py",
    strip_prefix = "abseil-py-master",
    urls = ["https://github.com/abseil/abseil-py/archive/master.zip"],
)

# === Python Integration ===
# Use our own fork since it forces python3.
http_archive(
    name = "io_bazel_rules_python",
    strip_prefix = "rules_python-master",
    urls = ["https://github.com/vilhelm/rules_python/archive/master.zip"],
)

# === Go Integration ===
http_archive(
    name = "io_bazel_rules_go",
    strip_prefix = "rules_go-master",
    urls = ["https://github.com/bazelbuild/rules_go/archive/master.zip"],
)

load("@io_bazel_rules_go//go:def.bzl", "go_rules_dependencies", "go_register_toolchains")

go_rules_dependencies()

go_register_toolchains()

# === Par Integration ===
http_archive(
    name = "subpar",
    strip_prefix = "subpar-master",
    urls = ["https://github.com/google/subpar/archive/master.zip"],
)

# === Protobuf Integration
http_archive(
    name = "org_pubref_rules_protobuf",
    strip_prefix = "rules_protobuf-master",
    urls = ["https://github.com/pubref/rules_protobuf/archive/master.zip"],
)

load("@org_pubref_rules_protobuf//python:rules.bzl", "py_proto_repositories")

py_proto_repositories()

load("@org_pubref_rules_protobuf//go:rules.bzl", "go_proto_repositories")

go_proto_repositories()

# === Pip Requirements ===
load("@io_bazel_rules_python//python:pip.bzl", "pip_import")

pip_import(
    name = "hypebot_deps",
    requirements = "//hypebot:requirements.txt",
)

load("@hypebot_deps//:requirements.bzl", "pip_install")

pip_install()

# Recursive workspace declarations required until design is implemented.
# https://bazel.build/designs/2016/09/19/recursive-ws-parsing.html
# absl recursive workspace
new_http_archive(
    name = "six_archive",
    build_file = "third_party/six.BUILD",
    sha256 = "105f8d68616f8248e24bf0e9372ef04d3cc10104f1980f54d57b2ce73a5ad56a",
    strip_prefix = "six-1.10.0",
    urls = [
        "http://mirror.bazel.build/pypi.python.org/packages/source/s/six/six-1.10.0.tar.gz",
        "https://pypi.python.org/packages/source/s/six/six-1.10.0.tar.gz",
    ],
)

bind(
    name = "six",
    actual = "@six_archive//:six",
)

new_http_archive(
    name = "mock_archive",
    build_file = "third_party/mock.BUILD",
    sha256 = "b839dd2d9c117c701430c149956918a423a9863b48b09c90e30a6013e7d2f44f",
    strip_prefix = "mock-1.0.1",
    urls = [
        "http://mirror.bazel.build/pypi.python.org/packages/a2/52/7edcd94f0afb721a2d559a5b9aae8af4f8f2c79bc63fdbe8a8a6c9b23bbe/mock-1.0.1.tar.gz",
        "https://pypi.python.org/packages/a2/52/7edcd94f0afb721a2d559a5b9aae8af4f8f2c79bc63fdbe8a8a6c9b23bbe/mock-1.0.1.tar.gz",
    ],
)
