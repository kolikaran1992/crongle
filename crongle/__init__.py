"""
Crongle – Kaggle Kernel Job Management Library

This package provides tools to submit Kaggle kernels programmatically,
track their execution, poll for results, and automatically download
outputs while managing temporary artifacts and cron jobs.

Core Classes:
- KernelJob: Dataclass schema representing a Kaggle kernel job.
- KernelLauncher: Submit kernels and manage job metadata.
- KAGGLE_API: Authenticated Kaggle API instance.
- get_kernel_url: Utility to generate Kaggle kernel URLs.
"""

# Core job objects
from .kernel_job import KernelJob
from .kernel_launcher import KernelLauncher

# Kaggle API
from .kaggle_api import KAGGLE_API, KAGGLE_USER_NAME


def get_kernel_url(kernel_name: str) -> str:
    return f"https://www.kaggle.com/code/{KAGGLE_USER_NAME}/{kernel_name}"


__all__ = [
    "KernelJob",
    "KernelLauncher",
    "KAGGLE_API",
    "get_kernel_url",
]
