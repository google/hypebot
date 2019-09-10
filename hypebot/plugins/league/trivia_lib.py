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
"""Contains classes for trivia bot."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import operator
import random
import threading

from absl import flags
from absl import logging

from hypebot.core import util_lib

FLAGS = flags.FLAGS

flags.DEFINE_integer('trivia_delay_seconds', 3, 'Number of seconds to wait '
                     'between trivia questions.')


class TriviaMaster(object):
  """Class which manages the trivia for multiple channels.

  This should only be instantiated once.
  """

  def __init__(self, game_lib, msg_fn):
    """Create a new TriviaMaster.

    Args:
      game_lib: a functional instance of game_lib.GameLib.
      msg_fn: function to allow Trivia to send messages.
    """
    self._question_maker = QuestionMaker(game_lib)
    self._msg_fn = msg_fn
    # keeps track of channel id -> TriviaChannel
    self._channel_map = {}

  def IsTrivaChannel(self, channel):
    return channel.id in self._channel_map

  def MakeNewChannel(self, channel):
    """Set up a TriviaChannel for the given channel, if it doesn't exist."""
    if self.IsTrivaChannel(channel):
      return
    self._channel_map[channel.id] = TriviaChannel(
        channel, self._question_maker, self._msg_fn)

  def AddQuestions(self, channel, num_questions):
    if not self.IsTrivaChannel(channel):
      return
    trivia_channel = self._channel_map[channel.id]
    trivia_channel.AddQuestions(num_questions)

  def CheckAnswer(self, channel, username, answer):
    if not self.IsTrivaChannel(channel):
      return
    trivia_channel = self._channel_map[channel.id]
    trivia_channel.CheckAnswer(username, answer)


class TriviaChannel(object):
  """Class which manages the trivia for one channel.

  Makes sure there is only one active question at a time.
  """

  _DEFAULT_TIMEOUT_SEC = 30
  _MAX_QUESTIONS = 30

  def __init__(self, channel, question_maker, msg_fn):
    """Create a new TriviaChannel.

    Args:
      channel: channel
      question_maker: instance of QuestionMaker()
      msg_fn: function to allow sending of messages.
    """

    self._question_maker = question_maker
    self._channel = channel
    self._msg_fn = msg_fn

    # number of pending questions to do. do a question if this > 0.
    # TODO: there is a potential race condition on this number if not
    # for the global interpreter lock
    self._num_questions_remaining = 0
    # The Question to currently be answered.
    self._current_question = None
    # The pending timeout timer for the current question.
    self._timeout_timer = None
    # Lock around the current question. Acquire this to change the status of the
    # current question.
    self._question_lock = threading.Lock()
    # Temporary leaderboard for a quiz session.
    self._leaderboard = Leaderboard()
    # Set of already seen hashed questions
    self._questions = set()

  def HasCurrentQuestion(self):
    return self._current_question is not None

  def AddQuestions(self, num):
    if self._num_questions_remaining == 0 and num >= 3:
      self._leaderboard.BeginGame()
    self._num_questions_remaining += num
    self._MaybeStartNewQuestion()

  def _MaybeStartNewQuestion(self):
    must_callback = False
    question = None
    with self._question_lock:
      if self._num_questions_remaining <= 0:
        self._questions.clear()
        self._leaderboard.AttemptToFinishGame(self._msg_fn, self._channel)
        return
      if self._num_questions_remaining >= self._MAX_QUESTIONS:
        self._num_questions_remaining = self._MAX_QUESTIONS
      if self.HasCurrentQuestion():
        return
      self._current_question = self._question_maker.GetRandomQuestion()
      self._timeout_timer = threading.Timer(
          self._DEFAULT_TIMEOUT_SEC, self._TimeoutQuestion)
      self._timeout_timer.start()
      self._num_questions_remaining -= 1
      must_callback = True
      question = self._current_question
      while hash(question.GetQuestion()) in self._questions:
        question = self._question_maker.GetRandomQuestion()
      self._current_question = question
      self._questions.add(hash(question.GetQuestion()))
    if must_callback:
      self._msg_fn(self._channel, question.GetQuestionText())

  # TODO: this could possibly be called for a new question if a question was
  # answered right near a timeout expiring
  def _TimeoutQuestion(self):
    must_callback = False
    question = None
    with self._question_lock:
      if self.HasCurrentQuestion():
        must_callback = True
        question = self._current_question
        self._current_question = None
        self._timeout_timer = None

    if must_callback:
      self._msg_fn(self._channel,
                   'Time\'s up! Answer was: %s' % question.GetAnswer())
      timer = threading.Timer(
          FLAGS.trivia_delay_seconds, self._MaybeStartNewQuestion)
      timer.start()

  def CheckAnswer(self, username, answer):
    must_callback = False
    question = None
    if not self.HasCurrentQuestion():
      return

    with self._question_lock:
      if not self.HasCurrentQuestion():
        return
      if self._current_question.CheckAnswer(answer):
        must_callback = True
        question = self._current_question
        self._current_question = None
        if self._timeout_timer:
          self._timeout_timer.cancel()
          self._timeout_timer = None
        self._leaderboard.Correct(username, question.GetPointValue())

    if must_callback:
      self._msg_fn(
          self._channel,
          '%s got it! Answer was: %s' % (username, question.GetAnswer()))
      timer = threading.Timer(
          FLAGS.trivia_delay_seconds, self._MaybeStartNewQuestion)
      timer.start()


