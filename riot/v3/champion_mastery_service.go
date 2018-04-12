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
	cmasterypb "github.com/google/hypebot/hypebot/protos/riot/v3/champion_mastery_go"

	"golang.org/x/net/context"
)

type ChampionMasteryService struct {
	c *http.Client
}

func NewChampionMasteryService(c *http.Client) *ChampionMasteryService {
	return &ChampionMasteryService{c: c}
}

func (s *ChampionMasteryService) ListChampionMasteries(ctx context.Context, in *cmasterypb.ListChampionMasteriesRequest) (*cmasterypb.ListChampionMasteriesResponse, error) {
	u := &url.URL{
		Host:   fmt.Sprintf("%s.api.riotgames.com", util.GetPlatformID(ctx)),
		Scheme: "https",
		Path:	fmt.Sprintf("/lol/champion-mastery/v3/champion-masteries/by-summoner/%d", in.SummonerId),
	}
	req, err := http.NewRequest("GET", u.String(), nil)
	if err != nil {
		return nil, err
	}

	out := &cmasterypb.ListChampionMasteriesResponse{}
	err = util.DoWithAPIKeyAndTransformBody(ctx, s.c, req, func(r io.Reader) io.Reader {
		return io.MultiReader(bytes.NewReader([]byte("{ \"championMasteries\": ")), r, bytes.NewReader([]byte(" }")))
	}, out)
	return out, err
}

func (s *ChampionMasteryService) GetChampionMastery(ctx context.Context, in *cmasterypb.GetChampionMasteryRequest) (*cmasterypb.ChampionMastery, error) {
	u := &url.URL{
		Host:   fmt.Sprintf("%s.api.riotgames.com", util.GetPlatformID(ctx)),
		Scheme: "https",
		Path:	fmt.Sprintf("/lol/champion-mastery/v3/champion-masteries/by-summoner/%d/by-champion/%d", in.SummonerId, in.ChampionId),
	}
	req, err := http.NewRequest("GET", u.String(), nil)
	if err != nil {
		return nil, err
	}

	out := &cmasterypb.ChampionMastery{}
	err = util.DoWithAPIKey(ctx, s.c, req, out)
	return out, err
}

func (s *ChampionMasteryService) GetChampionMasteryScore(ctx context.Context, in *cmasterypb.GetChampionMasteryScoreRequest) (*cmasterypb.ChampionMasteryScore, error) {
	u := &url.URL{
		Host:   fmt.Sprintf("%s.api.riotgames.com", util.GetPlatformID(ctx)),
		Scheme: "https",
		Path:	fmt.Sprintf("/lol/champion-mastery/v3/scores/by-summoner/%d", in.SummonerId),
	}
	req, err := http.NewRequest("GET", u.String(), nil)
	if err != nil {
		return nil, err
	}

	out := &cmasterypb.ChampionMasteryScore{}
	err = util.DoWithAPIKeyAndTransformBody(ctx, s.c, req, func(r io.Reader) io.Reader {
		return io.MultiReader(bytes.NewReader([]byte("{ \"score\": ")), r, bytes.NewReader([]byte(" }")))
	}, out)
	return out, err
}
