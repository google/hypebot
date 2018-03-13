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

	"github.com/vilhelm/hypebot/riot/util"
	leaguepb "github.com/vilhelm/hypebot/hypebot/protos/riot/v3/league_go"

	"golang.org/x/net/context"
)

type LeagueService struct {
	c *http.Client
}

func NewLeagueService(c *http.Client) *LeagueService {
	return &LeagueService{c: c}
}

func (s *LeagueService) ListLeaguePositions(ctx context.Context, in *leaguepb.ListLeaguePositionsRequest) (*leaguepb.ListLeaguePositionsResponse, error) {
	u := &url.URL{
		Host:   fmt.Sprintf("%s.api.riotgames.com", util.GetPlatformID(ctx)),
		Scheme: "https",
		Path:	fmt.Sprintf("/lol/league/v3/positions/by-summoner/%d", in.SummonerId),
	}
	req, err := http.NewRequest("GET", u.String(), nil)
	if err != nil {
		return nil, err
	}

	out := &leaguepb.ListLeaguePositionsResponse{}
	err = util.DoWithAPIKeyAndTransformBody(ctx, s.c, req, func(r io.Reader) io.Reader {
		return io.MultiReader(bytes.NewReader([]byte("{ \"positions\": ")), r, bytes.NewReader([]byte(" }")))
	}, out)
	return out, err
}
