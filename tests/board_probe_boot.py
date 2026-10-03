"""Boot a THROWAWAY in-process Polari server for the board probes (brd-wire).

managerObject registers its core source files relative to os.getcwd() (objectTreeManagerDecorators: mainDirPath =
os.getcwd()), so the boot must happen with the FRAMEWORK as the working directory — but the probes keep their artifacts
(work dirs, the bridge project, logs) in the throwaway directory they were started from. This helper:

  * points the sqlite DB at <throwaway>/data/ (DATABASE_PATH) — never the framework's own ./data;
  * puts a guard file there so the legacy-data-dir migration (polariDBmanagement.legacy_data_dir) sees a destination
    that "already holds databases" and NEVER copies or renames the framework's ./data/*_DB.db;
  * changes into the framework for the boot only, then back.

Call boot_env() before importing the framework (config is read from the environment), then boot().
"""
import os

GUARD = 'probe-guard_DB.db'   # matches the migration's *_DB.db glob; not the managerObject_DB.db the boot looks for


def boot_env(here=None):
    here = os.path.abspath(here or os.getcwd())
    data = os.path.join(here, 'data')
    os.makedirs(data, exist_ok=True)
    open(os.path.join(data, GUARD), 'a').close()
    os.environ['DATABASE_PATH'] = os.path.join(data, 'polari.db')
    os.environ.setdefault('POLARI_DB_BACKEND', 'sqlite')
    return here


def boot(framework, here=None):
    here = boot_env(here)
    from objectTreeManagerDecorators import managerObject
    os.chdir(framework)
    try:
        return managerObject(hasServer=True, hasDB=True)
    finally:
        os.chdir(here)
