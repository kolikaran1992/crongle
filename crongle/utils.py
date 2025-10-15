import json
from pathlib import Path
from dynalog import config, get_logger
from crongle.kaggle_api import KAGGLE_USER_NAME

# Config and Logger --
# --------------------

logger = get_logger(__name__)

config = config.from_env(
    "default",
    keep=True,
    SETTINGS_FILE_FOR_DYNACONF=[
        Path(__file__).parent.parent.joinpath("settings.toml").as_posix()
    ],
)
config.crongle.poll_script_path = Path(__file__).parent.joinpath("cron.py").as_posix()


# Other Utils --
# --------------


class JobFileError(Exception):
    """Raised when job JSON cannot be found or loaded."""


def get_cron_output_logfile(job_id: str) -> str:
    return f"{config.crongle.cron_job_log_base_dir}/{job_id}.log"


def get_job_json_path(job_id: str) -> Path:
    """Return path to job metadata JSON file."""
    return Path(config.crongle.job_queue_dir).joinpath(f"{job_id}.json")


def load_json_file(json_path: Path) -> dict:
    """Safely load a JSON file and raise a clear exception if missing or invalid."""
    if not json_path.exists():
        raise JobFileError(f"Job JSON not found at: {json_path}")

    try:
        with open(json_path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise JobFileError(f"Invalid JSON at {json_path}: {e}")
    except Exception as e:
        raise JobFileError(f"Failed to read JSON at {json_path}: {e}")


def get_kernel_url(kernel_name: str) -> str:
    return f"https://www.kaggle.com/code/{KAGGLE_USER_NAME}/{kernel_name}"
