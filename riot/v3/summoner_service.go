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
	"fmt"
	"net/http"
	"net/url"

	"github.com/vilhelm/hypebot/riot/util"
	summonerpb "github.com/vilhelm/hypebot/hypebot/protos/riot/v3/summoner_go"

	"golang.org/x/net/context"
)

type SummonerService struct {
	c *http.Client
}

func NewSummonerService(c *http.Client) *SummonerService {
	return &SummonerService{c: c}
}

func (s *SummonerService) GetSummoner(ctx context.Context, in *summonerpb.GetSummonerRequest) (*summonerpb.Summoner, error) {
	u := &url.URL{
		Host:   fmt.Sprintf("%s.api.riotgames.com", util.GetPlatformID(ctx)),
		Scheme: "https",
	}
	switch x := in.Key.(type) {
	case *summonerpb.GetSummonerRequest_AccountId:
		u.Path = fmt.Sprintf("/lol/summoner/v3/summoners/by-account/%d", x.AccountId)
	case *summonerpb.GetSummonerRequest_Id:
		u.Path = fmt.Sprintf("/lol/summoner/v3/summoners/%d", x.Id)
	case *summonerpb.GetSummonerRequest_Name:
		u.Path = fmt.Sprintf("/lol/summoner/v3/summoners/by-name/%s", x.Name)
	default:
		return nil, fmt.Errorf("GetSummoner: no key specified")
	}

	req, err := http.NewRequest("GET", u.String(), nil)
	if err != nil {
		return nil, err
	}
	out := &summonerpb.Summoner{}
	err = util.DoWithAPIKey(ctx, s.c, req, out)
	return out, err
}
