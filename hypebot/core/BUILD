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
    name = "async_lib",
    srcs = ["async_lib.py"],
    deps = [
        "@io_abseil_py//absl/logging",
    ],
)

py_library(
    name = "cache_lib",
    srcs = ["cache_lib.py"],
    deps = [
        requirement("arrow"),
    ],
)

py_library(
    name = "factory_lib",
    srcs = ["factory_lib.py"],
    deps = [
        ":params_lib",
        "//hypebot:types",
    ],
)

py_library(
    name = "inflect_lib",
    srcs = ["inflect_lib.py"],
    deps = [
        requirement("inflection"),
    ],
)

py_library(
    name = "name_complete_lib",
    srcs = ["name_complete_lib.py"],
    deps = [
        ":util_lib",
    ],
)

py_library(
    name = "params_lib",
    srcs = ["params_lib.py"],
    deps = [
    ],
)

py_library(
    name = "proxy_lib",
    srcs = ["proxy_lib.py"],
    deps = [
        ":cache_lib",
        ":util_lib",
        "@io_abseil_py//absl/logging",
        requirement("requests"),
    ],
)

py_library(
    name = "schedule_lib",
    srcs = ["schedule_lib.py"],
    deps = [
        "@io_abseil_py//absl/logging",
        requirement("arrow"),
        requirement("apscheduler"),
    ],
)

py_library(
    name = "util_lib",
    srcs = ["util_lib.py"],
    deps = [
        ":params_lib",
        "//hypebot/protos:user_py_pb2",
        requirement("arrow"),
        requirement("six"),
    ],
)

py_test(
    name = "util_lib_test",
    srcs = ["util_lib_test.py"],
    deps = [
        ":util_lib",
        requirement("arrow"),
        requirement("mock"),
    ],
)

py_library(
    name = "zombie_lib",
    srcs = ["zombie_lib.py"],
    deps = [
        "//hypebot/protos:channel_py_pb2",
    ],
)
