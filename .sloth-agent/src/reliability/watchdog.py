"""Watchdog - Heartbeat monitoring for agent process."""

import logging
import threading
import time
from datetime import datetime

from sloth_agent.core.config import Config

logger = logging.getLogger("watchdog")


class Watchdog:
    """
    Monitors agent heartbeat and restarts if process is unresponsive.

    Heartbeat interval: 3 minutes (180 seconds)
    Max missing heartbeats: 3 (9 minutes total before restart)
    Restart delay: 60 seconds
    """

    def __init__(self, config: Config, on_death=None):
        self.config = config
        self.heartbeat_interval = config.watchdog.heartbeat_interval
        self.max_missing = config.watchdog.max_missing_heartbeats
        self.restart_delay = config.watchdog.restart_delay
        self.on_death_callback = on_death

        self._last_heartbeat = datetime.now()
        self._missing_count = 0
        self._running = False
        self._thread = None

    def start(self):
        """Start the watchdog monitoring thread."""
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Watchdog started")

    def stop(self):
        """Stop the watchdog monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Watchdog stopped")

    def heartbeat(self):
        """Record a heartbeat from the agent process."""
        self._last_heartbeat = datetime.now()
        self._missing_count = 0
        logger.debug("Heartbeat received")

    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            time.sleep(self.heartbeat_interval)

            elapsed = (datetime.now() - self._last_heartbeat).total_seconds()

            if elapsed > self.heartbeat_interval:
                self._missing_count += 1
                logger.warning(
                    f"Missed heartbeat #{self._missing_count} "
                    f"(elapsed: {elapsed:.1f}s)"
                )

                if self._missing_count >= self.max_missing:
                    logger.error("Agent process unresponsive, triggering death handler")
                    self._handle_death()

    def _handle_death(self):
        """Handle agent death - trigger recovery."""
        self._running = False

        if self.on_death_callback:
            logger.info("Initiating agent recovery after death")
            threading.Timer(self.restart_delay, self.on_death_callback).start()
