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
	"strconv"

	"github.com/vilhelm/hypebot/riot/util"
	matchpb "github.com/vilhelm/hypebot/hypebot/protos/riot/v3/match_go"

	"golang.org/x/net/context"
)

type MatchService struct {
	c *http.Client
}

func NewMatchService(c *http.Client) *MatchService {
	return &MatchService{c: c}
}

func (s *MatchService) ListMatches(ctx context.Context, in *matchpb.ListMatchesRequest) (*matchpb.ListMatchesResponse, error) {
	u := &url.URL{
		Host:   fmt.Sprintf("%s.api.riotgames.com", util.GetPlatformID(ctx)),
		Scheme: "https",
		Path:   fmt.Sprintf("/lol/match/v3/matchlists/by-account/%d", in.AccountId),
	}
	v := url.Values{}
	for _, q := range in.Queues {
		v.Add("queue", strconv.Itoa(int(q)))
	}
	for _, s := range in.Seasons {
		v.Add("season", strconv.Itoa(int(s)))
	}
	for _, c := range in.Champions {
		v.Add("champion", strconv.Itoa(int(c)))
	}
	if in.BeginTimeMs != 0 || in.EndTimeMs != 0 {
		v.Set("beginTime", strconv.FormatInt(in.BeginTimeMs, 10))
		v.Set("endTime", strconv.FormatInt(in.EndTimeMs, 10))
	}
	if in.BeginIndex != 0 || in.EndIndex != 0 {
		v.Set("beginIndex", strconv.Itoa(int(in.BeginIndex)))
		v.Set("endIndex", strconv.Itoa(int(in.EndIndex)))
	}
	u.RawQuery = v.Encode()

	req, err := http.NewRequest("GET", u.String(), nil)
	if err != nil {
		return nil, err
	}

	out := &matchpb.ListMatchesResponse{}
	err = util.DoWithAPIKey(ctx, s.c, req, out)
	return out, err
}

func (s *MatchService) ListTournamentMatchIds(ctx context.Context, in *matchpb.ListTournamentMatchIdsRequest) (*matchpb.ListTournamentMatchIdsResponse, error) {
	u := &url.URL{
		Host:	fmt.Sprintf("%s.api.riotgames.com", util.GetPlatformID(ctx)),
		Scheme:	"https",
		Path:	fmt.Sprintf("/lol/match/v3/matches/by-tournament-code/%s/ids", url.PathEscape(in.TournamentCode)),
	}
	req, err := http.NewRequest("GET", u.String(), nil)
	if err != nil {
		return nil, err
	}

	out := &matchpb.ListTournamentMatchIdsResponse{}
	err = util.DoWithAPIKeyAndTransformBody(ctx, s.c, req, func(r io.Reader) io.Reader {
		return io.MultiReader(bytes.NewReader([]byte("{ \"gameIds\": ")), r, bytes.NewReader([]byte(" }")))
	}, out)
	return out, err
}

func (s *MatchService) GetMatch(ctx context.Context, in *matchpb.GetMatchRequest) (*matchpb.Match, error) {
	u := &url.URL{
		Host:   fmt.Sprintf("%s.api.riotgames.com", util.GetPlatformID(ctx)),
		Scheme: "https",
	}
	if in.TournamentCode == "" {
		u.Path = fmt.Sprintf("/lol/match/v3/matches/%d", in.GameId)
	} else {
		u.Path = fmt.Sprintf("/lol/match/v3/matches/%d/by-tournament-code/%s", in.GameId, in.TournamentCode)
	}

	req, err := http.NewRequest("GET", u.String(), nil)
	if err != nil {
		return nil, err
	}
	out := &matchpb.Match{}
	err = util.DoWithAPIKey(ctx, s.c, req, out)
	return out, err
}
