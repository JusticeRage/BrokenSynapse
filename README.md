# Broken Synapse

This repository contains the scripts I wrote in the few days I spent reversing the [Frozen Synapse](http://store.steampowered.com/app/98200) game.
They are released in the hope that someone wanting to write mods for the game will find them useful, but as for me, I've seen enough about its internals and don't plan on digging further.
 
I realize that these scripts could be used to enable cheating in multiplayer modes, so all I can say is: don't be that guy.

All the code is released under the terms of the [GPLv3 license](https://www.gnu.org/licenses/gpl-3.0.en.html).

This tool was designed for Python 2.7.

## frozen.py

This script is a quick client implementation which enables you to log into the game's server and get information from the lobby. You can also use it to download *encounter* files, which describe games.

```
$> ./frozen.py
*** Successfully logged in as SniperZwolf!
Active games:
	Extermination against Sichevoy-strelok (#1321820)
You are currently level 130.
Red DLC is activated for your account!
6 online players: 
	IceAngler (22)
	NeonMage (9)
	mouse2324 (1)
	Trigangle (2)
	Awakezok (1)
	Espekuer (1)
File recieved: psychoff/homeSc.txt:
----------
Frozen Synapse Out Now On PS Vita

<a:link\tj.mp*fsprime>Frozen Synapse Prime (EU) for PS Vita</a>
<a:link#tj.mp*fsprimeus>Frozen Synapse Prime (US) for PS Vita</a>

Frozen Synapse is also available for both Android tablets and the iPad - grab it while it's...cold.

<a:link\tj.mp*15bgOGy>Google Play Store</a>
<a:link\tappstore.com*frozensynapse>iOS App Store</a>
motd end
343407	Questar	ch1pm0nk
5
Afkoori	wonderhero	Neofelis	npktqb	Kron-OS	-	GionSina	RADR	pforhan	Mayu	kulho	-	MIB2	Milkopilko	Afkoori	robopuppycc	Slice	-	-
----------
* Server ping *
```

To use it, modify line 67 (`if not login(s, "[username]", "[password]"):`) with your own username and password. uncomment `s.send("textcom\tcommand\tselectMT\t[game ID]\n")` to obtain turn files for a given game.
Read through the script to find more commands to communicate with the server. You are also encouraged to use Wireshark and snoop on the game's traffic if you want to extend the client's capabilities.

## frozen_parse_mt.py

An incomplete parser for MT (multiturn) files, which describe a Frozen Synapse match.
Only the file's header is parsed; the rest of the format hasn't been reversed yet (although the script contains some pointers). I may go back to it one day. If you want to do it, you should look at the `Encounter::saveTo(Encounter *this, const char *)` function with IDA.

```
$> ./frozen_parse_mt.py enc/caff_finished.enc
Game 1321834 (finished with a score of -40.00 in 4 turns)
Player 1: caffinator (Rank: 4276 - Level: 18 - Wins: 52 - Losses: 62)
Player 2: SniperZwolf (Rank: 188 - Level: 129 - Wins: 610 - Losses: 248)
Match history: caffinator won 0 time(s) and SniperZwolf won 1 time(s).
```

## parse_dso.py

This is a decompiler for DSO files. It is compatible with the latest version of the Torque engine, and also the old one used by Frozen Synapse.
The code it generates can most of the time be used to replace the original DSO files which is quite nice, but it is far from being 100% foolproof. You may have to manually correct syntax errors if the game stops working as intended. Worst case scenario, you should still be able to read the game's code.
If you're working on an interesting mod and face some issues with the decompiler, get in touch with me and I'll do my best to fix the problem!

You can probably use this script to decompile other Torque engine games, but depending on their version, some modifications may be necessary. At some point between version 36 and 44, an offset was introduced in the opcodes. If you encounter problems, your best bet is to modify the `translate_opcode` function in `torque_vm_values.py` so opcodes are translated for the version you are working on. Again, feel free to get in touch with me if you need a hand here.

```
$> python parse_dso.py "[...]\Steam\SteamApps\common\Frozen Synapse\psychoff\gameScripts\gsClient.cs.dso" --stdout
$gsCommandPort = 28021;
if ($altPort)
{
	$gsCommandPort = 28028;
}
$minUsernameLen = 3;
$maxUsernameLen = 20;
$minPasswordLen = 3;
$maxPasswordLen = 40;
$newBaronIp = "62.197.39.230";
$grandServerIP = $newBaronIp;
if ($officeServer)
{
	$grandServerIP = "192.168.0.12";
}
...
```
The script's help contains more information about its usage.

## Contact
[![E-Mail](http://manalyzer.org/static/mail.png)](mailto:justicerage *at* manalyzer.org)
[![Tw](http://manalyzer.org/static/twitter.png)](https://twitter.com/JusticeRage)
[![GnuPG](http://manalyzer.org/static/gpg.png)](https://pgp.mit.edu/pks/lookup?op=vindex&search=0x40E9F0A8F5EA8754)
