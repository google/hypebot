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

load("@io_bazel_rules_go//go:def.bzl", "go_library")
load("@org_pubref_rules_protobuf//go:rules.bzl", "GRPC_COMPILE_DEPS")

go_library(
    name = "api",
    srcs = [
        "champion_mastery_service.go",
        "league_service.go",
        "match_service.go",
        "static_data_service.go",
        "summoner_service.go",
    ],
    deps = [
        "//riot:util",
        "//hypebot/protos/riot/v3:champion_mastery_go",
        "//hypebot/protos/riot/v3:league_go",
        "//hypebot/protos/riot/v3:match_go",
        "//hypebot/protos/riot/v3:static_data_go",
        "//hypebot/protos/riot/v3:summoner_go",
    ] + GRPC_COMPILE_DEPS,
)
