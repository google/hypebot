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
load("@com_github_grpc_grpc//bazel:python_rules.bzl", "py_grpc_library", "py_proto_library")

licenses(["notice"])  # Apache 2.0

package(default_visibility = ["//hypebot:private"])

proto_library(
    name = "champion_mastery_proto",
    srcs = ["champion_mastery.proto"],
)

py_proto_library(
    name = "champion_mastery_py_pb2",
    deps = [":champion_mastery_proto"],
)

py_grpc_library(
    name = "champion_mastery_py_pb2_grpc",
    srcs = [":champion_mastery_proto"],
    deps = [":champion_mastery_py_pb2"],
)

proto_library(
    name = "constants_proto",
    srcs = ["constants.proto"],
)

py_proto_library(
    name = "constants_py_pb2",
    deps = [":constants_proto"],
)

proto_library(
    name = "league_proto",
    srcs = ["league.proto"],
    deps = [":constants_proto"],
)

py_proto_library(
    name = "league_py_pb2",
    deps = [":league_proto"],
)

py_grpc_library(
    name = "league_py_pb2_grpc",
    srcs = [":league_proto"],
    deps = [":league_py_pb2"],
)

proto_library(
    name = "match_proto",
    srcs = ["match.proto"],
    deps = [":constants_proto"],
)

py_proto_library(
    name = "match_py_pb2",
    deps = [":match_proto"],
)

py_grpc_library(
    name = "match_py_pb2_grpc",
    srcs = [":match_proto"],
    deps = [":match_py_pb2"],
)

proto_library(
    name = "summoner_proto",
    srcs = ["summoner.proto"],
)

py_proto_library(
    name = "summoner_py_pb2",
    deps = [":summoner_proto"],
)

py_grpc_library(
    name = "summoner_py_pb2_grpc",
    srcs = [":summoner_proto"],
    deps = [":summoner_py_pb2"],
)
