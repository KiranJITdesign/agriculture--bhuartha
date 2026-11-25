"""Local development settings."""
import glob
import os
import sys

from .base import *  # noqa: F403

DEBUG = True
CORS_ALLOW_ALL_ORIGINS = True

if os.environ.get("USE_SPATIALITE", "1") == "1" and not os.environ.get("POSTGRES_HOST"):
    if os.name == "nt":
        _libs = glob.glob(os.path.join(sys.prefix, "Lib", "site-packages", "pyogrio.libs"))
        _proj_data = os.path.join(sys.prefix, "Lib", "site-packages", "pyogrio", "proj_data")
        if os.path.isdir(_proj_data):
            os.environ["PROJ_DATA"] = _proj_data
            os.environ["PROJ_LIB"] = _proj_data
        _mod_spatialite = os.path.join(sys.prefix, "Library", "bin", "mod_spatialite.dll")
        if os.path.exists(_mod_spatialite):
            _bin_dir = os.path.dirname(_mod_spatialite)
            os.environ["PATH"] = _bin_dir + os.pathsep + os.environ.get("PATH", "")
            globals()["SPATIALITE_LIBRARY_PATH"] = _mod_spatialite
        if _libs:
            _lib_dir = _libs[0]
            os.environ["PATH"] = _lib_dir + os.pathsep + os.environ.get("PATH", "")
            for _env_key, _pattern in (
                ("GDAL_LIBRARY_PATH", "gdal-*.dll"),
                ("GEOS_LIBRARY_PATH", "geos_c-*.dll"),
            ):
                _matches = glob.glob(os.path.join(_lib_dir, _pattern))
                if _matches:
                    globals()[_env_key] = _matches[0]
    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.spatialite",
            "NAME": str(BASE_DIR / "db.sqlite3"),  # noqa: F405
        }
    }
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
