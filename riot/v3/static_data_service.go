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
package api

import (
	"bytes"
	"fmt"
	"io"
	"net/http"
	"net/url"

	"github.com/google/hypebot/riot/util"
	staticpb "github.com/google/hypebot/hypebot/protos/riot/v3/static_data_go"

	"golang.org/x/net/context"
)

type StaticDataService struct {
	c *http.Client
}

func NewStaticDataService(c *http.Client) *StaticDataService {
	return &StaticDataService{c: c}
}

func (s *StaticDataService) ListChampions(ctx context.Context, in *staticpb.ListChampionsRequest) (*staticpb.ListChampionsResponse, error) {
	u := &url.URL{
		Host:   fmt.Sprintf("%s.api.riotgames.com", util.GetPlatformID(ctx)),
		Scheme: "https",
		Path:   "/lol/static-data/v3/champions",
	}
	v := url.Values{}
	if in.Locale != "" {
		v.Add("locale", in.Locale)
	}
	if in.Version != "" {
		v.Add("version", in.Version)
	}
	for _, t := range in.Tags {
		v.Add("tags", t)
	}
	if in.DataById {
		v.Add("dataById", "true")
	}
	u.RawQuery = v.Encode()

	req, err := http.NewRequest("GET", u.String(), nil)
	if err != nil {
		return nil, err
	}
	out := &staticpb.ListChampionsResponse{}
	err = util.DoWithAPIKey(ctx, s.c, req, out)
	return out, err
}

func (s *StaticDataService) ListItems(ctx context.Context, in *staticpb.ListItemsRequest) (*staticpb.ListItemsResponse, error) {
	u := &url.URL{
		Host:   fmt.Sprintf("%s.api.riotgames.com", util.GetPlatformID(ctx)),
		Scheme: "https",
		Path:   "/lol/static-data/v3/items",
	}
	v := url.Values{}
	if in.Locale != "" {
		v.Add("locale", in.Locale)
	}
	if in.Version != "" {
		v.Add("version", in.Version)
	}
	for _, t := range in.Tags {
		v.Add("tags", t)
	}
	u.RawQuery = v.Encode()

	req, err := http.NewRequest("GET", u.String(), nil)
	if err != nil {
		return nil, err
	}
	out := &staticpb.ListItemsResponse{}
	err = util.DoWithAPIKey(ctx, s.c, req, out)
	return out, err
}

func (s *StaticDataService) ListMasteries(ctx context.Context, in *staticpb.ListMasteriesRequest) (*staticpb.ListMasteriesResponse, error) {
	u := &url.URL{
		Host:   fmt.Sprintf("%s.api.riotgames.com", util.GetPlatformID(ctx)),
		Scheme: "https",
		Path:   "/lol/static-data/v3/masteries",
	}
	v := url.Values{}
	if in.Locale != "" {
		v.Add("locale", in.Locale)
	}
	if in.Version != "" {
		v.Add("version", in.Version)
	}
	for _, t := range in.Tags {
		v.Add("tags", t)
	}
	u.RawQuery = v.Encode()

	req, err := http.NewRequest("GET", u.String(), nil)
	if err != nil {
		return nil, err
	}
	out := &staticpb.ListMasteriesResponse{}
	err = util.DoWithAPIKey(ctx, s.c, req, out)
	return out, err
}

func (s *StaticDataService) ListReforgedRunePaths(ctx context.Context, in *staticpb.ListReforgedRunePathsRequest) (*staticpb.ListReforgedRunePathsResponse, error) {
	u := &url.URL{
		Host:   fmt.Sprintf("%s.api.riotgames.com", util.GetPlatformID(ctx)),
		Scheme: "https",
		Path:   "/lol/static-data/v3/reforged-rune-paths",
	}
	v := url.Values{}
	if in.Locale != "" {
		v.Add("locale", in.Locale)
	}
	if in.Version != "" {
		v.Add("version", in.Version)
	}
	u.RawQuery = v.Encode()

	req, err := http.NewRequest("GET", u.String(), nil)
	if err != nil {
		return nil, err
	}
	out := &staticpb.ListReforgedRunePathsResponse{}
	err = util.DoWithAPIKeyAndTransformBody(ctx, s.c, req, func(r io.Reader) io.Reader {
		return io.MultiReader(bytes.NewReader([]byte("{ \"paths\": ")), r, bytes.NewReader([]byte(" }")))
	}, out)
	return out, err
}
