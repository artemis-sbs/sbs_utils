"""Sizzle-reel capture harness (dev-only).

Shoots a promotional cut of Cosmos by staging scenes in the real engine, stepping a
declarative shot list, and capturing through OBS.

The design constraint that shapes everything here: the author of the shot list cannot
watch video, only stills. So the primary mode is not "record" - it is `contact`, which
steps the shot list one shot at a time, grabs one still per shot, and tiles them into a
single reviewable PNG. Recording only happens once the framing is already right.

See `cosmos_dev/tools/sizzle.py` for the CLI.
"""
