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
    name = "lcs_commands",
    srcs = ["lcs_commands.py"],
    deps = [
        "//hypebot/commands:command_lib",
        "//hypebot/core:inflect_lib",
        "//hypebot/core:params_lib",
        "//hypebot/core:util_lib",
        "//hypebot/data/league:messages",
        "@io_abseil_py//absl/flags",
        requirement("arrow"),
    ],
)

py_library(
    name = "lol_commands",
    srcs = ["lol_commands.py"],
    deps = [
        "//hypebot/commands:command_lib",
        "//hypebot/core:params_lib",
        "//hypebot/core:util_lib",
        "//hypebot/data/league:messages",
        "@io_abseil_py//absl/logging",
    ],
)

py_library(
    name = "summoner_commands",
    srcs = ["summoner_commands.py"],
    deps = [
        "//hypebot/commands:command_lib",
        "//hypebot/core:inflect_lib",
        "//hypebot/core:util_lib",
        "//hypebot/data/league:messages",
        "//hypebot/plugins/league:summoner_lib",
        requirement("arrow"),
    ],
)

py_library(
    name = "trivia_commands",
    srcs = ["trivia_commands.py"],
    deps = [
        "//hypebot/commands:command_lib",
    ],
)
