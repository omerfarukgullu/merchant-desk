# isyonetim

English | [Türkçe](README.tr.md)

A business management system for one-person companies and small teams that
runs entirely on your own machine. No account, no subscription, no internet
connection — all the data sits in a single SQLite file on your disk.

It starts empty. There are no sample customers or seeded products; you set
your business name and currency in Settings and work with your own data.

The interface is in Turkish. Everything else is configurable, so adapting it
to another language means translating the label dictionaries in
`isyonetim/dashboard/app.py` and the Typer help strings under `isyonetim/cli/`.

Three modules share one database:

- **Projects & tasks** — projects (or revenue streams), phases and tasks.
  Each task has a priority bucket (today / this week / backlog), a due date
  and a status.
- **Meetings & actions** — supplier, customer and accountant meetings, plus
  the action items that come out of them with an owner and a due date.
- **Sales & pricing** — products, sales channels, per-channel prices,
  competitor price tracking, a sales ledger, revenue and profit.

On top of that there is a calendar (task due dates, meetings and actions in
one month grid), an overview screen with today's digest and a 14-day revenue
trend, daily and weekly reports, CSV and Excel export, Windows notifications
for upcoming meetings, and one-command backups.

## Five ways to run it

All five share the same database and the same data layer:

1. **Dashboard** — `streamlit run isyonetim/dashboard/app.py`. Day-to-day
   work; reading as well as adding and editing.
2. **CLI** — `python -m isyonetim --help`. Fast entry and reporting.
3. **Desktop .exe** — `python build_exe.py`. For double-click use on a
   machine without Python.
4. **Network server** — `python run_server.py`. To reach the same data from
   a phone or laptop.
5. **Background reminder** — `python tray_app.py`. A separate, lightweight
   tray app that sends meeting notifications.

## Installation

Requires Python 3.10 or newer.

```bash
git clone <repository-url>
cd isyonetim

python -m venv .venv
.venv\Scripts\activate         # Windows
# source .venv/bin/activate    # macOS / Linux

pip install -r requirements.txt
```

The desktop `.exe` and the tray reminder are Windows-only and need extra
packages:

```bash
pip install -r requirements-windows.txt
```

Installing it as a package puts an `isyonetim` command on your PATH:

```bash
pip install .
isyonetim --help
```

## First run

```bash
streamlit run isyonetim/dashboard/app.py
```

The database is created on demand, so you do not have to run the CLI first.
Once the dashboard is up, open the **Ayarlar** (Settings) page and fill in
your business name, currency (TL, EUR, USD, £ …), default action owner and
reminder preferences. The dashboard title and every money label are driven by
those settings.

Settings are written to `data/settings.json` and never committed; the
template is in `settings.example.json`.

For server deployments or one-off runs you can override the settings file
with environment variables — `ISYONETIM_DB_PATH`, `ISYONETIM_BUSINESS_NAME`,
`ISYONETIM_CURRENCY`, `ISYONETIM_OWNER_NAME`,
`ISYONETIM_REMINDER_LEAD_MINUTES`, `ISYONETIM_DIGEST_AFTER_HOUR`,
`ISYONETIM_SERVER_PORT`. The full list with examples is in `.env.example`.
Precedence is environment variable, then `data/settings.json`, then the
built-in default.

To see the dashboard populated, you can load the generic sample data into a
separate file:

```bash
python scripts/seed_demo.py --db demo.db
export ISYONETIM_DB_PATH=$PWD/demo.db
streamlit run isyonetim/dashboard/app.py
```

The script never deletes anything on its own: if the target database already
has rows it warns and exits, and resetting needs `--reset` plus an explicit
confirmation.

## CLI usage

```bash
python -m isyonetim init                     # create the database / apply migrations
python -m isyonetim --help                   # all commands

python -m isyonetim project add "Product Sales" --goal "100 orders a month"
python -m isyonetim project add-phase "Product Sales" "Supplier talks"
python -m isyonetim project add-task "Product Sales" "Stock count" -p today
python -m isyonetim project set-task-status 1 completed

python -m isyonetim meeting add "Supplier call" --date 2026-11-03 --time 14:30 --type supplier
python -m isyonetim meeting add-action 1 "Request a quote" --owner "Manager" --due 2026-11-10
python -m isyonetim meeting list-actions --open-only

python -m isyonetim product add "Product A" --sku PROD-A --cost 450
python -m isyonetim channel add "Marketplace 1"
python -m isyonetim price add "Product A" 599 --channel "Marketplace 1"
python -m isyonetim price add "Product A" 579 --competitor "Rival Co"
python -m isyonetim price compare "Product A"
python -m isyonetim sale add "Product A" "Marketplace 1" --qty 2 --price 599 --date 2026-11-03

python -m isyonetim today                    # daily digest
python -m isyonetim weekly-summary           # weekly review across all three modules
python -m isyonetim project list-tasks --csv tasks.csv   # --csv on every list command
python -m isyonetim backup                   # timestamped backup
```

Projects, products and channels can be referenced by name or by id:
`project add-task 1 "Task"` and `project add-task "Product Sales" "Task"` do
the same thing.

