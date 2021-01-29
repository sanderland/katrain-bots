import json
import os
import sys
from settings import bot_strategies, greetings

if len(sys.argv) < 2:
    exit(0)

bot = sys.argv[1].strip()
port = int(sys.argv[2]) if len(sys.argv) > 2 else 8587

MAXGAMES = 10
GTP2OGS = "node ../gtp2ogs"
GTP2OGS = "node ../mygtp2ogs"

BOT_SETTINGS = f" --maxconnectedgames {MAXGAMES} --maxhandicapunranked 25 --maxhandicapranked 1 --noautohandicapranked --boardsizesunranked 9,13,19 --boardsizesranked 13,19 --komisranked automatic,5.5,6.5,7.5 --komisunranked all "
if "beta" in bot:
    BOT_SETTINGS += " --beta"
else:
    BOT_SETTINGS += "" #--rankedonly "

username = f"katrain-{bot}"

with open("config.json") as f:
    settings = json.load(f)
    all_ai_settings = settings["ai"]

ai_strategy, x_ai_settings, x_engine_settings = bot_strategies[bot]

ai_settings = {**all_ai_settings[ai_strategy], **x_ai_settings}

with open("secret/apikey.json") as f:
    apikeys = json.load(f)

if bot not in greetings or username not in apikeys:
    print("BOT {username} NOT FOUND")
    exit(1)

APIKEY = apikeys[username]
settings_dump = ", ".join(f"{k}={v}" for k, v in ai_settings.items() if not k.startswith("_"))
print(settings_dump)
newversion = "New version 1.7 with local search, distributed training models and Mac OSX package recently released!"
GREETING = f"Hello, play with these bots at any time by downloading KaTrain at bit.ly/katrain - {newversion} - Current mode is {ai_strategy} ({greetings[bot]})"
REJECTNEW = f"Sorry, the bots are shutting down and not accepting games right now, play with them at any time by downloading KaTrain at bit.ly/katrain - {newversion}"

if settings:
    GREETING += f" Settings: {settings_dump}."
BYEMSG = "Thank you for playing. If you have any feedback, please message my admin! "

cmd = f'{GTP2OGS} --debug --apikey {APIKEY} --rejectnewfile ~/shutdown_bots --username {username} --greeting "{GREETING}" --farewell "{BYEMSG}" --rejectnewmsg "{REJECTNEW}" {BOT_SETTINGS} --farewellscore --aichat --noclock --nopause --speeds blitz,live  --persist --minrank 25k  -- python ai2gtp.py {bot} {port}'
print(f"starting bot {username} using server port {port} --> {cmd}")
os.system(cmd)
