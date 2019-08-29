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
"""League trivia commands."""

from hypebot.commands import command_lib
from hypebot.core import params_lib


@command_lib.CommandRegexParser(r'trivia ?([0-9]*)')
class TriviaAddCommand(command_lib.BaseCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'main_channel_only': False,
      })

  def _Handle(self, channel, user, num_questions):
    if not self._core.trivia.IsTrivaChannel(channel):
      return
    num_questions = min(int(num_questions or 1), 10)
    self._core.trivia.AddQuestions(channel, num_questions)


@command_lib.PublicParser
class TriviaAnswerCommand(command_lib.BasePublicCommand):

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS, {
          'main_channel_only': False,
      })

  def _Handle(self, channel, user, message):
    if not self._core.trivia.IsTrivaChannel(channel):
      return
    self._core.trivia.CheckAnswer(channel, user, message)
