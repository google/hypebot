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
    name = "alias_lib",
    srcs = ["alias_lib.py"],
    deps = [
    ],
)

py_library(
    name = "coin_lib",
    srcs = ["coin_lib.py"],
    deps = [
        "//hypebot/core:schedule_lib",
        "//hypebot/core:util_lib",
        "//hypebot/data:messages",
        "//hypebot/protos:bet_py_pb2",
        "@com_google_protobuf//:protobuf_python",
        "@io_abseil_py//absl/logging",
        requirement("arrow"),
    ],
)

py_library(
    name = "deploy_lib",
    srcs = ["deploy_lib.py"],
    deps = [
        ":coin_lib",
        "//hypebot/core:async_lib",
    ],
)

py_library(
    name = "hypestack_lib",
    srcs = ["hypestack_lib.py"],
    deps = [
        ":coin_lib",
        "//hypebot/core:util_lib",
        "//hypebot/storage:storage_lib",
        "@io_abseil_py//absl/logging",
    ],
)

py_library(
    name = "inventory_lib",
    srcs = ["inventory_lib.py"],
    deps = [
        ":coin_lib",
        "//hypebot:types",
        "//hypebot/core:factory_lib",
        "//hypebot/storage:storage_lib",
        "@six_archive//:six",
    ],
)

py_library(
    name = "vegas_game_lib",
    srcs = ["vegas_game_lib.py"],
    deps = [
        ":inventory_lib",
        "//hypebot/core:inflect_lib",
        "//hypebot/core:util_lib",
        "//hypebot/protos:bet_py_pb2",
        "@io_abseil_py//absl/logging",
        "@six_archive//:six",
        requirement("arrow"),
    ],
)

py_library(
    name = "weather_lib",
    srcs = ["weather_lib.py"],
    deps = [
        "//hypebot/core:proxy_lib",
        "//hypebot/protos:weather_py_pb2",
        requirement("arrow"),
    ],
)
