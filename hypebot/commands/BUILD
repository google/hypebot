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
    name = "command_lib",
    srcs = ["command_lib.py"],
    deps = [
        "//hypebot/core:params_lib",
        "//hypebot/core:util_lib",
        "//hypebot/data:messages",
        "//hypebot/protos:channel_py_pb2",
        "@io_abseil_py//absl/logging",
    ],
)

py_library(
    name = "command_factory",
    srcs = ["command_factory.py"],
    deps = [
        ":bash_commands",
        ":bling_commands",
        ":deploy_commands",
        ":hypecoin_commands",
        ":hypestack_commands",
        ":interface_commands",
        ":inventory_commands",
        ":public_commands",
        ":remote_commands",
        ":simple_commands",
        "//hypebot/commands/league:lcs_commands",
        "//hypebot/commands/league:lol_commands",
        "//hypebot/commands/league:summoner_commands",
        "//hypebot/commands/league:trivia_commands",
        "//hypebot/core:factory_lib",
    ],
)

py_library(
    name = "bash_commands",
    srcs = ["bash_commands.py"],
    deps = [
        ":command_lib",
        "//hypebot:hypecore",
        "//hypebot/data:messages",
        "//hypebot/plugins:alias_lib",
        "//hypebot/protos:channel_py_pb2",
        "//hypebot/protos:user_py_pb2",
        "@io_abseil_py//absl/logging",
    ],
)

py_library(
    name = "bling_commands",
    srcs = ["bling_commands.py"],
    deps = [
        ":command_lib",
        "//hypebot/core:util_lib",
        "//hypebot/plugins:coin_lib",
        "//hypebot/protos:channel_py_pb2",
    ],
)

py_library(
    name = "deploy_commands",
    srcs = ["deploy_commands.py"],
    deps = [
        ":command_lib",
        "//hypebot:hypecore",
        "//hypebot/core:util_lib",
        "//hypebot/protos:channel_py_pb2",
        "@io_abseil_py//absl/logging",
    ],
)

py_library(
    name = "hypecoin_commands",
    srcs = ["hypecoin_commands.py"],
    deps = [
        ":command_lib",
        "//hypebot/core:inflect_lib",
        "//hypebot/core:params_lib",
        "//hypebot/core:util_lib",
        "//hypebot/data:messages",
        "//hypebot/plugins:coin_lib",
        "//hypebot/protos:bet_py_pb2",
        "//hypebot/protos:channel_py_pb2",
        "@io_abseil_py//absl/logging",
        requirement("arrow"),
    ],
)

py_library(
    name = "hypestack_commands",
    srcs = ["hypestack_commands.py"],
    deps = [
        ":command_lib",
        "//hypebot:hypecore",
        "//hypebot/core:inflect_lib",
        "//hypebot/core:util_lib",
        "//hypebot/protos:channel_py_pb2",
    ],
)

py_library(
    name = "interface_commands",
    srcs = ["interface_commands.py"],
    deps = [
        ":command_lib",
    ],
)

py_library(
    name = "inventory_commands",
    srcs = ["inventory_commands.py"],
    deps = [
        ":command_lib",
        "//hypebot/plugins:inventory_lib",
    ],
)

py_library(
    name = "public_commands",
    srcs = ["public_commands.py"],
    deps = [
        ":command_lib",
        "//hypebot/core:params_lib",
        "//hypebot/core:util_lib",
        "//hypebot/data:messages",
        "//hypebot/plugins:coin_lib",
        "@io_abseil_py//absl/logging",
        requirement("arrow"),
    ],
)

py_library(
    name = "remote_commands",
    srcs = ["remote_commands.py"],
    deps = [
        ":command_lib",
        "//hypebot:types",
        "//hypebot/core:params_lib",
        "//hypebot/core:util_lib",
        "//hypebot/plugins:weather_lib",
    ],
)

py_library(
    name = "simple_commands",
    srcs = ["simple_commands.py"],
    deps = [
        ":command_lib",
        "//hypebot/core:inflect_lib",
        "//hypebot/core:params_lib",
        "//hypebot/core:util_lib",
        "//hypebot/data:messages",
        "//hypebot/plugins:vegas_game_lib",
        "//hypebot/protos:channel_py_pb2",
        "@io_abseil_py//absl/logging",
    ],
)
