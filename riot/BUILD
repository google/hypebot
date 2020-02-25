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
load("@hypebot_deps//:requirements.bzl", "requirement")

licenses(["notice"])  # Apache 2.0

package(default_visibility = ["//hypebot:private"])

py_binary(
    name = "riot_api_server",
    srcs = ["riot_api_server.py"],
    deps = [
        "//hypebot/protos/riot/v4:champion_mastery_py_pb2_grpc",
        "//hypebot/protos/riot/v4:constants_py_pb2",
        "//hypebot/protos/riot/v4:league_py_pb2_grpc",
        "//hypebot/protos/riot/v4:match_py_pb2_grpc",
        "//hypebot/protos/riot/v4:summoner_py_pb2_grpc",
        "@io_abseil_py//absl:app",
        "@io_abseil_py//absl/flags",
        "@io_abseil_py//absl/logging",
        requirement("certifi"),
        requirement("chardet"),
        requirement("idna"),
        requirement("requests"),
        requirement("urllib3"),
    ],
)
