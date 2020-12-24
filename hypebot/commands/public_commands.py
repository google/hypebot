# Lint as: python3
# coding=utf-8
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
"""Commands that handle every public message."""

# In general, we want to catch all exceptions, so ignore lint errors for e.g.
# catching Exception
# pylint: disable=broad-except

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import collections
import random
import re
from threading import RLock
import time
from typing import Text

from absl import logging
import arrow
from hypebot import hype_types
from hypebot.commands import command_lib
from hypebot.core import params_lib
from hypebot.core import util_lib
from hypebot.data import messages
from hypebot.plugins import coin_lib
from hypebot.plugins import inventory_lib
from hypebot.protos import channel_pb2
from hypebot.protos import user_pb2


@command_lib.PublicParser
class AutoReplySnarkCommand(command_lib.BasePublicCommand):
  """Auto-reply to auto-replies."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BasePublicCommand.DEFAULT_PARAMS,
      {
          'probability': 0.25,
          # How often to apply extra snark. Note this is only checked when an
          # auto-reply is emitted. Thus the chance that an extra-snarky reply is
          # returned is (probability * extra_snark_probability).
          'extra_snark_probability': 0.5,
      })

  _AUTO_REPLIES = (
      'Much appreciated',
      'Works fine',
      'Good point',
      'Agreed',
      'Ouch',
      'Neat!',
      'Congrats!',
      'Do it',
      'Me too',
      'Noted!',
      'lol',
      'Wow, thanks',
      '💩',
      '💪',
      '😬',
      '🔥',
      'Cool story, bro',
  )

  _SNARK_TEMPLATES = (
      '{}...',
      '{} /s',
      '{} 🙄',
      '{} 🤔',
  )

  def __init__(self, *args):
    super(AutoReplySnarkCommand, self).__init__(*args)
    self._regex = re.compile(r' \((auto|auto-reply|ar)\)$')

  def _Handle(self, channel: channel_pb2.Channel, user: user_pb2.User,
              message: Text) -> hype_types.CommandResponse:
    match = self._regex.search(message)
    if match and random.random() < self._params.probability:
      reply = random.choice(self._AUTO_REPLIES)
      if random.random() < self._params.extra_snark_probability:
        reply = random.choice(self._SNARK_TEMPLATES).format(reply)
      return '%s (%s)' % (reply, match.groups()[0])


_SongLine = collections.namedtuple('SongLine', 'state lyric pattern')


@command_lib.PublicParser
class CookieJarCommand(command_lib.BasePublicCommand):
  """Let's sing a children's song."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BasePublicCommand.DEFAULT_PARAMS,
      {
          # Amount of time to wait before resetting song.
          'timeout_sec': 60,
      })

  _SONG = [
      _SongLine('accusation', None,
                r'(?i)(\S+) stole the (\S+)s from the \2 jar\??$'),
      _SongLine('disbelief', 'Who, me?', r'(?i)who,? me'),
      _SongLine('confirmation', 'Yes, you!', r'(?i)yes,? you'),
      _SongLine('denial', 'Couldn\'t be!',
                r"(?i)(couldn't be|not me|wasn't me)"),
      _SongLine('question', 'Then who?', r'(?i)then,? who'),
  ]

  def __init__(self, *args):
    super(CookieJarCommand, self).__init__(*args)
    self._lock = RLock()
    self._ResetSong()

  def _ResetSong(self):
    with self._lock:
      self._cookie = None
      self._line_num = 0
      self._accusor = None
      self._accused = None

  def _AccusorsTurn(self):
    with self._lock:
      return self._line_num % 2 == 0

  def _AccusedTurn(self):
    return not self._AccusorsTurn()

  def _BotIsAccusor(self):
    with self._lock:
      return self._accusor.user_id == self._core.name

  def _BotIsAccused(self):
    with self._lock:
      return self._accused.user_id == self._core.name

  def _NextLine(self, channel):
    with self._lock:
      self._last_time = time.time()
      self._line_num = (self._line_num + 1) % len(self._SONG)
      line = self._SONG[self._line_num]

      if line.state == 'accusation':
        self._accusor = self._accused

      if ((self._AccusorsTurn() and self._BotIsAccusor()) or
          (self._AccusedTurn() and self._BotIsAccused())):
        # Bot needs to take action.
        if line.state == 'accusation':
          self._accused = random.choice(self._core.user_tracker.AllHumans())
          self._Reply(
              channel, '%s stole the %ss from the %s jar' %
              (self._accused.display_name, self._cookie, self._cookie))
        else:
          self._Reply(channel, line.lyric)
        self._NextLine(channel)

  def _Handle(self, channel: channel_pb2.Channel, user: user_pb2.User,
              message: Text) -> hype_types.CommandResponse:
    with self._lock:
      if (self._cookie and
          time.time() - self._last_time > self._params.timeout_sec):
        self._ResetSong()

      line = self._SONG[self._line_num]
      match = re.match(line.pattern, message)
      if match:
        if line.state == 'accusation':
          if not self._accusor:
            # No accusor means no current song.
            if match.groups()[0].lower() != 'who':
              return
            self._cookie = match.groups()[1]
            self._accusor = user
            self._accused = user_pb2.User(
                user_id=self._core.name, display_name=self._core.name)
          elif user == self._accusor and match.groups()[1] == self._cookie:
            self._accused = self._core.interface.FindUser(match.groups()[0])

        if ((self._AccusorsTurn() and user == self._accusor) or
            (self._AccusedTurn() and user == self._accused)):
          self._NextLine(channel)


