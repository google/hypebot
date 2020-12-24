# Copyright 2020 The Hypebot Authors. All rights reserved.
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
"""Implementation of news_lib.NewsLib powered by NYTimes."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import arrow

from hypebot.core import params_lib
from hypebot.core import util_lib
from hypebot.news import news_lib
from hypebot.protos import message_pb2


class NYTimesNews(news_lib.NewsLib):
  """Data provided by The New York Times."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      news_lib.NewsLib.DEFAULT_PARAMS,
      {
          'base_url': 'https://api.nytimes.com/svc/',
          # Sign up for token at https://developer.nytimes.com
          'api_key': None,
      })

  @property
  def source(self):
    return 'The New York Times'

  @property
  def icon(self):
    return message_pb2.Card.Image(
        url='https://developer.nytimes.com/files/poweredby_nytimes_30a.png',
        alt_text='Data provided by The New York Times')

  def GetHeadlines(self, query, max_results=5):
    endpoint_url = self._params.base_url + 'search/v2/articlesearch.json'
    r = self._proxy.FetchJson(
        endpoint_url,
        params={
            'api-key': self._params.api_key,
            'q': query,
            'sort': 'relevance',
            'fl': 'headline,web_url,source,pub_date',
            'begin_date': arrow.now().shift(years=-1).strftime('%Y%m%d')
        })

    articles = []
    docs = util_lib.Access(r, 'response.docs')
    for doc in docs:
      if 'source' not in doc:
        continue
      articles.append({
          'title': doc['headline'].get('main'),
          'url': doc['web_url'],
          'source': doc['source'],
          'pub_date': doc['pub_date']
      })
    return articles[:max_results]

  def GetTrending(self, max_results=5):
    endpoint_url = self._params.base_url + 'topstories/v2/home.json'
    r = self._proxy.FetchJson(
        endpoint_url,
        params={'api-key': self._params.api_key},
        force_lookup=True)
    articles = []
    for article in [a for a in r['results'] if a.get('title')][:max_results]:
      articles.append({
          'title': article['title'],
          'url': article['short_url'],
          'abstract': article['abstract'],
      })

    return articles
