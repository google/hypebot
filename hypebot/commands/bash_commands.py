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
"""Bash command FTW."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import re

from absl import logging

from hypebot import hypecore
from hypebot.commands import command_lib
from hypebot.data import messages
from hypebot.plugins import alias_lib
from hypebot.protos.channel_pb2 import Channel
from hypebot.protos.user_pb2 import User


_RESERVED_ALIAS_KEYWORDS = ['list', 'remove', 'copy', 'clone']


@command_lib.CommandRegexParser(r'alias (add )?([^ ]+) (.+)')
class AliasAddCommand(command_lib.BaseCommand):
  """Adds or updates a user's alias."""

  @command_lib.MainChannelOnly
  def _Handle(self,
              channel: Channel,
              user: str,
              add_prefix: str,
              alias_name: str,
              alias_cmd: str) -> hypecore.MessageType:
    alias_name = alias_name.lower()
    if alias_name == '!alias':
      return 'I don\'t think that would be a good idea.'
    if not add_prefix:
      # Process 'alias add list' but not 'alias list'.
      if alias_name in _RESERVED_ALIAS_KEYWORDS:
        return
    had_command = alias_lib.AddOrUpdateAlias(
        self._core.cached_store, user, alias_name, alias_cmd)
    return '%s alias %s.' % ('Updated' if had_command else 'Added', alias_name)


@command_lib.CommandRegexParser(
    r'alias (?:copy|clone) (?P<target_user>.+?) (.+)')
class AliasCloneCommand(command_lib.BaseCommand):
  """Steal an alias from someone else."""

  @command_lib.MainChannelOnly
  def _Handle(self,
              channel: Channel,
              user: str,
              alias_name: str,
              target_user: User) -> hypecore.MessageType:
    alias_name = alias_name.lower()
    aliases = alias_lib.GetAliases(self._core.cached_store, target_user.id)

    if alias_name in aliases:
      alias_lib.AddOrUpdateAlias(self._core.cached_store, user, alias_name,
                                 aliases[alias_name])
      return 'Cloned %s from %s.' % (alias_name, target_user.name)
    else:
      return 'Alias %s not found' % alias_name


@command_lib.CommandRegexParser(r'alias remove (.+)')
class AliasRemoveCommand(command_lib.BaseCommand):
  """Removes an alias from a user's set."""

  @command_lib.MainChannelOnly
  def _Handle(self,
              channel: Channel,
              user: str,
              alias_name: str) -> hypecore.MessageType:
    had_command = alias_lib.RemoveAlias(self._core.cached_store, user,
                                        alias_name)
    if had_command:
      return 'Removed alias %s.' % alias_name
    else:
      return 'No command %s found.' % alias_name


@command_lib.CommandRegexParser(r'alias list ?(?P<target_user>.*)')
class AliasListCommand(command_lib.BaseCommand):
  """Lists all aliases saved for a user."""

  @command_lib.MainChannelOnly
  @command_lib.LimitPublicLines()
  def _Handle(self,
              channel: Channel,
              user: str,
              target_user: User) -> hypecore.MessageType:
    aliases = alias_lib.GetAliases(self._core.cached_store, target_user.id)
    logging.info('Aliases for user %s: %s', target_user.name, str(aliases))
    if not aliases:
      return messages.ALIASES_NO_ALIASES % target_user.name
    header = ['%s aliases:' % target_user.name]
    return header + ['[%s] -> %s' % (k, v) for k, v in aliases.items()]


@command_lib.CommandRegexParser(r'echo ([\s\S]+?)')
class EchoCommand(command_lib.BaseCommand):
  """Display a string to standard output."""

  @command_lib.MainChannelOnly
  @command_lib.LimitPublicLines()
  def _Handle(self,
              channel: Channel,
              user: str,
              string: str) -> hypecore.MessageType:
    lines = string.split('\n')
    return lines


@command_lib.CommandRegexParser(r'grep (?:"(.+?)"|([\S]+)) ([\s\S]+?)')
class GrepCommand(command_lib.BaseCommand):
  """Print lines matching a pattern."""

  @command_lib.MainChannelOnly
  @command_lib.LimitPublicLines()
  def _Handle(self,
              channel: Channel,
              user: str,
              multi_word: str,
              single_word: str,
              message: str) -> hypecore.MessageType:
    needle = re.compile(multi_word or single_word, re.IGNORECASE)
    haystack = message.split('\n')
    replies = []
    for stalk in haystack:
      if needle.search(stalk):
        replies.append(stalk)
    return replies


@command_lib.CommandRegexParser(r's '
                                # The pattern to match (replace)
                                r'/?(?:"(.+?)"|([\S]+))'
                                # The pattern to replace it with
                                r'/(?:"(.*?)"|([\S]*))'
                                # (optional) Parser-level options
                                r'(?:/(.*?))?'
                                # The message itself
                                r' ([\s\S]+?)')
class SubCommand(command_lib.BaseCommand):
  """Substitute lines according to a pattern."""

  @command_lib.MainChannelOnly
  @command_lib.LimitPublicLines()
  def _Handle(self,
              channel: Channel,
              user: str,
              multi_word_search: str,
              single_word_search: str,
              multi_word_replace: str,
              single_word_replace: str,
              options: str,
              message: str) -> hypecore.MessageType:
    search_str = multi_word_search or single_word_search
    replace_str = multi_word_replace or single_word_replace or ''
    haystack = message.split('\n')
    replies = []
    flags = 0
    if options and 'i' in options.lower():
      flags = re.IGNORECASE
    for stalk in haystack:
      replies.append(re.sub(search_str, replace_str, stalk, flags=flags))
    return replies


@command_lib.CommandRegexParser(
    r'wc ((?:-[lwc] |--(?:lines|words|chars) )+)?([\s\S]*)')
class WordCountCommand(command_lib.BaseCommand):

  def __init__(self, *args):
    super(WordCountCommand, self).__init__(*args)
    # TODO(someone): Create a command_lib.ArgumentParser.
    self._parser = argparse.ArgumentParser()
    self._parser.add_argument('-l', '--lines', action='store_true')
    self._parser.add_argument('-w', '--words', action='store_true')
    self._parser.add_argument('-c', '--chars', action='store_true')

  @command_lib.MainChannelOnly
  def _Handle(self,
              channel: Channel,
              unused_user: str,
              options: str,
              message: str) -> hypecore.MessageType:
    if options:
      try:
        options = self._parser.parse_args(options.strip().split())
      except Exception:  # pylint: disable=broad-except
        return 'Unrecognized arguments.'
    else:
      options = argparse.Namespace(lines=True, words=True, chars=True)

    responses = []
    if options.lines:
      if not message:
        responses.append('0')
      else:
        responses.append(str(len(message.split('\n'))))
    if options.words:
      responses.append(str(len(message.split())))
    if options.chars:
      responses.append(str(len(message)))
    return ' '.join(responses)

