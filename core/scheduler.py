"""
===============================================================================

Hermes OS

File:
scheduler.py

Purpose:
Simple scheduler for running Hermes jobs.

Author:
Hermes Quant Labs

Foundation:
II - The Nervous System

===============================================================================
"""

from typing import Callable

from core.logger import logger


class Scheduler:
    """Simple job scheduler."""

    def __init__(self):
        self._jobs: dict[str, Callable] = {}

    def add_job(self, name: str, job: Callable) -> None:
        """Register a scheduled job."""
        self._jobs[name] = job
        logger.info(f"Scheduled job added: {name}")

    def run_job(self, name: str):
        """Run a scheduled job."""
        job = self._jobs.get(name)

        if job is None:
            logger.warning(f"Scheduled job not found: {name}")
            return

        logger.info(f"Running scheduled job: {name}")
        return job()

    def list_jobs(self) -> list[str]:
        """Return all scheduled job names."""
        return list(self._jobs.keys())


scheduler = Scheduler()
