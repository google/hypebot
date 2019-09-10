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

# pylint: disable=anomalous-backslash-in-string
_DANK_MEMES = [
    'One does not simply win weekend tourneys.',
    'I deserve Challenjour, gg',
    ':^)',
    'ヽ༼ຈل͜ຈ༽ﾉ ヽ༼ຈل͜ຈ༽ﾉ ヽ༼ຈل͜ຈ༽ﾉ ヽ༼ຈل͜ຈ༽ﾉ ヽ༼ຈل͜ຈ༽ﾉ ヽ༼ຈل͜ຈ༽ﾉ ヽ༼ຈل͜ຈ༽ﾉ ヽ༼ຈل͜ຈ༽ﾉ',
    '#worthhype',
    'This channel has more #hype than CLG has potential!',
    '#KABUM2015',
    '#PAIN2016',
    'Better nerf Irelia...',
    'I ate oranges, and it was k.',
    '#TSMTSMTSM',
    '[dankness intensifies]',
    'Not HypeBot; HyyyypeBot.',
    'This is where HypeBot shines!',
    'HypeBot does it all... with style!',
    ('HypeBot\'s mission is to organize the world\'s information and make it '
     'universally dank.'),
    '/me is watching EU LCS.',
    'u wot m8',
    'Misspell disappoint in a bug? Son, I am disappoint.',
    'ayyyyyyyyyyyy lmao',
    'rito pls',
    'D is for Dank.',
    'Interior crocodile alligator, I drive a Chevrolet movie theater.',
    'Same.',
    'Le Toucan has arrived.',
    'Quote me on this, EU is garbage',
    'NA > EU',
    'RIP Clairvoyance Ashe',
    '[chiming intensifies]',
    'Yo, {person}, body these fools!',
    '/me remains unconvinced.',
    'Why do NA supports only play Soraka/Janna/Karma?! ¯\_(ツ)_/¯',
    'Hypbot IV: A Nw Mm',
    '{person} is one of the generally "good guy owners" of HypeBot.',
    ('We do not mind at all if there is a massive delta between Hypebot and '
     'other bots...'),
    'Love me some {person}',
    '/me goes full nuts.',
    'MikeYeung HYPE!',
    ('I\'m not allowed to disclose the numbers but trust me, it wasn\'t a '
     'close race.'),
    '👹 You look familiar.',
]
_TEAM_MEMES = [
    '#{team}Hype!',
    'Brace yourself, Team {team} is coming.',
    'I don\'t always host a tournament, but when I do Team {team} wins!',
]
_MEME_TEAMS = [
    'HypeBot',
]
# Ensure that the team memes don't overshadow the dank memes.
_DANK_WEIGHT = (len(_TEAM_MEMES) * len(_MEME_TEAMS)) // len(_DANK_MEMES) + 1
ALL_MEMES = _DANK_MEMES * _DANK_WEIGHT + [
    meme.format(team=team) for team in _MEME_TEAMS for meme in _TEAM_MEMES]
FALLBACK_LIVESTREAM_LINK = 'Check https://www.youtube.com/gaming for the link'
FREELO = [
    ('Did you know there are other ways to win besides stomping your lane '
     'opponent? Try typing "?" in all chat any time someone on the enemy team '
     'dies.'),
    ('Any time your jungler is in another lane, make sure you let him know '
     'your true feelings about it!'),
    ('Communication with your teammates is important! Be sure to inform your '
     'entire team whenever a teammate is feeding their lane opponent, or '
     'failed a flash or whiffed a skillshot!'),
    ('Always buy a control ward when you go back to base! That way you can '
     'sell it later if you are 30g short!'),
    'Miss Fortune\'s first name is Sarah and Vayne\'s is Shauna',
    'If at first you don\'t succeed, try flaming again.',
    ('If Wukong stops moving when being chased, it means he accepts his fate '
     'so you should ult him.'),
    'If nocturne ults, just turn up your brightness. It\'s not a big deal.',
    'It\'s only the jungler\'s fault when you are not the jungler.',
    ('If the opposing laner gets ahead of you, make sure your jungler knows '
     'it\'s his fault so he can correct it in future games!'),
    ('Chasing after Singed is a great way to make your Spectre\'s Cowl as '
     'gold efficient as possible!'),
    ('When playing Mordekaiser, be sure to feed the enemy marksmen early to '
     'increase the strength of your puppet.'),
    ('When playing Blitzcrank, prioritize hooking the enemy Amumu so your team '
     'can burst him down before he can ult.'),
    'Remember to spam AOE abilities under the tower to help your ADC last hit.',
    ('You can catch enemy Draven\'s axes! Make sure to flash forward to steal '
     'his to conserve mana.'),
    ('The more an item costs, the better it is. This makes trinkets the worst '
     'items in the game, don\'t waste time trying to use them.'),
    ('Gnar has great AP ratios! Make sure you go for an early deathcap '
     'to make his GNAR! and Hyper do some serious damage.'),
    ('If you have trouble keeping up with your opponent\'s leveling, try buying'
     ' an EXP boost!'),
    ('Don\'t worry about building magic resist against Ryze because he does '
     'mana damage.'),
    ('When playing Cho\'Gath, try not to get too many stacks, as it makes it '
     'easier for the enemy to hit you.'),
    ('Your enemy will know you\'re the jungler if you take smite. Take ignite '
     'or teleport instead to play mind games.'),
    ('When teamfighting, always focus the enemy marksmen or mages. You should '
     'never focus the enemy tank.'),
    'Laugh is the most powerful skill in the game.',
    ('After acing the enemy team at their base, you should go back and take '
     'their jungle instead of the inhibitor. Inhibitors only give 50g which is '
     'less efficient.'),
    'When playing Bard, be sure to ult your wards to extend their timers.',
    ('Runaan\'s Hurricane lets Vayne deal true damage to three champions at '
     'once.'),
    ('If you\'re falling behind in farm, let the enemy kill your inhibitor. '
     'Super minions grant you more gold and deny your lane opponent cs.'),
    ('Use Ghost/Flash to get back to lane when playing against Zoe, ensuring '
     'they cannot be used against you.'),
]
HYPEBOT_IS_THE_CHAMP_STRING = ('HypeBot is a L7-9 Vision main, generating ∞ '
                               'chests this season.')
HYPEBOT_IS_THE_CHIMP_STRING = 'HypeBot doesn\'t monkey around.'
HYPEBOT_ALL_CHAMPS_STRING = 'HypeBot knows champs, HypeBot has the best champs.'
POEM = [
    'There was once a hype bot with dank memes who was very lonely.',
    'why was it lonely?',
    'All things must !raise this bot, so they shunned it.',
    'did it chase them all?',
    'It took an axe and rekt itself in two, right down the middle.',
    'hypebot, wtf',
    'So it would always have a #Hype.',
]
ROOSTERS = [
    'cock-a-doodle-doo',
    'koekelekoe',
    'kikiriki',
    'gokogoko',
    'cocorico',
    'cuc-a-dudal-du',
    'quiquiriquí',
    'קוקוריקו',
    'chichirichí',
    'Foghorn Leghorn',
    'Albert Eggstein',
    'gallo',
    'coq',
    'Hahn Solo',
    '公鸡',
    '雄鶏',
]
SCHEDULE_NO_GAMES_STRING = ('Tune in next season to see if NA makes it out of '
                            'groups.')
WHO_IS_HYPEBOT_STRING = ('HypeBot = ¯\_(ツ)_/¯ [DECAKILL, Challenjour (KR), '
                         'Ranked LCK 1v9: Teemo, 1337pts (W)]')
