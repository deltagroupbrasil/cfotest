Test Suite

- Location: `DeltaCFOAgent/tests`
- Framework: `unittest` (stdlib)

Quick Run

- PowerShell: `./DeltaCFOAgent/run_tests.ps1`
- CMD: `DeltaCFOAgent\run_tests.bat`
- Direct: `python -m unittest discover -s DeltaCFOAgent\tests -p "test_*.py" -v`

Notes

- Requires Python 3.9+ accessible via `py` or `python` in PATH.
- Tests are self-contained and avoid external network or services.
- Current coverage targets `database_utils.py` end-to-end behaviors:
  - Connection lifecycle, CRUD, batching
  - Integrity and vacuum
  - Lock-file cleanup (`fix_database_locks`)
  - Singleton manager `get_database_manager`

