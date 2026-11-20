#!/usr/bin/env python3
"""ZJUT LUG · Linux 新手村 —— 三个小游戏。"""

from __future__ import annotations

import argparse
import random
import sys
import time

from box_game import BoxGame
from canvas import Canvas, Frame
from command_game import CommandGame
from sort_game import SortGame
from term import Terminal
from ui import (
    MIN_H, MIN_W, Menu, render_about, render_final, render_intro, render_pause,
    render_result, render_title, render_too_small,
)
from village import LEVELS, Run

FPS = 30


def make_game(key: str, w: int, h: int, rng: random.Random):
    if key == "sort":
        return SortGame(w, h, rng.randrange(1_000_000))
    if key == "command":
        return CommandGame(w, h, rng.randrange(1_000_000))
    return BoxGame(w, h, rng.randrange(1_000_000))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="lug-newbie", description="ZJUT LUG · Linux 新手村")
    ap.add_argument("--seed", type=int, default=None, help="固定随机种子（调试用）")
    args = ap.parse_args(argv or sys.argv[1:])
    rng = random.Random(args.seed if args.seed is not None else random.randrange(1_000_000))

    try:
        term = Terminal()
    except Exception as e:
        print(f"启动失败：{e}", file=sys.stderr)
        return 1

    state = "title"
    run = Run()
    game = None
    paused = False
    menu = Menu()
    pause_menu = Menu()
    placed_key = None
    last_size = None
    last = time.monotonic()
    running = True

    def go(new_state: str, reset_run: bool = False) -> None:
        nonlocal state, game, paused, placed_key, run
        if reset_run:
            run = Run()
        state = new_state
        game = None
        paused = False
        menu.focus = 0
        pause_menu.focus = 0
        placed_key = None
        term.clear_image()
        term.clear()

    def start_game() -> None:
        nonlocal game, state, paused, placed_key
        w, h = term.size()
        game = make_game(run.level.key, w, h, rng)
        state = "play"
        paused = False
        placed_key = None
        term.clear_image()
        term.clear()

    def record() -> None:
        nonlocal state
        if game is None:
            return
        run.record(game.outcome())
        state = "result"
        menu.focus = 0
        term.clear_image()
        term.clear()

    def next_level() -> None:
        run.advance()
        if run.finished:
            go("final")
        else:
            go("intro")

    def do_menu(action: str | None) -> None:
        nonlocal running, state
        if action is None:
            return
        if state == "title":
            if action == "start":
                go("intro", reset_run=True)
            elif action == "about":
                go("about")
            elif action == "quit":
                running = False
        elif state == "about":
            if action == "back":
                go("title")
        elif state == "intro":
            if action == "start":
                start_game()
            elif action == "title":
                go("title", reset_run=True)
        elif state == "result":
            if action == "next":
                next_level()
            elif action == "retry":
                start_game()
            elif action == "title":
                go("title", reset_run=True)
        elif state == "final":
            if action == "again":
                go("title", reset_run=True)
            elif action == "quit":
                running = False

    def do_pause(action: str | None) -> None:
        nonlocal paused
        if action is None:
            return
        if action == "resume":
            paused = False
            term.clear()
        elif action == "retry":
            start_game()
        elif action == "title":
            go("title", reset_run=True)

    def menu_key(key: str) -> None:
        nonlocal running
        if key in ("tab", "right", "down"):
            menu.move(1)
        elif key in ("left", "up"):
            menu.move(-1)
        elif key in ("enter", "space"):
            do_menu(menu.selected())
        elif key == "esc":
            if state == "about":
                go("title")
            elif state in ("intro", "result", "final"):
                go("title", reset_run=True)
            else:
                running = False
        elif key in ("q", "Q"):
            running = False

    with term:
        while running:
            frame_start = time.monotonic()
            dt = min(0.08, frame_start - last)
            last = frame_start
            w, h = term.size()
            if (w, h) != last_size:
                last_size = (w, h)
                placed_key = None
                term.clear_image()
                term.clear()
                if state == "play" and game is not None:
                    game = make_game(run.level.key, w, h, rng)

            key = term.read_key(0.008)
            mouse = None
            if key is not None and key.startswith("mouse:"):
                parts = key.split(":")
                mouse = (parts[1], int(parts[2]), int(parts[3]))
                key = None

            if key == "ctrl-c":
                running = False
            elif w < MIN_W or h < MIN_H:
                pass
            elif state == "title":
                if mouse:
                    action = menu.hit(mouse[1], mouse[2])
                    if action:
                        menu.hover_focus(mouse[1], mouse[2])
                        do_menu(action)
                elif key is not None:
                    menu_key(key)
            elif state == "about":
                if mouse:
                    action = menu.hit(mouse[1], mouse[2])
                    if action:
                        do_menu(action)
                elif key in ("esc", "q", "Q", "enter", "space"):
                    go("title")
            elif state == "intro":
                if mouse:
                    action = menu.hit(mouse[1], mouse[2])
                    if action:
                        menu.hover_focus(mouse[1], mouse[2])
                        do_menu(action)
                elif key is not None:
                    menu_key(key)
            elif state == "play" and game is not None:
                if paused:
                    if mouse:
                        action = pause_menu.hit(mouse[1], mouse[2])
                        if action:
                            do_pause(action)
                    elif key in ("p", "P", "esc"):
                        paused = False
                        term.clear()
                    elif key in ("tab", "right", "down"):
                        pause_menu.move(1)
                    elif key in ("left", "up"):
                        pause_menu.move(-1)
                    elif key in ("enter", "space"):
                        do_pause(pause_menu.selected())
                else:
                    if mouse:
                        if mouse[0] == "right":
                            paused = True
                            pause_menu.focus = 0
                            term.clear()
                        else:
                            game.click(mouse[1], mouse[2])
                    elif key in ("p", "P", "esc"):
                        paused = True
                        pause_menu.focus = 0
                        term.clear()
                    elif key is not None:
                        game.handle_key(key)
            elif state == "result":
                if mouse:
                    action = menu.hit(mouse[1], mouse[2])
                    if action:
                        menu.hover_focus(mouse[1], mouse[2])
                        do_menu(action)
                elif key is not None:
                    menu_key(key)
            elif state == "final":
                if mouse:
                    action = menu.hit(mouse[1], mouse[2])
                    if action:
                        menu.hover_focus(mouse[1], mouse[2])
                        do_menu(action)
                elif key in ("tab", "right", "down"):
                    menu.move(1)
                elif key in ("left", "up"):
                    menu.move(-1)
                elif key in ("enter", "space"):
                    do_menu(menu.selected())
                elif key in ("q", "Q", "esc"):
                    running = False

            if not running:
                break

            if state == "play" and game is not None and not paused:
                game.update(dt)
                if game.status != "playing":
                    record()

            if w < MIN_W or h < MIN_H:
                frame = render_too_small(Canvas(w, h))
            elif state == "title":
                frame = render_title(Canvas(w, h), menu, frame_start, term.protocol)
            elif state == "about":
                frame = render_about(Canvas(w, h), menu, frame_start)
            elif state == "intro":
                frame = render_intro(Canvas(w, h), run, menu, frame_start)
            elif state == "play" and game is not None:
                c = Canvas(w, h)
                game.render(c)
                if paused:
                    render_pause(c, pause_menu, run.level)
                frame = Frame(c.render())
            elif state == "result":
                outcome = run.outcomes.get(run.level.key)
                if outcome is None:
                    frame = render_title(Canvas(w, h), menu, frame_start, term.protocol)
                else:
                    frame = render_result(Canvas(w, h), run, outcome, menu, frame_start)
            else:
                frame = render_final(Canvas(w, h), run, menu, frame_start, term.protocol)

            term.write(frame.text)
            if frame.png is not None and frame.rect is not None:
                if frame.art_key != placed_key:
                    term.clear_image()
                    term.place_image(frame.img, frame.png, *frame.rect)
                    placed_key = frame.art_key
            elif placed_key is not None:
                term.clear_image()
                placed_key = None

            spent = time.monotonic() - frame_start
            if spent < 1 / FPS:
                time.sleep(1 / FPS - spent)

    print("新手村收摊了。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