To move the database, use the `--db <path>` option or the
`ISYONETIM_DB_PATH` environment variable. Run from a checkout, the default
location is `data/isyonetim.db`.

## Dashboard

It is not read-only: projects, tasks, meetings, action items, products,
prices and sales can all be added and updated there. It is completely
independent of the CLI.

Pages are in the sidebar: overview, calendar, projects & tasks, meetings &
actions, sales, settings. At the top of the sidebar there is a quick-add box —
whatever you type lands as a task for today in an auto-created "Inbox"
project, which you can re-file afterwards. Below it are the upcoming and
overdue items, and at the bottom the refresh and backup buttons.

The theme lives in `.streamlit/config.toml`, with light and dark modes set up
separately. Switch between Light / Dark / Use system setting from the ☰ menu
at the top right, under Settings → App theme.

## Desktop app (.exe)

Opens the dashboard in a native window without browser chrome.

```bash
python desktop_app.py        # quick test, no packaging
python build_exe.py          # build the .exe (takes a few minutes)
```

The output is `dist\IsYonetimSistemi\IsYonetimSistemi.exe`. It cannot be
moved on its own — the whole `dist\IsYonetimSistemi\` folder has to travel
with it. For a desktop shortcut, run `create_shortcut.bat`.

In `.exe` mode data and backups are kept under `%APPDATA%\isyonetim\data\`,
because the contents of `dist\` are replaced on every build. The icon comes
from `assets/app_icon.ico` (generated by `assets/generate_icon.py`).

## Remote access

The dashboard and the `.exe` are reachable only from this computer by
default. To use the same data from another device, leave this machine running
as a server and put both devices on a private
[Tailscale](https://tailscale.com) network; the data stays on this computer
and is never exposed to the internet.

1. Install Tailscale on both devices and sign in with the same account.
2. Start the server on this machine and leave it running: `run_server.bat`
3. From the other device, open the `100.x.x.x` address that `tailscale ip`
   reports, with the port: `http://100.x.x.x:8501`

**Security note:** there is no login or password on this page; access control
comes down entirely to who is on your Tailscale network (or Wi-Fi). Never
port-forward it to the internet. Binding to the network happens only in
`run_server.py` — a plain `streamlit run` or the `.exe` never exposes itself.

## Background reminder

A separate, lightweight tray application that checks the database every
minute even when the dashboard is closed.

When a meeting that has a time set is less than your configured lead time
away (15 minutes by default) it sends a notification, once per meeting.
Meetings without a time are never notified, they only show up on the
calendar. It also reports the day's task, meeting and overdue-action counts
in a single notification, on the first check after your configured hour
(08:00 by default).

```bash
python tray_app.py           # development
python build_tray_exe.py     # build the .exe
```

The output is `dist\IsYonetimHatirlatici\IsYonetimHatirlatici.exe`, much
smaller than the main app since it bundles neither streamlit nor pandas.
Right-clicking the tray icon gives you open panel, check now and quit. To
start it with Windows run `create_startup_shortcut.bat`; to remove it, delete
the shortcut from the `shell:startup` folder.

Notifications always appear in the Windows notification centre. Whether they
also pop up as a banner depends on your Focus Assist settings.

## Data and privacy

All the data is in `data/isyonetim.db` on your own disk. Nothing is sent
anywhere and Streamlit usage stats are off. `data/` and `backups/` are in
`.gitignore`, so your business data will not end up on GitHub by accident.

Back up with `python -m isyonetim backup` or the button in the dashboard;
copies land in `backups/` with a timestamp. The database is opened in WAL
mode, so the CLI, the dashboard and the reminder can use the same file at the
same time.

## Development

```bash
pip install -r requirements-dev.txt

python -m pytest            # tests
python -m ruff check .      # linter
```

The data layer takes a `sqlite3.Connection` from its caller, which lets the
tests run against an in-memory database without touching the disk. To change
the schema, add the next numbered `.sql` file under
`isyonetim/migrations/` — it is applied on startup and recorded in the
`schema_migrations` table.

## Project layout

```
isyonetim/
  config.py              data/backup paths (checkout, user dir, .exe)
  settings.py            business name, currency, reminder preferences
  core/db.py             connection + migration runner (WAL mode)
  migrations/            ordered .sql schema files
  models/                project/phase/task, meeting/action, sales data access
  cli/                   typer commands (independent of the dashboard)
  reports/               daily/weekly aggregation, CSV + Excel export
  dashboard/app.py       dashboard: read + write (independent of the CLI)
  dashboard/theme_css.py extra visual effects
tests/                   pytest tests (data layer, reports, settings, CLI)
scripts/seed_demo.py     optional generic sample data
assets/app_icon.ico      application icon
desktop_app.py           opens the dashboard in a pywebview window
build_exe.py             desktop .exe packaging
tray_app.py              system tray + reminder
build_tray_exe.py        packages the reminder as its own small .exe
run_server.py / .bat     serves the dashboard on the network
create_shortcut.*        desktop shortcut
create_startup_shortcut.*  adds the reminder to Windows startup
.streamlit/config.toml   theme + server defaults
settings.example.json    settings file template
```

## License

[MIT](LICENSE).
