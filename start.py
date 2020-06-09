import re
import shlex
import subprocess
import sys
import threading

from settings import DEFAULT_PORT

port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
bots = sys.argv[2:]

shutting_down = False

STARTING, ENDING = "starting new bot", "bot exited"
KEYWORDS = ["error", STARTING, ENDING, "game over", "rejecting challenge"]
IGNORE = ["[Kivy", "[Python", "[GCC", "[Logger"]
LOGFILE = f"logs/log{port}"

active_bots = {bot: 0 for bot in bots}
active_bots["all_started"] = 0
started_count = 0

with open(LOGFILE, "a") as logf:

    def print_stats():
        total = 0
        for bot, num in active_bots.items():
            if num > 0 and not bot.startswith("all"):
                total += num
                print(f"\t{bot}: {num} active games")
        print(f"\ttotal: {total} active games, {active_bots['all_started']} started in this session")

    def read(io, tag):
        while not shutting_down:
            line = io.readline().decode().strip()
            if not line.strip():
                continue
            tagline = f"[{tag}] {line}"
            if not any(kw in line for kw in IGNORE):
                logf.write(tagline + "\n")
                logf.flush()

            if any(kw in line.lower() for kw in KEYWORDS):
                print(tagline)
            if STARTING in line.lower():
                active_bots[tag] += 1
                active_bots["all_started"] += 1
                print_stats()
            if ENDING in line.lower():
                active_bots[tag] -= 1
                print_stats()

    threads = []

    def startproc(cmd, tag):
        scmd = shlex.split(cmd)
        pipe = subprocess.Popen(scmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        t = threading.Thread(target=read, args=(pipe.stdout, tag), daemon=True)
        threads.append(t)
        t.start()
        t = threading.Thread(target=read, args=(pipe.stderr, tag + ":ERROR"), daemon=True)
        threads.append(t)
        t.start()
        print(f"'{cmd}' started")

    startproc(f"python engine_server.py {port}", "Engine")
    for botname in bots:
        startproc(f"python start_bot.py {botname} {port}", botname)

    for t in threads:
        t.join()