@command_lib.PublicParser
class EggHuntCommand(command_lib.BasePublicCommand):
  """Gotta find them all."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BasePublicCommand.DEFAULT_PARAMS, {
          'find_chance': 0.05,
      })

  def _Handle(self, channel: channel_pb2.Channel, user: user_pb2.User,
              message: Text) -> hype_types.CommandResponse:
    if random.random() < self._params.find_chance:
      item = inventory_lib.Create('HypeEgg', self._core, user, {})
      self._core.inventory.AddItem(user, item)
      return '%s found a(n) %s' % (user, item.human_name)


@command_lib.PublicParser
class GreetingsCommand(command_lib.BasePublicCommand):
  """Greet users who acknowledge hypebot's presence."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BasePublicCommand.DEFAULT_PARAMS,
      {
          'ratelimit': {
              'enabled': True,
              'return_only': True
          },
          # Channels where we greet users who don't explictly greet hypebot.
          # Still grants paychecks in all other channels.
          'greet_channels': []
      })

  def _Handle(self, channel: channel_pb2.Channel, user: user_pb2.User,
              message: Text) -> hype_types.CommandResponse:
    got_paid = False
    # We only deliver paychecks if:
    #  * We're running in prod (to avoid dev bots spamming people)
    #  * We have a cached_store to read from
    #  * The request comes from a main channel
    #  * The user is not a bot
    if all((not self._core.params.execution_mode.dev, self._core.cached_store,
            not user.bot)):
      got_paid = self._DeliverPaycheck(user)

    # TODO: This and below don't really belong here.
    if re.search(
        r'(?i)Good ?night,? (sweet )?(%s|#?%s)' %
        (self._core.name, channel.name), message):
      return f'And flights of angels sing thee to thy rest, {user.display_name}'

    if re.search(r'(?i)oh,? %s(\..*)?\s*$' % self._core.name, message):
      return messages.OH_STRING

    # Keeping the optional # in the regex supports IRC channels.
    match = re.search(
        r'(?i)(morning|afternoon|evening),? (%s|#?%s)' %
        (self._core.name, channel.name), message)
    if match:
      return self._BuildGreeting(user, match.group(1))

    # If we didn't give user a paycheck, they can't get a greeting for just
    # talking. They must explictly greet hypebot.
    if got_paid and util_lib.MatchesAny(self._params.greet_channels, channel):
      return self._BuildGreeting(user)

  def _DeliverPaycheck(self, user: user_pb2.User):
    """Potentially give user a paycheck, returns if user got paid."""
    now = arrow.utcnow()
    last_activity = self._core.user_tracker.LastActivity(user)

    if last_activity < now.shift(hours=-6):
      if not self._core.bank.ProcessPayment(coin_lib.MINT_ACCOUNT, user, 100,
                                            'Paycheck', self._Reply):
        self._Reply(user, messages.HYPECOIN_MINT_EXHAUSTION_STR)
      return True

  def _BuildGreeting(self, user, time_of_day=None):
    """Builds a reply to user when they need to be greeted."""
    hour = arrow.now(self._core.timezone).hour

    if 3 <= hour < 12:
      true_time_of_day = 'Morning'
    elif 12 <= hour < 18:
      true_time_of_day = 'Afternoon'
    else:
      true_time_of_day = 'Evening'

    if not time_of_day:
      time_of_day = true_time_of_day
    time_of_day = time_of_day.title()

    # We build ranges of hours that correspond to the time of day given (e.g.
    # morning), and the 3 hours surrounding that range. We then compare that to
    # what time the user said it was, and adjust our level of snark
    # commensurately.
    time_ranges = (range(3, 12), list(range(0, 3)) + list(range(12, 15)))
    if time_of_day == 'Afternoon':
      time_ranges = (range(12, 18), list(range(9, 12)) + list(range(18, 21)))
    elif time_of_day == 'Evening':
      time_ranges = (list(range(0, 3)) + list(range(18, 24)),
                     list(range(15, 18)) + list(range(3, 6)))

    greeting_params = {'user': user.display_name, 'time_of_day': time_of_day}
    custom_greeting = self._core.store.GetValue(user.user_id, 'greetings')
    if hour in time_ranges[0]:
      greeting = custom_greeting or '{time_of_day}, {user}'
    elif hour in time_ranges[1]:
      greeting = '"{time_of_day}", {user}'
    else:
      greeting = 'Not even close {user}'

    if '{bal}' in greeting:
      greeting_params['bal'] = util_lib.FormatHypecoins(
          self._core.bank.GetBalance(user))
    try:
      return greeting.format(**greeting_params)
    except Exception as e:
      logging.info('GreetingCommand exception: %s', e)
      self._core.bank.FineUser(user, 100, 'Bad greeting', self._Reply)
      return ('%s has an invalid greeting and feels bad for trying to '
              'break %s' % (user, self._core.name))


