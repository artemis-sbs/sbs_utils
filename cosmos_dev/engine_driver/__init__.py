"""Host-side driver for the REAL Artemis Cosmos engine (dev-only).

Unlike the in-engine code, this runs as a separate host process, so it may use
threads, queues, and pip packages freely. It launches the engine, drives it
through the cosmos_devqueue command queue (no mouse needed for control), tails
logs, and captures screenshots for the one thing the queue can't verify: the
actual rendered view.

See engine_driver.driver.EngineDriver.
"""
from .driver import EngineDriver, build_mastlib  # noqa: F401
