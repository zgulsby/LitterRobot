#!/bin/sh
# Local convenience script — adjust paths to match your environment
cd "$(dirname "$0")"
python3 -m src.main >> /tmp/litterrobot.log 2>&1
