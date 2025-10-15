import shutil, sys
from pathlib import Path

from dataclasses import dataclass

from crontab import CronTab
from crongle.utils import get_cron_output_logfile, get_job_json_path, config, logger
from crongle.kernel_job import KernelJob
import getpass


_PYTHON_PATH = sys.executable

Path(config.crongle.cron_job_log_base_dir).mkdir(exist_ok=True, parents=True)


@dataclass(frozen=True)
class CronInterval:
    minute: str = "minute"
    hour: str = "hour"


def _get_cron_comment(job_id: str) -> str:
    """Return a unique cron comment string for a job."""
    return f"crongle-job-{job_id}"


def initialize_polling_cron(
    job: KernelJob,
    interval_amount: int = 5,
    interval_unit: str = CronInterval.minute,
    slack_channel_id: str = None,
    slack_bot_token: str = None,
) -> None:
    """
    Create a cron job that periodically runs the polling script for this kernel job.

    Args:
        job (KernelJob): The job to poll.
        interval_amount (int, optional): Interval frequency. Defaults to 5.
        interval_unit (str, optional): Time unit for scheduling ("seconds", "minutes", "hours").
                              Defaults to "minutes".
        slack_channel_id (str, optional): the id of the channel where slack messages have to be sent
        about cron status. If null then no slack message will be sent. Null by default
        slack_bot_token (str, optional): the bot token used for sending slack messages. If null then
        no slack message will be sent. Null by default

    """
    assert 0 < interval_amount <= 60 and isinstance(
        interval_amount, int
    ), f"`interval_amount` should be an integer between 1 and 60"

    poll_script_path = config.crongle.poll_script_path
    cron_comment = _get_cron_comment(job.job_id)

    cron_command = f"{_PYTHON_PATH} {poll_script_path} --job-id {job.job_id} >> {get_cron_output_logfile(job.job_id)} 2>&1"
    if slack_bot_token is not None and slack_channel_id is not None:
        cron_command = (
            f"SLACK_BOT_TOKEN={slack_bot_token} SLACK_CHANNEL_ID={slack_channel_id} "
        ) + cron_command
    cron = CronTab(user=getpass.getuser())

    # Prevent duplicates
    for existing in cron:
        if cron_comment in existing.comment:
            logger.warning(f"Cron for job {job.job_id} already exists. Skipping.")
            return

    job_cron = cron.new(command=cron_command, comment=cron_comment)

    if interval_unit == CronInterval.minute:
        job_cron.minute.every(interval_amount)
    elif interval_unit == CronInterval.hour:
        job_cron.hour.every(interval_amount)
    else:
        raise ValueError(f"Unsupported scheduling unit: {interval_unit}")

    cron.write()

    logger.info(
        f"Initialized polling cron for job {job.job_id} (every {interval_amount} {interval_unit})"
    )


def remove_polling_cron(job_id: str) -> None:
    """
    Remove the cron job associated with a given job_id.

    Args:
        job_id (str): Job ID whose cron needs to be removed.
    """
    cron = CronTab(user=getpass.getuser())
    removed = False

    for job in cron:
        if _get_cron_comment(job_id) in job.comment:
            cron.remove(job)
            removed = True

    if removed:
        cron.write()
        logger.info(f"Removed cron job for job_id {job_id}")
    else:
        logger.warning(f"No cron job found for job_id {job_id}")


def cleanup_job(job: KernelJob) -> None:
    """
    Clean up job artifacts after completion or cancellation.

    This removes:
        - The temporary folder
        - The job JSON file

    Args:
        job_json_path (str): Path to the per-job JSON file.
    """
    # Remove temp folder
    try:
        shutil.rmtree(job.temp_folder, ignore_errors=True)
        logger.info(f"Removed temporary folder for job {job.job_id}: {job.temp_folder}")
    except Exception as e:
        logger.error(f"Failed to remove temp folder for job {job.job_id}: {e}")

    # Remove job JSON
    try:
        job_json_path = get_job_json_path(job.job_id)
        Path(job_json_path).unlink(missing_ok=True)
        logger.info(f"Deleted job JSON for job {job.job_id}")
    except Exception as e:
        logger.error(f"Failed to delete job JSON for job {job.job_id}: {e}")

    # Remove cron
    remove_polling_cron(job.job_id)
