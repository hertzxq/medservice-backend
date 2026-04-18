# scripts/ — manual parser runs

Batch scripts for running review parsers against a specific branch. Under the hood they call `POST /api/v1/parsing/trigger-by-branch` on the running backend — reviews are saved directly to the main DB and appear in the UI (dedup by `branch_id + platform + reviewer_name + published_at`).

## Setup

1. Backend is running: `poetry run uvicorn app.main:app --reload` (port 8000).
2. Copy the config:
   ```bat
   copy scripts\.env.example scripts\.env
   ```
3. In `scripts/.env` set `ADMIN_USERNAME` and `ADMIN_PASSWORD` (defaults match seed credentials `admin`/`12345678`).

`.env` is already covered by the root `.gitignore`.

## parse.bat — run parsing

```bat
scripts\parse.bat <branch_id> [<platform> ...]
```

Platforms: `yandex_maps`, `google_maps`, `2gis`, `prodoctorov`. If omitted — all four are parsed.

Examples:

```bat
scripts\parse.bat 1                              REM all platforms for branch 1
scripts\parse.bat 1 yandex_maps                  REM Yandex only
scripts\parse.bat 2 yandex_maps 2gis             REM Yandex + 2GIS
```

The script:
1. Logs in via `/auth/login` (verifies `isSuperuser`).
2. POSTs to `/parsing/trigger-by-branch` with `branchId` and platform list.
3. Polls `/parsing/status` every 3 seconds, prints progress.
4. Outputs a JSON summary at the end (`last_result`): how many reviews were parsed/inserted per platform.

If a platform URL is not yet saved for the branch, the backend will find the org by name and city and store the URL in `branch.platform_urls` — the next run takes the fast path.

## parse-status.bat — current status

```bat
scripts\parse-status.bat
```

Prints `status` (`idle | running | completed | error`), `last_run_at`, `progress`, and the last result.

## Limitations

- The backend holds parsing state in one process's memory (see `_parsing_state` in `app/api/v1/parsing.py`). Parallel runs are not possible — a second `trigger-by-branch` returns 409.
- Scripts require Windows + PowerShell 5.1+ (standard on Win10/11).