@command_lib.PublicParser
@command_lib.CommandRegexParser(r'(hype)')
# BaseCommand because 1) This isn't only a PublicParser command and 2) it does
# have a ratelimiter
class HypeCommand(command_lib.BaseCommand):
  """Get HYPED (where applicable)!"""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BaseCommand.DEFAULT_PARAMS,
      {
          # Number of unique hypers needed to get doged.
          'doge_num_hypers': 3,
          # Time needed to get doged.
          'doge_time_seconds': 10,
          # Interval between doge spams.
          'doge_rate_seconds': 3600,
          'ratelimit': {
              'interval': 0.5,
              'return_only': True,
          },
      })

  def __init__(self, *args):
    super(HypeCommand, self).__init__(*args)

    self._last_doge = {}
    self._dogers = {}
    # Record of users who have replied to hypes keyed by channel, then user.
    self._hype_chains = collections.defaultdict(
        lambda: collections.defaultdict(dict))

  # Prevents bots from recursive hyping.
  @command_lib.HumansOnly()
  def _Handle(self, channel: channel_pb2.Channel, user: user_pb2.User,
              message: Text) -> hype_types.CommandResponse:
    if message == 'hype':
      # Fake the hype so it can still trigger easter eggs.
      message = '#%sHype' % self._core.name

    hypes = []
    responses = []
    t = time.time()
    for token in message.split():
      if re.match(r'(?i)(#.*antihy+pe+)\W*$', token):
        self._Spook(user)  # This avoid ratelimit, but it's private.
        return '%s, take that non-hype attitude elsewhere.' % user.display_name
      match = re.match(r'(?i)(#.*hy+pe+)\W*$', token)
      if match:
        hypes.append(match.group(1))
        self._UpdateHypeChains(channel, user, t)
        self._dogers = {
            user_id: hype_time
            for (user_id, hype_time) in self._dogers.items()
            if t - hype_time <= self._params.doge_time_seconds
        }
        self._dogers[user.user_id] = t
        logging.info('Dogers: %s', self._dogers)
        if random.randint(0, 100) == 42:
          responses.append(messages.PROSE_HYPE % self._core.name)
        if len(self._dogers) >= self._params.doge_num_hypers:
          if (t - self._last_doge.get(channel.id, 0) >=
              self._params.doge_rate_seconds):
            self._last_doge[channel.id] = t
            logging.info('\n'.join(messages.DOGE))
            # This uses its own ratelimit, so avoid the return_only ratelimit.
            self._Reply(channel, messages.DOGE)
    if hypes:
      responses.insert(0, ' '.join(hypes))
    return responses

  def _UpdateHypeChains(self, channel, user, hype_time):
    """Records humans who have hyped recently and awards HypeStacks."""
    logging.info('HypeChain: Adding/Updating hypechain for %s/%s', channel.id,
                 user)
    user_hype_record = self._hype_chains[channel.id][user.user_id]
    user_hype_record['time'] = hype_time
    if 'users' not in user_hype_record:
      user_hype_record['users'] = set()

    to_be_removed = set()
    for hype_user_id, hype_info in self._hype_chains[channel.id].items():
      if hype_time - hype_info['time'] > 60:
        logging.info('HypeChain: Removing hypechain for %s/%s', channel.id,
                     hype_user_id)
        to_be_removed.add(hype_user_id)
      elif (hype_user_id != user.user_id and
            user.user_id not in user_hype_record['users']):
        logging.info('HypeChain: Awarding a stack to %s for %s\'s hype in %s',
                     hype_user_id, user, channel.name)
        user_hype_record['users'].add(user.user_id)
        self._core.hypestacks.AwardStack(
            self._core.interface.FindUser(hype_user_id))
    for user_id in to_be_removed:
      del self._hype_chains[channel.id][user_id]


