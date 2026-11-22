"""dakie: command-line tools behind the dakie_clips skill.

  dakie setup                         build the SFX + press libraries, write config
  dakie doctor                        check tools
  dakie init <url>                    create project + rights check (no video download)
  dakie scan <project>                chat replay, audio loudness, transcript
  dakie candidates <project>          rank candidate moments -> analysis/candidates.md
  dakie text <project> <from> <to>    print transcript for a range (--compact 30)
  dakie prepare <project> <n> <start> <end>   download section, word timings, face tracking
  dakie words <project> <n>           print the clip's timed transcript (for writing the plan)
  dakie layout <project> <n>          when the webcam overlay is on screen; suggests plan "cam_off"
  dakie render <project> <n>          render clips/clip_NN/plan.json -> final.mp4
  dakie package <project> <n>         validate meta.json, copyright checklist, copy to final/
  dakie keywords <phrase> [...]       YouTube search suggestions for hashtag/SEO research
  dakie publish status|setup|plan|run|enable|disable|privacy   upload finished clips (always with approval)
  dakie sfx list|add|remove|tag|suggest|rebuild     manage the sound-effects library
  dakie press list|add|remove|enable|disable|priority|generate   manage hydraulic press footage

Library examples:
  dakie press add ~/Downloads/press1.mp4 ~/Downloads/press2.mp4 --license "Pexels License" --source <url>
  dakie press add ~/Downloads/press_folder --license "Pixabay Content License"
  dakie press generate --count 3          (3 more original loops you own)
  dakie sfx add ~/Downloads/boom.mp3 --tags "impact,explosion" --license CC0 --category impact
  dakie sfx add ~/Downloads/sfx_pack --license "Pixabay Content License" --category custom
"""
from __future__ import annotations

import argparse
import json
import sys

