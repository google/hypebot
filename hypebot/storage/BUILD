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
    name = "storage_factory",
    srcs = ["storage_factory.py"],
    deps = [
        ":memstore_lib",
        ":redis_lib",
        ":storage_lib",
        "//hypebot/core:factory_lib",
    ],
)

py_library(
    name = "storage_lib",
    srcs = ["storage_lib.py"],
    deps = [
        "//hypebot:types",
        "//hypebot/core:params_lib",
        "@io_abseil_py//absl/logging",
        "@six_archive//:six",
        requirement("retrying"),
    ],
)

py_library(
    name = "memstore_lib",
    srcs = ["memstore_lib.py"],
    deps = [
        ":storage_lib",
        "//hypebot:types",
        "//hypebot/core:cache_lib",
    ],
)

py_library(
    name = "redis_lib",
    srcs = ["redis_lib.py"],
    deps = [
        ":storage_lib",
        "//hypebot:types",
        "//hypebot/core:params_lib",
        requirement("redis"),
    ],
)
