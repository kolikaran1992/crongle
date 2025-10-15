import json
import shutil
from pathlib import Path

from crongle.kernel_job import KernelJob
from crongle.kaggle_api import KAGGLE_API
from crongle.utils import get_job_json_path, config, logger
from crongle import kernel_watcher

Path(config.crongle.job_queue_dir).mkdir(exist_ok=True, parents=True)

username = KAGGLE_API.get_config_value("username")


class KernelLauncher:
    """Responsible for submitting Kaggle kernel jobs and creating job metadata."""

    def __init__(self):
        pass

    def _create_job_object(
        self, kernel_name, script_path, output_folder, timeout, kernel_kwargs
    ) -> KernelJob:
        return KernelJob(
            kernel_name=kernel_name,
            script_path=script_path,
            output_folder=output_folder,
            timeout=timeout,
            kernel_kwargs=kernel_kwargs,
        )

    def _prepare_temp_folder(self, job: KernelJob, kernel_name: str) -> None:
        temp_script_path = Path(job.temp_folder).joinpath("main.py")
        shutil.copy(job.script_path, temp_script_path)

        metadata_path = Path(job.temp_folder).joinpath("kernel-metadata.json")
        for key, fixed_val in zip(
            ["language", "kernel_type", "code_file", "id"],
            ["python", "script", "main.py", f"{username}/{kernel_name}"],
        ):
            passed_val = job.kernel_kwargs.pop(key, None)
            if passed_val is not None and passed_val != fixed_val:
                logger.info(
                    f"over-riding user passed {key}: '{passed_val}' with '{fixed_val}'"
                )

        kernel_metadata = {
            "language": "python",
            "kernel_type": "script",
            "is_private": True,
            "code_file": "main.py",
            "id": f"{username}/{kernel_name}",
        }
        kernel_metadata.update(job.kernel_kwargs)
        with open(metadata_path, "w") as f:
            json.dump(kernel_metadata, f, indent=4)

    def _push_kernel(self, job: KernelJob) -> None:
        try:
            KAGGLE_API.kernels_push_cli(job.temp_folder, timeout=job.timeout)
        except Exception as e:
            shutil.rmtree(job.temp_folder, ignore_errors=True)
            raise e

    def _save_job_json(self, job: KernelJob) -> None:
        job_json_path = get_job_json_path(job.job_id)
        with open(job_json_path, "w") as f:
            json.dump(job.to_dict(), f, indent=2)

    def submit_job(
        self,
        kernel_name,
        script_path,
        output_folder,
        slack_bot_token: str = None,
        slack_channel_id: str = None,
        timeout=config.crongle.default_job_timeout,
        interval_amount: int = 5,
        interval_unit: str = kernel_watcher.CronInterval.minute,
        kernel_kwargs=None,
    ) -> str:
        kernel_kwargs = kernel_kwargs or {}
        job = self._create_job_object(
            kernel_name, script_path, output_folder, timeout, kernel_kwargs
        )
        self._prepare_temp_folder(job, kernel_name)
        self._push_kernel(job)
        self._save_job_json(job)
        kernel_watcher.initialize_polling_cron(
            job=job,
            interval_amount=interval_amount,
            interval_unit=interval_unit,
            slack_bot_token=slack_bot_token,
            slack_channel_id=slack_channel_id,
        )

        logger.info(f"Submitted job {job.job_id} for kernel '{kernel_name}'")
        return job.job_id
