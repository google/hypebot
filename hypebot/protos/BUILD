# Copyright 2020 The Hypebot Authors. All rights reserved.
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

load("@rules_proto//proto:defs.bzl", "proto_library")
load("//bazel:python_rules.bzl", "py_proto_library")

licenses(["notice"])  # Apache 2.0

package(default_visibility = ["//hypebot:private"])

proto_library(
    name = "bank_proto",
    srcs = ["bank.proto"],
    deps = ["@com_google_protobuf//:timestamp_proto"],
)

py_proto_library(
    name = "bank_py_pb2",
    deps = ["bank_proto"],
)

proto_library(
    name = "bet_proto",
    srcs = ["bet.proto"],
    deps = ["@com_google_protobuf//:any_proto"],
)

py_proto_library(
    name = "bet_py_pb2",
    deps = ["bet_proto"],
)

proto_library(
    name = "channel_proto",
    srcs = ["channel.proto"],
)

py_proto_library(
    name = "channel_py_pb2",
    deps = ["channel_proto"],
)

proto_library(
    name = "esports_proto",
    srcs = ["esports.proto"],
    deps = ["//hypebot/protos/riot/v4:match_proto"],
)

py_proto_library(
    name = "esports_py_pb2",
    deps = ["esports_proto"],
)

proto_library(
    name = "message_proto",
    srcs = ["message.proto"],
)

py_proto_library(
    name = "message_py_pb2",
    deps = ["message_proto"],
)

proto_library(
    name = "stock_proto",
    srcs = ["stock.proto"],
)

py_proto_library(
    name = "stock_py_pb2",
    deps = ["stock_proto"],
)

proto_library(
    name = "user_proto",
    srcs = ["user.proto"],
)

py_proto_library(
    name = "user_py_pb2",
    deps = ["user_proto"],
)

proto_library(
    name = "weather_proto",
    srcs = ["weather.proto"],
)

py_proto_library(
    name = "weather_py_pb2",
    deps = ["weather_proto"],
)