from .common import CONFIG_PATH, HOME, ffmpeg, parse_ts, project_dir


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dakie", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup")
    sub.add_parser("doctor")
    p = sub.add_parser("init"); p.add_argument("url")
    p = sub.add_parser("scan"); p.add_argument("project")
    p = sub.add_parser("candidates"); p.add_argument("project"); p.add_argument("--top", type=int, default=40)
    p.add_argument("--chat-delay", type=float, default=8.0)
    p = sub.add_parser("text"); p.add_argument("project"); p.add_argument("start"); p.add_argument("end")
    p.add_argument("--compact", type=int, default=0)
    p = sub.add_parser("prepare"); p.add_argument("project"); p.add_argument("n", type=int)
    p.add_argument("start"); p.add_argument("end")
    p = sub.add_parser("words"); p.add_argument("project"); p.add_argument("n", type=int)
    p = sub.add_parser("layout"); p.add_argument("project"); p.add_argument("n", type=int)
    p = sub.add_parser("render"); p.add_argument("project"); p.add_argument("n", type=int)
    p = sub.add_parser("package"); p.add_argument("project"); p.add_argument("n", type=int)
    p = sub.add_parser("keywords"); p.add_argument("phrases", nargs="+")
    p = sub.add_parser("publish", help="upload finished clips to YouTube, Instagram, Facebook, TikTok")
    p.add_argument("action", choices=["status", "setup", "plan", "run", "enable", "disable", "privacy"])
    p.add_argument("args", nargs="*")
    p.add_argument("--clips", default=""); p.add_argument("--platforms", default="")
    p.add_argument("--approve"); p.add_argument("--force", action="store_true")
    p.add_argument("--include-red", action="store_true")
    p.add_argument("--client-secret-file"); p.add_argument("--page-id"); p.add_argument("--port", type=int, default=8765)
    p = sub.add_parser("sfx"); p.add_argument("action", choices=["list", "add", "remove", "tag", "suggest", "rebuild"])
    p.add_argument("args", nargs="*")
    p.add_argument("--name"); p.add_argument("--tags", default=""); p.add_argument("--license")
    p.add_argument("--source", default=""); p.add_argument("--category", default="custom")
    p = sub.add_parser("press")
    p.add_argument("action", choices=["list", "add", "remove", "enable", "disable", "priority", "generate"])
    p.add_argument("args", nargs="*"); p.add_argument("--license"); p.add_argument("--source", default="")
    p.add_argument("--name"); p.add_argument("--priority", type=int, default=8)
    p.add_argument("--credit", help="attribution line for CC BY footage, added to every clip's description")
    p.add_argument("--seed", type=int); p.add_argument("--count", type=int, default=1)
    a = ap.parse_args(argv)

    if a.cmd == "setup":
        from . import press, sfx
        from .common import ensure_home
        ensure_home()
        sfx.init_library()
        press.init_library()
        print(f"Config: {CONFIG_PATH}\nHome:   {HOME}")
    elif a.cmd == "doctor":
        import subprocess
        from .common import venv_bin
        print("ffmpeg :", ffmpeg())
        print("yt-dlp :", subprocess.run([venv_bin("yt-dlp"), "--version"], capture_output=True, text=True).stdout.strip())
        print("deno   :", venv_bin("deno"))
        for mod in ("faster_whisper", "chat_downloader", "numpy", "PIL"):
            try:
                __import__(mod); print(f"{mod:15}: ok")
            except Exception as e:
                print(f"{mod:15}: MISSING ({e})")
        r = subprocess.run([sys.executable, "-c", "import cv2;print(cv2.__version__)"], capture_output=True, text=True)
        print("opencv :", r.stdout.strip() or r.stderr[-200:])
        print("home   :", HOME, "(exists)" if HOME.exists() else "(run: dakie setup)")
    elif a.cmd == "init":
        from .fetch import init
        init(a.url)
    elif a.cmd == "scan":
        from .fetch import scan
        scan(project_dir(a.project))
    elif a.cmd == "candidates":
        from .signals import build
        build(project_dir(a.project), a.top, a.chat_delay)
    elif a.cmd == "text":
        from .signals import text_range
        print(text_range(project_dir(a.project), parse_ts(a.start), parse_ts(a.end), a.compact))
    elif a.cmd == "prepare":
        from .clip import prepare
        prepare(project_dir(a.project), a.n, parse_ts(a.start), parse_ts(a.end))
    elif a.cmd == "words":
        from .clip import dump_words
        print(dump_words(project_dir(a.project), a.n))
    elif a.cmd == "layout":
        from .clip import layout_timeline
        r = layout_timeline(project_dir(a.project), a.n)
        print(r["timeline"] or r.get("note"))
        print("(1 char per second: . = webcam overlay on screen, F = no overlay / camera full-screen)")
        print("suggested plan cam_off:", json.dumps(r["cam_off"]))
    elif a.cmd == "render":
        from .clip import render
        render(project_dir(a.project), a.n)
    elif a.cmd == "package":
        from .meta import package
        package(project_dir(a.project), a.n)
    elif a.cmd == "publish":
        from . import publish as pub
        if a.action == "status":
            print(pub.status())
        elif a.action == "setup":
            import getpass

            def ask(label, hidden=False):
                while True:      # paste, then Return; an empty answer just asks again
                    v = (getpass.getpass(label) if hidden else input(label)).strip()
                    if v:
                        return v
                    print("  (nothing received - paste it with Cmd+V, then press Return)")
            which = (a.args or [""])[0]
            if which == "youtube":
                f = a.client_secret_file or input("Path to the Google OAuth client JSON (Desktop app): ")
                f = f.strip().strip("'\"").replace("\\ ", " ")   # accept drag-and-drop paths
                pub.setup_youtube(f, a.port)
            elif which in ("meta", "instagram", "facebook"):
                app_id = ask("Meta App ID: ")
                secret = ask("Meta App Secret (hidden): ", True)
                token = ask("User access token from Graph API Explorer (hidden): ", True)
                pub.setup_meta(app_id, secret, token, a.page_id)
            elif which == "tiktok":
                key = ask("TikTok Client Key: ")
                while True:
                    secret = ask("TikTok Client Secret (hidden): ", True)
                    ok, why = pub.check_tiktok_client(key, secret)
                    if ok:
                        print("  Key and secret accepted by TikTok.")
                        break
                    print(f"  TikTok rejected this key + secret ({why}). The secret you pasted is {len(secret)} "
                          "characters long.\n  Make sure you're on the SANDBOX tab, reveal Client secret, use its copy "
                          "button, then paste again.")
                pub.setup_tiktok(key, secret, a.port)
            else:
                sys.exit("usage: dakie publish setup youtube|meta|tiktok   (see references/publishing.md)")
        elif a.action in ("enable", "disable"):
            if not a.args or a.args[0] not in pub.PLATFORMS:
                sys.exit(f"usage: dakie publish {a.action} {'|'.join(pub.PLATFORMS)}")
            pub._set_enabled(a.args[0], a.action == "enable")
            print(pub.status())
        elif a.action == "privacy":
            if not a.args or a.args[0] not in ("public", "unlisted", "private"):
                sys.exit("usage: dakie publish privacy public|unlisted|private   (YouTube default)")
            cfg = json.loads(CONFIG_PATH.read_text())
            cfg.setdefault("publish", {}).setdefault("youtube", {})["privacy"] = a.args[0]
            CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
            print(pub.status())
        elif a.action == "plan":
            if not a.args:
                sys.exit("usage: dakie publish plan <project> [--clips 1,2,3] [--platforms youtube,tiktok]")
            clips = [int(x) for x in a.clips.split(",") if x.strip()] or None
            plats = [x.strip() for x in a.platforms.split(",") if x.strip()] or None
            plan = pub.make_plan(project_dir(a.args[0]), clips, plats, a.include_red)
            print(pub.plan_markdown(plan))
        elif a.action == "run":
            if not a.args or not a.approve:
                sys.exit("usage: dakie publish run <project> --approve <plan id>   "
                         "(only after the plan was reviewed and approved)")
            pub.run_plan(project_dir(a.args[0]), a.approve, a.force,
                         only_platforms=[p.strip() for p in a.platforms.split(",") if p.strip()] or None,
                         only_clips=[c.strip() for c in a.clips.split(",") if c.strip()] or None)
    elif a.cmd == "keywords":
        from .meta import keyword_suggestions
        for ph in a.phrases:
            print(f"{ph}:")
            for k in keyword_suggestions(ph):
                print(f"  {k}")
    elif a.cmd == "sfx":
        from . import sfx
        if a.action == "list":
            lib = sfx.library()
            for e in lib:
                print(f"{e['name']:18} {e['category']:11} {', '.join(e['tags'])}  [{e['license'][:40]}]")
            print(f"\n{len(lib)} sounds in {len({e['category'] for e in lib})} categories")
        elif a.action == "rebuild":
            sfx.init_library(force=True)
        elif a.action == "add":
            if not a.args or not a.license:
                sys.exit("usage: dakie sfx add <file|folder> [...] --license LICENSE [--tags a,b] [--category C] "
                         "[--name NAME] [--source URL]")
            sfx.add(a.args, [t.strip() for t in a.tags.split(",") if t.strip()], a.license, a.source,
                    a.category, a.name)
        elif a.action == "remove":
            if not a.args:
                sys.exit("usage: dakie sfx remove <name>")
            sfx.remove(a.args[0])
        elif a.action == "tag":
            if not a.args or not a.tags:
                sys.exit("usage: dakie sfx tag <name> --tags a,b,c")
            sfx.retag(a.args[0], [t.strip() for t in a.tags.split(",") if t.strip()])
        elif a.action == "suggest":
            from .clip import clip_dir
            from .common import read_json
            words = read_json(clip_dir(project_dir(a.args[0]), int(a.args[1])) / "words.json")["words"]
            print(json.dumps(sfx.suggest(words, 20), indent=2))
    elif a.cmd == "press":
        from . import press
        from .common import PRESS_DIR
        if a.action == "list":
            lib = press.library()
            for e in lib:
                print(f"{e['file']:40} {'on ' if e['enabled'] else 'off'} p{e['priority']:<2} [{e['license'][:60]}]")
            on = sum(1 for e in lib if e["enabled"])
            print(f"\n{on} enabled press videos: up to {on} clips per project can each get a different one.")
        elif a.action == "add":
            if not a.args or not a.license:
                sys.exit("usage: dakie press add <file|folder> [...] --license LICENSE [--source URL] "
                         "[--priority 1-10] [--name NAME]")
            press.add(a.args, a.license, a.source, a.priority, a.name, a.credit)
        elif a.action in ("remove", "enable", "disable", "priority"):
            if not a.args:
                sys.exit(f"usage: dakie press {a.action} <file>" + (" --priority N" if a.action == "priority" else ""))
            if a.action == "remove":
                press.remove(a.args[0])
            else:
                press.set_entry(a.args[0], enabled={"enable": True, "disable": False}.get(a.action),
                                priority=a.priority if a.action == "priority" else None)
        elif a.action == "generate":

            lib = press.library()
            taken = {int(e["file"][16:18]) for e in lib if e["file"].startswith("generated_press_")}
            seeds = [a.seed] if a.seed else []
            k = 1
            while len(seeds) < a.count:
                if k not in taken and k not in seeds:
                    seeds.append(k)
                k += 1
            for seed in seeds:
                out = PRESS_DIR / f"generated_press_{seed:02d}.mp4"
                theme = press.THEMES[(seed - 1) % len(press.THEMES)]["name"]
                print(f"Rendering original press loop {seed} ({theme})...")
                press.generate(out, seed=seed)
                lib = [e for e in lib if e["file"] != out.name]
                lib.append({"file": out.name, "license": press.ORIGINAL, "source": "dakie press generator",
                            "enabled": True, "priority": 5})
            press.save(lib)
            print(f"Added {len(seeds)} loop(s).")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:          # API errors: show the message, not a traceback
        msg = str(e)
        if "expired" in msg.lower() or "validating access token" in msg.lower():
            msg += ("\n\nThe token has expired. Generate a new one (for Meta: Graph API Explorer > "
                    "Generate Access Token) and run the setup again right away.")
        sys.exit("\n" + msg)
