"""dakie: command-line tools behind the dakie_clips skill.

  dakie setup                         build the SFX + press libraries, write config
  dakie doctor                        check tools
  dakie init <url>                    create project + rights check (no video download)
  dakie scan <project>                chat replay, audio loudness, transcript
  dakie candidates <project>          rank candidate moments -> analysis/candidates.md
  dakie text <project> <from> <to>    print transcript for a range (--compact 30)
  dakie prepare <project> <n> <start> <end>   download section, word timings, face tracking
  dakie words <project> <n>           print the clip's timed transcript (for writing the plan)
  dakie render <project> <n>          render clips/clip_NN/plan.json -> final.mp4
  dakie package <project> <n>         validate meta.json, copyright checklist, copy to final/
  dakie sfx list|add|suggest          manage the sound-effects library
  dakie press list|add                manage hydraulic press footage
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
    p = sub.add_parser("candidates"); p.add_argument("project"); p.add_argument("--top", type=int, default=25)
    p.add_argument("--chat-delay", type=float, default=8.0)
    p = sub.add_parser("text"); p.add_argument("project"); p.add_argument("start"); p.add_argument("end")
    p.add_argument("--compact", type=int, default=0)
    p = sub.add_parser("prepare"); p.add_argument("project"); p.add_argument("n", type=int)
    p.add_argument("start"); p.add_argument("end")
    p = sub.add_parser("words"); p.add_argument("project"); p.add_argument("n", type=int)
    p = sub.add_parser("render"); p.add_argument("project"); p.add_argument("n", type=int)
    p = sub.add_parser("package"); p.add_argument("project"); p.add_argument("n", type=int)
    p = sub.add_parser("sfx"); p.add_argument("action", choices=["list", "add", "suggest", "rebuild"])
    p.add_argument("args", nargs="*")
    p.add_argument("--name"); p.add_argument("--tags", default=""); p.add_argument("--license")
    p.add_argument("--source", default=""); p.add_argument("--category", default="custom")
    p = sub.add_parser("press"); p.add_argument("action", choices=["list", "add", "generate"])
    p.add_argument("args", nargs="*"); p.add_argument("--license"); p.add_argument("--source", default="")
    p.add_argument("--seed", type=int, default=2)
    a = ap.parse_args(argv)

    if a.cmd == "setup":
        from . import press, sfx
        from .common import ensure_home
        ensure_home()
        sfx.init_library()
        press.init_library()
        print(f"Config: {CONFIG_PATH}\nHome:   {HOME}")
    elif a.cmd == "doctor":
        import shutil, subprocess
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
    elif a.cmd == "render":
        from .clip import render
        render(project_dir(a.project), a.n)
    elif a.cmd == "package":
        from .meta import package
        package(project_dir(a.project), a.n)
    elif a.cmd == "sfx":
        from . import sfx
        if a.action == "list":
            for e in sfx.library():
                print(f"{e['name']:16} {e['category']:11} {', '.join(e['tags'])}  [{e['license'][:40]}]")
        elif a.action == "rebuild":
            sfx.init_library(force=True)
        elif a.action == "add":
            if not a.args or not a.name:
                sys.exit("usage: dakie sfx add <file> --name NAME --tags a,b --license LICENSE [--source URL] [--category C]")
            sfx.add(a.args[0], a.name, [t.strip() for t in a.tags.split(",") if t.strip()], a.license, a.source, a.category)
        elif a.action == "suggest":
            from .clip import clip_dir
            from .common import read_json
            words = read_json(clip_dir(project_dir(a.args[0]), int(a.args[1])) / "words.json")["words"]
            print(json.dumps(sfx.suggest(words, 20), indent=2))
    elif a.cmd == "press":
        from . import press
        from .common import PRESS_DIR
        if a.action == "list":
            for e in press.library():
                print(f"{e['file']:32} {'on ' if e.get('enabled', True) else 'off'} [{e['license']}]")
        elif a.action == "add":
            if not a.args:
                sys.exit("usage: dakie press add <file.mp4> --license LICENSE [--source URL]")
            press.add(a.args[0], a.license, a.source)
        elif a.action == "generate":
            from .common import read_json, write_json
            out = PRESS_DIR / f"generated_press_{a.seed:02d}.mp4"
            press.generate(out, seed=a.seed)
            lib = [e for e in press.library() if e["file"] != out.name]
            lib.append({"file": out.name, "license": "Original: generated by Dakie Clips (you own it)",
                        "source": "dakie press generator", "enabled": True})
            write_json(press.LIB, lib)
            print(f"Added {out}")


if __name__ == "__main__":
    main()
