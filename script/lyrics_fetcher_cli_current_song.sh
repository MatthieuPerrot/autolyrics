#!/bin/env bash
./lyrics_fetcher_cli.py "$(lsof  -c mplayer -F 2>/dev/null | cut -c 2- | grep '\.mp3')"
