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
    name = "esports_lib",
    srcs = ["esports_lib.py"],
    deps = [
        "//hypebot/core:name_complete_lib",
        "//hypebot/core:util_lib",
        "//hypebot/data/league:messages",
        "//hypebot/data/league:nicknames",
        "@io_abseil_py//absl/logging",
        requirement("arrow"),
    ],
)

py_library(
    name = "game_lib",
    srcs = ["game_lib.py"],
    deps = [
        "//hypebot/core:name_complete_lib",
        "//hypebot/core:util_lib",
        "//hypebot/data/league:nicknames",
    ],
)

py_library(
    name = "items_lib",
    srcs = ["items_lib.py"],
    deps = [
        "//hypebot/core:name_complete_lib",
    ],
)

py_library(
    name = "rito_lib",
    srcs = ["rito_lib.py"],
    deps = [
        "//hypebot/protos/riot:platform_py_pb2",
        "//hypebot/protos/riot/v3:champion_mastery_py_pb2",
        "//hypebot/protos/riot/v3:league_py_pb2",
        "//hypebot/protos/riot/v3:match_py_pb2",
        "//hypebot/protos/riot/v3:static_data_py_pb2",
        "//hypebot/protos/riot/v3:summoner_py_pb2",
        "@com_google_protobuf//:protobuf_python",
        "@io_abseil_py//absl/logging",
        requirement("grpcio"),
    ],
)

py_library(
    name = "summoner_lib",
    srcs = [
        "summoner_lib.py",
    ],
    deps = [
        "//hypebot/core:inflect_lib",
        "//hypebot/protos/riot/v3:constants_py_pb2",
        "//hypebot/protos/riot/v3:league_py_pb2",
        "@io_abseil_py//absl/logging",
        requirement("arrow"),
    ],
)

py_library(
    name = "trivia_lib",
    srcs = [
        "trivia_lib.py",
    ],
    deps = [
        ":game_lib",
        "//hypebot/core:util_lib",
        "@io_abseil_py//absl/flags",
        "@io_abseil_py//absl/logging",
    ],
)
