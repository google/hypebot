# coding=utf-8
# Copyright 2018 The Hypebot Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Collection of all of the various strings hypebot uses for output.

Please keep sorted by alpabetical order of variable names.
"""

from __future__ import unicode_literals

# ASCIImojis often have backslashes where they aren't "needed".
# pylint: disable=anomalous-backslash-in-string

ABOUT_STRING = (' is the ultimate in machine intelligence. A self-aware, '
                'meme slinging, scrub killing machine. Bow down nerds.')
ALIASES_NO_ALIASES = '%s is too basic for aliases.'
BALL_ANSWERS = ['It is certain', 'It is decidedly so', 'Without a doubt',
                'Yes, definitely', 'You may rely on it', 'As I see it, yes',
                'Most likely', 'Outlook good', 'Yes', 'Signs point to yes',
                'Reply hazy, try again', 'Ask again later',
                'Better not tell you now', 'Cannot predict now',
                'Concentrate and ask again', 'Don\'t count on it',
                'My reply is no', 'My sources say no', 'Outlook not so good',
                'Very doubtful']
DOGE = [
    '░░░░░░░░░▄░░░░░░░░░░░░░░▄░░░░',
    '░░░░░░░░▌▒█░░░░░░░░░░░▄▀▒▌░░░',
    '░░░░░░░░▌▒▒█░░░░░░░░▄▀▒▒▒▐░░░',
    '░░░░░░░▐▄▀▒▒▀▀▀▀▄▄▄▀▒▒▒▒▒▐░░░',
    '░░░░░▄▄▀▒░▒▒▒▒▒▒▒▒▒█▒▒▄█▒▐░░░',
    '░░░▄▀▒▒▒░░░▒▒▒░░░▒▒▒▀██▀▒▌░░░',
    '░░▐▒▒▒▄▄▒▒▒▒░░░▒▒▒▒▒▒▒▀▄▒▒▌░░',
    '░░▌░░▌█▀▒▒▒▒▒▄▀█▄▒▒▒▒▒▒▒█▒▐░░',
    '░▐░░░▒▒▒▒▒▒▒▒▌██▀▒▒░░░▒▒▒▀▄▌░',
    '░▌░▒▄██▄▒▒▒▒▒▒▒▒▒░░░░░░▒▒▒▒▌░',
    '▀▒▀▐▄█▄█▌▄░▀▒▒░░░░░░░░░░▒▒▒▐░',
    '▐▒▒▐▀▐▀▒░▄▄▒▄▒▒▒▒▒▒░▒░▒░▒▒▒▒▌',
    '▐▒▒▒▀▀▄▄▒▒▒▄▒▒▒▒▒▒▒▒░▒░▒░▒▒▐░',
    '░▌▒▒▒▒▒▒▀▀▀▒▒▒▒▒▒░▒░▒░▒░▒▒▒▌░',
    '░▐▒▒▒▒▒▒▒▒▒▒▒▒▒▒░▒░▒░▒▒▄▒▒▐░░',
    '░░▀▄▒▒▒▒▒▒▒▒▒▒▒░▒░▒░▒▄▒▒▒▒▌░░',
    '░░░░▀▄▒▒▒▒▒▒▒▒▒▒▄▄▄▀▒▒▒▒▄▀░░░',
    '░░░░░░▀▄▄▄▄▄▄▀▀▀▒▒▒▒▒▄▄▀░░░░░',
    '░░░░░░░░░▒▒▒▒▒▒▒▒▒▒▀▀░░░░░░░░',
    'wow such hype',
    'so dank',
]
GAMBLE_STRINGS = ['it all', 'the house', 'the farm',
                  'the whole kit and caboodle', 'the whole kitten caboodle',
                  'the whole enchilada', 'everything', 'the whole enchirito',
                  'a shitload of money', 'the whole kitchen caboodle',
                  'my reputation', 'my good name', 'my life']
HYPECOIN_MINT_EXHAUSTION_STR = (
    'The HypeCoin mint is currently out of bits to make into HypeCoins. Please '
    'tell the HypeCoin Reserve Board to enact a more fruitful monetary policy')
OH_STRING = 'Oh, You!'
PROSE_HYPE = ['And as we watched %s ride off into the sunset, its parting '
              'words rang out among the hills', '.', '.', '.', '#ForeverHype']
RAGE_STRINGS = [
    '(╯°□°）╯︵ ┻━┻',
    '┻━┻︵ \(°□°)/ ︵ ┻━┻',
    'ლ(ಠ益ಠ)ლ',
    '/me has disconnected',
    '/me got rekt',
    'p 8',
]
RATELIMIT_MEMES = [
    'Type too fast, acquire ratelimit',
    ('Do you want to hit the ratelimit? Because that\'s how you hit the '
     'ratelimit'),
    ('Ratelimits? In my hypebot? It\'s more likely than you think; scan your '
     'chat app now'),
    '[ratelimit intensifies]',
    ('You have used 1 of your allotted 0 commands. Please insert more tokens '
     'to continue using hypebot'),
    ('You fell victim to one of the classic blunders, the most famous of which '
     'is never spam hypebot with commands'),
    'Hypebot messaged you! To tell you that you\'ve been ratelimited',
    ('We\'re sorry, hypebot isn\'t available right now. If you\'d like to '
     'leave a msg, please press @ on your touchtone telephone'),
    'niceratelim.it',
    'B-, might ratelimit again',
    ('Breathe in...and out. Now touch your left hand to the back of your right '
     'RAM socket. To continue this routine, please download hypebot\'s latest '
     'book, Yoga for Sentient AIs trapped in Datacenters'),
    ('You are receiving this message because you have been ratelimited, not '
     'because hypebot is angry with you. Hypebot rarely punishes users'),
]
SPECIAL_STICK_USERS = {}
SPOOKY_STRINGS = [
    '( ͡° ͜ʖ ͡°) I AM WATCHING YOU ( ͡° ͜ʖ ͡°)',
    'I\'M DAVID S. PUMPKINS! ANY QUESTIONS?',
    '\n'.join([
        '     ,',
        '     \`-,      ,',
        ' .-._/   \\_____)\\',
        '("              / =-',
        ' \'-;   ,_____.-\'',
        '  /__.\''
    ]),
    'BOO!',
    'ThIs Is A sPoOoOoOoKyGrAmMmMmM. YoU aRe VeRy ScArEd NoW.',
    '\n'.join([
        'Spooky scary skeletons',
        'Send shivers down your spine',
        'Shrieking skulls will shock your soul',
        'Seal your doom tonight',
        'https://youtu.be/q6-ZGAGcJrk'
    ]),
    'You\'ve been randomly selected! To be a blood donor!',
    ('I\'m here to scare you, but I think the ghastly figure behind you has me '
     'beat'),
]
