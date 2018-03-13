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
package(default_visibility = ["//visibility:public"])

licenses(["notice"])  # Apache 2.0

load("@org_pubref_rules_protobuf//go:rules.bzl", "go_proto_library")
load("@org_pubref_rules_protobuf//python:rules.bzl", "py_proto_library")

py_proto_library(
    name = "champion_mastery_py_pb2",
    protos = ["champion_mastery.proto"],
    with_grpc = True,
)

go_proto_library(
    name = "champion_mastery_go",
    protos = ["champion_mastery.proto"],
    with_grpc = True,
)

py_proto_library(
    name = "constants_py_pb2",
    protos = ["constants.proto"],
    with_grpc = True,
)

go_proto_library(
    name = "constants_go",
    protos = ["constants.proto"],
    with_grpc = True,
)

py_proto_library(
    name = "league_py_pb2",
    proto_deps = [":constants_py_pb2"],
    protos = ["league.proto"],
    with_grpc = True,
)

go_proto_library(
    name = "league_go",
    proto_deps = [":constants_go"],
    protos = ["league.proto"],
    with_grpc = True,
)

py_proto_library(
    name = "match_py_pb2",
    proto_deps = [":constants_py_pb2"],
    protos = ["match.proto"],
    with_grpc = True,
)

go_proto_library(
    name = "match_go",
    proto_deps = [":constants_go"],
    protos = ["match.proto"],
    with_grpc = True,
)

py_proto_library(
    name = "static_data_py_pb2",
    protos = ["static_data.proto"],
    with_grpc = True,
)

go_proto_library(
    name = "static_data_go",
    protos = ["static_data.proto"],
    verbose = 0,
    with_grpc = True,
)

py_proto_library(
    name = "summoner_py_pb2",
    protos = ["summoner.proto"],
    with_grpc = True,
)

go_proto_library(
    name = "summoner_go",
    protos = ["summoner.proto"],
    with_grpc = True,
)