@command_lib.PublicParser
class MissingPingCommand(command_lib.BasePublicCommand):
  """Flame teammates."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BasePublicCommand.DEFAULT_PARAMS, {
          'ratelimit': {
              'enabled': True,
              'interval': 2,
              'return_only': True
          },
      })

  def __init__(self, *args):
    super(MissingPingCommand, self).__init__(*args)
    self._target = collections.defaultdict(str)
    self._regex = re.compile(r'^\?+(.*)')

  def _Handle(self, channel: channel_pb2.Channel, user: user_pb2.User,
              message: Text) -> hype_types.CommandResponse:
    ping_match = self._regex.match(message)
    if ping_match:
      ping_target = ping_match.groups()[0].strip()
      missing_str = 'enemies are'
      if ping_target:
        if util_lib.CanonicalizeName(ping_target) == self._core.name.lower():
          ping_target = user.display_name
        missing_str = '%s is' % ping_target
        self._target[channel.id] = ping_target
      elif self._target[channel.id]:
        missing_str = '%s is' % self._target[channel.id]
      return '%s signals that %s missing' % (self._core.params.name,
                                             missing_str)
    elif not user.bot:
      self._target[channel.id] = user.display_name


_SayPhrase = collections.namedtuple('_SayPhrase', 'phrase repetitions')


@command_lib.PublicParser
class SayCommand(command_lib.BasePublicCommand):
  """Teach hypebot how to respond to certain phrases."""

  DEFAULT_PARAMS = params_lib.MergeParams(
      command_lib.BasePublicCommand.DEFAULT_PARAMS,
      {
          # Number of times to repeat phrase.
          'repetitions': 5,
      })

  # Key for anyone instead of a specific user. Use all caps to not collide with
  # normalized usernames.
  _ANY_SPEAKER = 'ANY_SPEAKER'

  def __init__(self, *args):
    super(SayCommand, self).__init__(*args)

    # Compile regex for efficiency.
    self._regex = re.compile(r'(?i)when (\S+) says? (.+) you say (.+)$')
    # Store phrases to repeat keyed on channel, user, and then message.
    self._phrases = collections.defaultdict(
        lambda: collections.defaultdict(dict))

  def _Handle(self, channel: channel_pb2.Channel, user: user_pb2.User,
              message: Text) -> hype_types.CommandResponse:
    match = self._regex.search(message)
    if match:
      speaker = match.groups()[0].lower()
      if speaker == 'i':
        speaker = user.user_id
      if speaker in ['we', 'anyone', 'someone']:
        speaker = self._ANY_SPEAKER
      speaker_phrase = match.groups()[1]
      hypebot_phrase = match.groups()[2]
      self._phrases[channel.id][speaker][speaker_phrase] = _SayPhrase(
          hypebot_phrase, self._params.repetitions)

    responses = []
    for speaker in [user.user_id, self._ANY_SPEAKER]:
      say = self._phrases[channel.id][speaker].get(message)
      if say and say.repetitions > 0:
        responses.append(say.phrase)
        say = _SayPhrase(say.phrase, say.repetitions - 1)
        if say.repetitions <= 0:
          responses.append('It\'s an old meme, sir, but it checks out.')
          del self._phrases[channel.id][speaker][message]
        else:
          self._phrases[channel.id][speaker][message] = say
        # Short circuit so we only get one response.
      return responses
