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
package(default_visibility = ["//hypebot:private"])

licenses(["notice"])  # Apache 2.0

load("@hypebot_deps//:requirements.bzl", "requirement")

py_library(
    name = "interface_lib",
    srcs = ["interface_lib.py"],
    deps = [
        "//hypebot:types",
        "//hypebot/core:params_lib",
        "@io_abseil_py//absl/logging",
        "@six_archive//:six",
    ],
)

py_library(
    name = "interface_factory",
    srcs = ["interface_factory.py"],
    deps = [
        ":capture_interface",
        ":discord_interface",
        ":interface_lib",
        "//hypebot/core:factory_lib",
    ],
)

py_library(
    name = "capture_interface",
    srcs = ["capture_interface.py"],
    deps = [
        ":interface_lib",
        "//hypebot:types",
    ],
)

py_library(
    name = "discord_interface",
    srcs = ["discord_interface.py"],
    deps = [
        ":interface_lib",
        "//hypebot:types",
        "//hypebot/core:params_lib",
        "//hypebot/protos:channel_py_pb2",
        "@io_abseil_py//absl/logging",
        requirement("discord"),
    ],
)
