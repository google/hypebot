// Copyright 2018 The Hypebot Authors. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
package util

import (
	"fmt"
	"io"
	"net/http"
	"strings"

	platformpb "github.com/google/hypebot/hypebot/protos/riot/platform_go"

	"github.com/golang/protobuf/proto"
	"github.com/golang/protobuf/jsonpb"
	"golang.org/x/net/context"
	"google.golang.org/grpc/metadata"
)

func ForwardAPIKey(ctx context.Context, r *http.Request) error {
	md, ok := metadata.FromIncomingContext(ctx)
	if !ok {
		return fmt.Errorf("Failed getting metadata")
	}
	if r.Header == nil {
		r.Header = http.Header{}
	}
	r.Header.Add("X-Riot-Token", strings.Join(md["api-key"], ""))
	return nil
}

func GetPlatformID(ctx context.Context) string {
	md, ok := metadata.FromIncomingContext(ctx)
	if !ok {
		return strings.ToLower(platformpb.PlatformId_NA1.String())
	}
	return strings.Join(md["platform-id"], "")
}

func DoWithAPIKey(ctx context.Context, c *http.Client, req *http.Request, out proto.Message) error {
	return DoWithAPIKeyAndTransformBody(ctx, c, req, func(r io.Reader) io.Reader { return r }, out)
}

func DoWithAPIKeyAndTransformBody(ctx context.Context, c *http.Client, req *http.Request, bodyTrans func(io.Reader) io.Reader, out proto.Message) error {
	err := ForwardAPIKey(ctx, req)
	if err != nil {
		return fmt.Errorf("no API key specified: %v", err)
	}

	resp, err := c.Do(req)
	if err != nil {
		return fmt.Errorf("could not fetch: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return fmt.Errorf("http status %d", resp.StatusCode)
	}

	unmarshaler := &jsonpb.Unmarshaler{AllowUnknownFields: true}
	err = unmarshaler.Unmarshal(bodyTrans(resp.Body), out)
	if err != nil {
		return fmt.Errorf("error parsing response: %v", err)
	}
	return nil
}
