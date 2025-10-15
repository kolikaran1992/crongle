from crongle.utils import config, logger
import os
from pathlib import Path
import shutil


_kaggle_json_dir = Path(config.crongle.kaggle_json_dir)


def _copy_file(src: str, dst: str):
    Path(dst).mkdir(exist_ok=True, parents=True)
    shutil.copy2(src, dst)
    logger.info(f'copied file: "{src}" to "{dst}"')


def _set_kaggle_permissions():
    _path = _kaggle_json_dir.joinpath("kaggle.json").as_posix()
    os.chmod(_path, 0o600)
    logger.info(f'permission changed for "{_path}"')


try:
    from kaggle.api.kaggle_api_extended import KaggleApi

    KAGGLE_API = KaggleApi()
    KAGGLE_API.authenticate()
except:
    _copy_file(config.kaggle.kaggle_secret_json, _kaggle_json_dir.as_posix())
    _set_kaggle_permissions()
    from kaggle.api.kaggle_api_extended import KaggleApi

    KAGGLE_API = KaggleApi()
    KAGGLE_API.authenticate()

KAGGLE_USER_NAME = KAGGLE_API.get_config_value("username")
