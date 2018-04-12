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
package main

import (
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"

	"github.com/google/hypebot/riot/v3/api"
	cmasterypb "github.com/google/hypebot/hypebot/protos/riot/v3/champion_mastery_go"
	leaguepb "github.com/google/hypebot/hypebot/protos/riot/v3/league_go"
	matchpb "github.com/google/hypebot/hypebot/protos/riot/v3/match_go"
	staticpb "github.com/google/hypebot/hypebot/protos/riot/v3/static_data_go"
	summonerpb "github.com/google/hypebot/hypebot/protos/riot/v3/summoner_go"

	"google.golang.org/grpc"
)

var (
	hostname = flag.String("host", "localhost", "The server hostname")
	port = flag.Int("port", 50051, "The server port")
)

func main() {
	flag.Parse()
	log.Printf("%s:%d", *hostname, *port)
	lis, err := net.Listen("tcp", fmt.Sprintf("%s:%d", *hostname, *port))
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}

	tr := &http.Transport{
		MaxIdleConns:	10,
	}

	s := grpc.NewServer()
	// Register all Riot API RPC services.
	cmasterypb.RegisterChampionMasteryServiceServer(s, api.NewChampionMasteryService(&http.Client{Transport: tr}))
	leaguepb.RegisterLeagueServiceServer(s, api.NewLeagueService(&http.Client{Transport: tr}))
	matchpb.RegisterMatchServiceServer(s, api.NewMatchService(&http.Client{Transport: tr}))
	staticpb.RegisterStaticDataServiceServer(s, api.NewStaticDataService(&http.Client{Transport: tr}))
	summonerpb.RegisterSummonerServiceServer(s, api.NewSummonerService(&http.Client{Transport: tr}))

	s.Serve(lis)
}
