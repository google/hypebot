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
load("@subpar//:subpar.bzl", "par_binary")

licenses(["notice"])  # Apache 2.0

package(default_visibility = ["//hypebot:private"])

package_group(
    name = "private",
    packages = [
        "//hypebot/...",
        "//riot/...",
    ],
)

py_library(
    name = "all_py_pb2",
    deps = [
        "//hypebot/protos:bank_py_pb2",
        "//hypebot/protos:bet_py_pb2",
        "//hypebot/protos:channel_py_pb2",
        "//hypebot/protos:esports_py_pb2",
        "//hypebot/protos:message_py_pb2",
        "//hypebot/protos:stock_py_pb2",
        "//hypebot/protos:user_py_pb2",
        "//hypebot/protos:weather_py_pb2",
        "//hypebot/protos/riot:platform_py_pb2",
        "//hypebot/protos/riot/v3:static_data_py_pb2",
        "//hypebot/protos/riot/v4:champion_mastery_py_pb2_grpc",
        "//hypebot/protos/riot/v4:constants_py_pb2",
        "//hypebot/protos/riot/v4:league_py_pb2_grpc",
        "//hypebot/protos/riot/v4:match_py_pb2_grpc",
        "//hypebot/protos/riot/v4:summoner_py_pb2_grpc",
    ],
)

py_library(
    name = "hypebot_lib",
    srcs = glob(["**/*.py"]),
    data = glob(["**/*.json"]),
    deps = [
        ":all_py_pb2",
        "@io_abseil_py//absl/flags",
        "@io_abseil_py//absl/logging",
        "@six_archive//:six",
        requirement("aiohttp"),
        requirement("arrow"),
        requirement("async_timeout"),
        requirement("attrs"),
        requirement("apscheduler"),
        requirement("certifi"),
        requirement("chardet"),
        requirement("discord.py"),
        requirement("grpcio"),
        requirement("idna"),
        requirement("inflection"),
        requirement("multidict"),
        requirement("python-dateutil"),
        requirement("redis"),
        requirement("retrying"),
        requirement("requests"),
        requirement("six"),
        requirement("urllib3"),
        requirement("websockets"),
        requirement("yarl"),
    ],
)

par_binary(
    name = "basebot",
    srcs = ["basebot.py"],
    # Required since cacert.pem is not extracted otherwise.
    zip_safe = False,
    deps = [
        ":hypebot_lib",
        "@io_abseil_py//absl:app",
    ],
)

par_binary(
    name = "lolbot",
    srcs = ["lolbot.py"],
    zip_safe = False,
    deps = [
        ":hypebot_lib",
        "@io_abseil_py//absl:app",
    ],
)
