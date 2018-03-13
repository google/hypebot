# HypeBot Help

HypeBot is always here to help.

## Supported Commands (All Bots)

### "Fun" Commands

*   !
    *   The one command to rule them all.
*   !8ball [question]
    *   Bot will read the lines of fate and answer your yes/no question.
*   !disappoint [son|me]
    *   Bot responds with "[son], I am disappoint."
    *   "me" will use your own username.
*   !energy [target]
    *   Infuse [target] with energy.
*   !help
    *   no u
*   !rage
    *   Hypebot expresses anger over the current administration.
*   !raise [donger]
    *   Hypebot will help you raise things (by responding with dongers.)
*   !riot [rito]
    *   Hypebot will start rioting about a given topic.
*   !rip [scrub]
    *   Hypebot will mourn the dead.
*   ![2|same]
    *   Repeats the last command issued with "me" as an argument.
*   !stock [symbol,...]
    *   Fetches the latest quote for each symbol, defaulting to GOOG and GOOGL.
*   !version
    *   Prints version of running bot.
*   !weather [location]
    *   Fetches weather predictions for the supplied location.

### Personalized Commands

*   !alias [subcommand]
    *   add [alias] [message]
        *   Adds the supplied alias to your list of aliases. When a user types
            the alias, HypeBot will interpret it as if they had typed the text
            supplied as the message. For example, typing `!alias !blizzard
            !riot` followed by `!blizzard` will execute the command `!riot`.
        *   Alias also supports passing arguments to the alias with the use of
            placeholders:
            *   Limited group capture. Typing `!alias !gift !rob \1 1` followed
                by `!gift brcooley` will execute the command `!rob brcooley 1`.
                If the placeholder doesn't match an argument, it will be
                removed.
            *   `\me` is replaced with the username of whoever invoked the
                command. (e.g. `\me is the best \mentor` -> `vilhelm is the best
                \mentor`).
            *   Pass all or some arguments with `\@` or a slice of arguments
                with `\@start:end`. The slice notation behaves like python
                slices.
    *   remove [alias]
        *   Removes the supplied alias from your list of aliases.
    *   list [user|me]
        *   Lists all aliases and their associated messages for the given user.
    *   clone [user] [alias]
        *   Copies an alias of the given user into your own alias list.
*   !greet [0-4|list]
    *   Increase your street cred with hypebot.

### HypeCoin Commands

*   !bet [amount] [more]? [for|against|on] [target]
    *   Place, or add to, a bet for given target (Stock: symbol or
        lotto/jackpot).
*   !gift [user] [amount]
    *   Transfer [amount] hypecoins from your account to [user]'s account.
*   !rob [user] [amount]
    *   Attempts to steal [amount] hypecoins from [user]. Chance of success
        diminishes with the percent of user's hypecoins you are trying to steal,
        how much the user has been stolen from recently, and how much you have
        been a thief recently.
*   !hc [subcommand]
    *   balance [user|me]
        *   Display user's hypecoin balance.
    *   bet [args]
        *   Softlink for !bet [args]
    *   [my]bets [user|game]+
        *   Display up to 5 current bets from any of [user|game].
    *   circulation
        *   Display stats about hypecoins in circulation.
    *   forbes
        *   Display Forbes 4, the wealthiest in hypebotland.
    *   gift [args]
        *   Softlink for !gift [args]
    *   rob [args]
        *   Softlink for !rob [args]
    *   reset
        *   Reset your balance to 100 hypecoins.
    *   tx [user|me]
        *   Displays user's last 5 hypecoin transactions.
*   !jackpot
    *   List all current lotto bets

### Development Commands

*   !reload
    *   Reloads all data.

## League Commands (HypeBot)

*   !bet [amount] [for|against|on] [team_a] over [team_b]
    *   Bet on professional (and EU) LoL matches.
*   !body [name]
    *   Hypebot will ask [name] to body some fools.
*   !champs[all][-region] [name|me]
    *   Looks up specified username/summoner name (from go/lolsummoners) to find
        champion mastery data, printing out the top three champions this
        summoner plays. "me" will use your own username, !champsall will fetch
        smurf accounts in addition to a user's main account. Takes an optional
        region following a hyphen after !champs or !champsall (e.g. !champs-euw
        [name]).
*   !champ[all][-region] [name|me] [champ-in-brackets]
*   !champ[all][-region] [name|me]:[champ]
    *   Like !champs but for a specific champion only. champ-in-brackets is a
        champion name enclosed in square brackets, e.g. "[lux]". Example
        command: "!champ me [lux]" Alternative syntax example: "!champ me:lux"
*   !chimps[all][-region] [name|me]
    *   Find about the specified user's chimp mastery. (See !champs.)
*   !item [item]
    *   Prints out the item's stats and description.
*   !lcs-ch(a|u)mps [lcs_player]
    *   Prints out summary data about lcs_player's performance in the current
        split.
*   !lcs-pb[-region] [specifier] [order]
    *   Displays champion pick/ban stats from the LCS, optionally filtered by
        region. order can be '^' or 'v' (defaulting to 'v'). specifier can be
        any of the following:
        *   'all' will show champions ordered by pick + ban rate.
        *   'bans' will show champions ordered by ban rate.
        *   'picks' will show champions ordered by pick rate.
        *   'wins' will show champions ordered by win rate.
        *   'unique' will show a summary of the number of unique champions
            picked or banned.
        *   Any unique prefix of a champion name will show stats for that
            champion (e.g. !lcs-pb tahm).
*   !lore [champ]
    *   Prints out the champion's lore. Note: it only works as a PM to hypebot.
*   !freelo
    *   Hypebot gives dank advice for climbing the elo ladder.
*   !(p|passive) [champ]
    *   Prints out champion passive.
*   !patch[notes] [patch_number]
    *   Prints a link to the most recent patch notes, or the notes for the
        specified patch_number
*   !roster [team]
    *   Prints the starting roster for a given LCS team
*   !schedule(full) [league]
    *   Prints 5 (10 if full) upcoming LCS matches for the given leauge, or any
        upcoming matches if no league is given.
*   !skill (q|w|e|r) [champ] OR !(q|w|e|r) [champ]
    *   Prints out champion skill.
*   !standings [league]
    *   Prints LCS standings for the given league. NOTE: Does not work in #lol.
*   !stats [champ]
    *   Prints out champion base/scaling stats.
*   !statsat [level] [champ]
    *   Prints out champion base stats at the given level.
*   !trivia [N]
    *   Prints out N trivia questions. Answer the question by typing a line
        containing only the answer. NOTE: Only available in #trivia.
*   !who[all][-region] [name|me]
    *   Looks up specified summoner name along with extra data from Rito. "me"
        will use your own username, !whoall will fetch smurf accounts in
        addition to a user's main account. Takes an optional region following a
        hyphen after !who or !whoall (e.g. !who-euw [name]).