class QuestionMaker(object):
  """Question generating class.

  Uses stats library to generate random questions.
  """

  _SKILLS = ['Q', 'W', 'E', 'R']

  def __init__(self, game_lib):
    self._game = game_lib
    self._champ_names = self._game.GetAllChampNames()

    # Question categories and weight of occurrence.
    self._CATEGORIES = [
        (self._PassiveToChampQuestion, 1.0),
        (self._SkillToChampQuestion, 4.0),
        (self._TitleToChampQuestion, 1.0),
        (self._ChampToTitleQuestion, 1.0),
        (self._HypeBotQuestion, 0.05),
        ]

  def GetRandomQuestion(self):
    question = None

    while not question:
      total_weight = sum(weight for _, weight in self._CATEGORIES)
      r = random.uniform(0, total_weight)
      category_idx = 0
      weight_sum = 0.0
      for _, weight in self._CATEGORIES:
        if weight + weight_sum >= r:
          break
        weight_sum += weight
        category_idx += 1

      category = self._CATEGORIES[category_idx][0]
      question = category()
      if not question:
        logging.error('Failed to make a question for category: %s', category)

    return question

  def _RandomChamp(self):
    champ_name = random.sample(self._champ_names, 1)[0]
    champ = self._game.ChampFromName(champ_name)
    return champ

  def _PassiveToChampQuestion(self):
    champ = self._RandomChamp()
    name = champ.name
    passive = util_lib.Dankify(champ.passive.name)
    question_text = '[Passives] Which champion\'s passive is "{}"?'.format(
        passive)
    return Question(question_text, name, canonical_fn=self._game.GetChampId)

  def _SkillToChampQuestion(self):
    champ = self._RandomChamp()
    name = champ.name
    skill_letter = random.sample(self._SKILLS, 1)[0]

    skill = self._game.GetChampSkill(champ, skill_letter)

    question_text = '[Skills] Which champion\'s {} is "{}"?'.format(
        skill_letter, util_lib.Dankify(skill.name))
    return Question(question_text, name, canonical_fn=self._game.GetChampId)

  def _TitleToChampQuestion(self):
    champ = self._RandomChamp()
    name = champ.name
    title = util_lib.Dankify(champ.title)

    question_text = '[Titles] Fill in the champ: ____, {}'.format(title)
    return Question(question_text, name, canonical_fn=self._game.GetChampId)

  def _ChampToTitleQuestion(self):
    champ = self._RandomChamp()
    name = champ.name
    title = champ.title

    # automatically show "the" when title starts with it
    if title.lower().startswith('the '):
      title = title[4:]
      question_text = '[Titles] Fill in the title: {}, the ____'.format(name)
    else:
      question_text = '[Titles] Fill in the title: {}, ____'.format(name)
    return Question(question_text, title)

  def _HypeBotQuestion(self):
    question_text = '[HypeBot] Who is the dankest bot of them all?'
    return Question(question_text, 'hypebot', 5)


class Question(object):
  """A class that contains a question and its answer."""

  def __init__(self, question, answer, point_value=1,
               canonical_fn=util_lib.CanonicalizeName):
    self._question = question
    self._answer = answer
    self._canonical_fn = canonical_fn
    self._canonical_answer = self._canonical_fn(answer)
    self._points = point_value

  def GetQuestion(self):
    return self._question

  def GetQuestionText(self):
    return 'Trivia time! Q: ' + self._question

  def GetAnswer(self):
    return self._answer

  def GetPointValue(self):
    return self._points

  def CheckAnswer(self, answer):
    """Returns True if answer is correct, False otherwise."""
    return self._canonical_answer == self._canonical_fn(answer)


class Leaderboard(object):
  """A leaderboard class so you can taunt others with your knowledge."""

  def __init__(self):
    self.Reset()

  def Reset(self):
    self._user_score_map = {}
    self._active = False

  def BeginGame(self):
    self.Reset()
    self._active = True

  def Correct(self, username, point_value):
    if self._active:
      if username not in self._user_score_map:
        self._user_score_map[username] = 0
      self._user_score_map[username] += point_value

  def AttemptToFinishGame(self, msg_fn, channel):
    if self._active:
      msg_fn(channel, self.Results())
    self._active = False

  def Results(self):
    sorted_users = sorted(self._user_score_map.items(),
                          key=operator.itemgetter(1), reverse=True)
    user_info = []
    for user in sorted_users:
      user_info.append('{} ({})'.format(user[0], user[1]))
    return 'Trivia Leaderboard: [{}]'.format(', '.join(user_info))
