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
load("@subpar//:subpar.bzl", "par_binary")

package_group(
    name = "private",
    packages = [
        "//hypebot/...",
    ],
)

par_binary(
    name = "basebot",
    srcs = ["basebot.py"],
    default_python_version = "PY3",
    srcs_version = "PY3",
    # Required since cacert.pem is not extracted otherwise.
    zip_safe = False,
    deps = [
        ":hypecore",
        "//hypebot/commands:command_factory",
        "//hypebot/core:params_lib",
        "//hypebot/core:util_lib",
        "//hypebot/interfaces:interface_factory",
        "//hypebot/plugins:alias_lib",
        "//hypebot/plugins:vegas_game_lib",
        "//hypebot/protos:channel_py_pb2",
        "@io_abseil_py//absl:app",
        "@io_abseil_py//absl/flags",
        "@io_abseil_py//absl/logging",
        requirement("arrow"),
    ],
)

par_binary(
    name = "lolbot",
    srcs = ["lolbot.py"],
    default_python_version = "PY3",
    srcs_version = "PY3",
    zip_safe = False,
    deps = [
        ":basebot",
        "//hypebot/core:params_lib",
        "//hypebot/data/league:messages",
        "//hypebot/plugins:vegas_game_lib",
        "//hypebot/plugins/league:esports_lib",
        "//hypebot/plugins/league:game_lib",
        "//hypebot/plugins/league:items_lib",
        "//hypebot/plugins/league:rito_lib",
        "//hypebot/plugins/league:summoner_lib",
        "//hypebot/plugins/league:trivia_lib",
        "//hypebot/protos:channel_py_pb2",
        "@io_abseil_py//absl:app",
        "@io_abseil_py//absl/flags",
    ],
)

py_library(
    name = "hypecore",
    srcs = ["hypecore.py"],
    deps = [
        ":types",
        "//hypebot/core:async_lib",
        "//hypebot/core:proxy_lib",
        "//hypebot/core:schedule_lib",
        "//hypebot/core:util_lib",
        "//hypebot/core:zombie_lib",
        "//hypebot/interfaces:interface_lib",
        "//hypebot/plugins:coin_lib",
        "//hypebot/plugins:deploy_lib",
        "//hypebot/plugins:hypestack_lib",
        "//hypebot/plugins:inventory_lib",
        "//hypebot/protos:channel_py_pb2",
        "//hypebot/stocks:stock_factory",
        "//hypebot/storage:storage_factory",
    ],
)

py_library(
    name = "types",
    srcs = ["types.py"],
    deps = [
        "//hypebot/protos:channel_py_pb2",
        "//hypebot/protos:message_py_pb2",
    ],
)
