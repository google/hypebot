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
load("@org_pubref_rules_protobuf//python:rules.bzl", "py_proto_library")
load("@subpar//:subpar.bzl", "par_binary")

package_group(
    name = "private",
    packages = [
        "//hypebot/...",
    ],
)

py_proto_library(
    name = "all_py_pb2",
    proto_deps = ["//google/protobuf:any_py_pb2"],
    protos = glob(["**/*.proto"]),
    with_grpc = True,
)

py_library(
    name = "hypebot_lib",
    srcs = glob(["**/*.py"]),
    data = glob(["**/*.json"]),
    deps = [
        ":all_py_pb2",
        "@com_google_protobuf//:protobuf_python",
        "@io_abseil_py//absl/flags",
        "@io_abseil_py//absl/logging",
        "@six_archive//:six",
        requirement("arrow"),
        requirement("apscheduler"),
        requirement("discord"),
        requirement("grpcio"),
        requirement("inflection"),
        requirement("redis"),
        requirement("retrying"),
        requirement("requests"),
        requirement("six"),
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
        ":hypebot_lib",
        "@io_abseil_py//absl:app",
    ],
)

par_binary(
    name = "lolbot",
    srcs = ["lolbot.py"],
    default_python_version = "PY3",
    srcs_version = "PY3",
    zip_safe = False,
    deps = [
        ":hypebot_lib",
        "@io_abseil_py//absl:app",
    ],
)
