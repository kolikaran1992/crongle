from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4
from pathlib import Path

from crongle.utils import config, logger

_DEFAULT_JOB_STATUS = "RUNNING"

# timeout in seconds, default = 9 hours
_DEFAULT_JOB_TIMEOUT = config.crongle.default_job_timeout


@dataclass
class KernelJob:
    # Name of the Kaggle kernel
    kernel_name: str = field(init=True)

    # Original script path submitted by user
    script_path: str = field(init=True)

    # Path where results will be saved
    output_folder: str = field(init=True)

    # Temporary folder created for submission
    temp_folder: str = field(
        init=True,
        default_factory=lambda: Path(config.crongle.base_job_artefacts_dir)
        .joinpath(uuid4().hex)
        .as_posix(),
    )

    # Current status: running, complete, cancelled
    status: str = field(init=True, default=_DEFAULT_JOB_STATUS)

    # Timeout in seconds (default 9 hours)
    timeout: int = field(init=True, default=_DEFAULT_JOB_TIMEOUT)

    # Extra settings like GPU, internet, etc.
    kernel_kwargs: Optional[Dict] = field(init=True, default_factory=dict)

    job_id: str = field(init=True, default_factory=lambda: uuid4().hex)
    submitted_at: str = field(default_factory=lambda: config.now_iso)

    def __post_init__(self) -> None:
        Path(self.output_folder).mkdir(exist_ok=True, parents=True)
        Path(self.temp_folder).mkdir(exist_ok=True, parents=True)

    def to_dict(self) -> Dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "job_id": self.job_id,
            "kernel_name": self.kernel_name,
            "script_path": self.script_path,
            "output_path": self.output_folder,
            "temp_folder": self.temp_folder,
            "status": self.status,
            "submitted_at": self.submitted_at,
            "timeout": self.timeout,
            "kernel_kwargs": self.kernel_kwargs,
        }

    @staticmethod
    def from_dict(data: Dict) -> "KernelJob":
        """Deserialize from dictionary."""
        return KernelJob(
            job_id=data["job_id"],
            kernel_name=data["kernel_name"],
            script_path=data["script_path"],
            output_folder=data["output_path"],
            temp_folder=data["temp_folder"],
            status=data.get("status", _DEFAULT_JOB_STATUS),
            submitted_at=data.get("submitted_at"),
            timeout=data.get("timeout", _DEFAULT_JOB_TIMEOUT),
            kernel_kwargs=data.get("kernel_kwargs", {}),
        )
