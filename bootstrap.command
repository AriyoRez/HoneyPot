#!/usr/bin/env bash
# bootstrap.command — double-clickable macOS launcher for setup.sh.
#
# On first run, macOS Gatekeeper may block this file. If so, right-click the
# file in Finder and choose "Open" once to allow it, then it will run normally.
cd "$(dirname "$0")"
./setup.sh
