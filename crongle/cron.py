"""
Crongle: Poll Kernel Status Script
----------------------------------
This script is invoked by cron jobs to check the status of Kaggle kernels.
It takes a `--job-id` argument, retrieves the corresponding job config,
checks if the kernel run is complete, and downloads results if so.

If complete or cancelled → cleans up job and removes its cron.
"""

import argparse, sys, requests, os
from pathlib import Path

from crongle.kernel_job import KernelJob
from crongle.kernel_watcher import cleanup_job
from crongle.utils import (
    get_cron_output_logfile,
    get_job_json_path,
    load_json_file,
    JobFileError,
    logger,
    config,
)
from crongle.kaggle_api import KAGGLE_USER_NAME as username, KAGGLE_API


def _send_slack_message(
    status: str,
    details: str,
    job_id: str,
) -> None:
    """
    Sends a structured notification message to the Slack channel configured in config.

    Args:
        title (str): Title of the message.
        status (str): Status string, e.g., "CRITICAL ALERT" or "CRON RUN COMPLETE".
        details (str): Detailed description or log of the event.
        job_id (str): Optional job identifier.
    """
    slack_bot_token = os.environ.get("SLACK_BOT_TOKEN") or ""
    slack_channel_id = os.environ.get("SLACK_CHANNEL_ID") or ""

    if not slack_bot_token or not slack_channel_id:
        logger.info(
            f"empty SLACK_BOT_TOKEN: '{slack_bot_token}' or SLACK_CHANNEL_ID: '{slack_channel_id}', not sending slack notification"
        )
        return

    timestamp = config.now_iso

    message = f"\n--- CRONGLE Notification ---\n" f"[{timestamp}] STATUS: {status}\n"

    if job_id:
        message += f"JOB ID: {job_id}\n"

    message += f"DETAILS:\n{details}\n"
    message += "------------------------------\n"

    headers = {
        "Authorization": f"Bearer {slack_bot_token}",
        "Content-Type": "application/json",
    }
    payload = {"channel": slack_channel_id, "text": message}

    try:
        response = requests.post(
            "https://slack.com/api/chat.postMessage", json=payload, headers=headers
        )
        data = response.json()
        if not data.get("ok"):
            raise Exception(f"Slack API error: {data}")
        logger.info("Slack message sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send Slack message: {e}")


def _load_job(job_id: str) -> KernelJob:
    """Load job metadata JSON using shared utils."""
    job_json_path = get_job_json_path(job_id)
    data = load_json_file(job_json_path)
    return KernelJob.from_dict(data)


def _get_kernel_status(kernel_name: str) -> str:
    """Return the current Kaggle kernel status."""
    try:
        status = KAGGLE_API.kernels_status(
            f"{username}/{kernel_name}"
        ).status.name.lower()
        logger.info(f"Kernel '{kernel_name}' status: {status}")
        return status
    except Exception as e:
        logger.error(f"Failed to fetch kernel status for {kernel_name}: {e}")
        return "unknown"


def _download_kernel_output(job: KernelJob) -> None:
    """Download kernel output to the job's output folder."""
    try:
        logger.info(
            f"Downloading output for kernel {job.kernel_name} → {Path(job.output_folder).resolve().as_posix()}"
        )
        KAGGLE_API.kernels_output(
            kernel=f"{username}/{job.kernel_name}", path=job.output_folder
        )
        logger.info(f"Download complete for job {job.job_id}")
    except Exception as e:
        logger.error(f"Failed to download kernel output for {job.kernel_name}: {e}")


def _get_job_id_from_args():
    parser = argparse.ArgumentParser(
        description="Poll Kaggle kernel job status and cleanup when done."
    )
    parser.add_argument(
        "--job-id", required=True, help="The job_id of the kernel job to poll."
    )
    args = parser.parse_args()

    return args.job_id


def main():
    try:
        job_id = _get_job_id_from_args()
        job = _load_job(job_id)
    except JobFileError as e:
        logger.error(f"Unexpected error while loading job: {job_id}, {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error while loading job: {job_id}, {e}")
        sys.exit(1)

    status = _get_kernel_status(job.kernel_name)
    details = f"\ncron output logfile: {get_cron_output_logfile(job.job_id)}\n"
    _send_slack_message(status=status, details=details, job_id=job_id)
    if status in ("complete", "cancel_acknowledged", "error", "unknown"):
        logger.info(
            f"Kernel {job.kernel_name} finished with status '{status}' — downloading results."
        )
        if status == "complete":
            _download_kernel_output(job)
            details += f"\ndata downloaded at: {Path(job.output_folder).resolve().as_posix()}\n"
        cleanup_job(job)
        details += f"\ncleaned up job metadata\n"
        _send_slack_message(status=status, details=details, job_id=job_id)
        logger.info(f"Job {job.job_id} cleanup complete.")
    elif status == "running":
        logger.info(
            f"Job {job.job_id} still running inside Kernel {job.kernel_name} — will check again later."
        )
    else:
        logger.warning(
            f"Unknown or failed status '{status}' for {job.kernel_name}. No action taken."
        )


if __name__ == "__main__":
    main()
