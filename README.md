# C003_stock

A clear, bilingual market-event dashboard with a rolling **three-calendar-month** window. Built for **GitHub Pages + GitHub Actions**, like C002_drug_board, with a new interface and independent source collectors.

## What is ready

- The default **three-month overview** shows all intersecting months together, including the partial first and last months. Colored dates open that day's events; the timeline remains available.
- **Watchlist** starts with BA, ADSK, AA and UNH. Company-name RSS searches refresh daily and include only headlines published in the trailing 72 hours. Dated three-month assessments are editorial and do not silently change when headlines refresh.

- An event timeline and monthly calendar, with search, sector categories and high-impact filters.
- English / 中文. Event explanations and scenario analysis are included in both languages. Publisher headlines retain their original language.
- Separate scheduled / tentative dates and uncertain watch themes. No made-up probabilities, price targets or consensus estimates.
- Event details: why it matters, what to watch, potentially affected markets, source links and the last verification date.
- Device-local bookmarks and `.ics` calendar export. Exported entries are all-day reminders; the details show release times when available.
- A no-API-key updater, a GitHub deployment workflow, parser/date tests and a Windows launcher.

## Open locally

Unzip the project. On Windows with Python installed, double-click `start.bat`.

Or run from this folder:

```bash
python server.py --open
```

Open **http://localhost:8003**. Keep the terminal open while using the site. Do not open index.html directly: the browser needs a local server to read the event JSON.

Local viewing does not activate unattended updates. The daily job runs on GitHub after the repository is published and Actions is enabled; your PC can then be switched off.

## Publish on GitHub

1. Create a repository named **C003_stock**. A public repository supports GitHub Pages on the free GitHub plan. Do not put passwords, brokerage details or private holdings in this repository.
2. Upload the **contents** of this project to the repository root, on branch **main**. Include `.github/workflows/daily-update.yml`; do not upload the ZIP itself. A local checkout or GitHub Desktop preserves the `.github` folder reliably.
3. Open repository **Settings → Pages → Build and deployment → Source → GitHub Actions**.
4. Open **Settings → Actions → General → Workflow permissions** and allow this repository's workflow to write its refreshed JSON. If organisation policies or branch rules prohibit bot commits, resolve that repository policy rather than force-pushing or weakening unrelated protections.
5. Open **Actions → Update and deploy C003_stock → Run workflow**. Wait for **build** and **deploy** to complete. The `github-pages` deployment provides the live URL.

The workflow tests the project, refreshes data, commits `data/events.json`, builds only public website files and deploys those same files. It does **not** depend on a bot's commit triggering a second workflow.

### Daily timing

The included schedule is **12:17 UTC every day**: **7:17 AM New York time in winter / 8:17 AM in summer**. GitHub can delay scheduled jobs. Change the `cron` line in `.github/workflows/daily-update.yml` to adjust timing. Scheduled workflows run from the default branch; this project uses `main`.

GitHub may disable scheduled workflows in a public repository after 60 days without repository activity. Check the Actions page if updates stop. The dashboard shows the last attempt and flags data older than 48 hours; the configured schedule alone is not proof of a fresh update.

Official GitHub references:

- https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule

## What updates automatically

| Coverage | Daily behaviour |
|---|---|
| Federal Reserve | Reads published meeting dates; preserves the calendar's tentative designation. Excludes separately labelled strategy meetings. |
| BLS | Reads CPI and employment release dates, keeping the reference period distinct from the release date. |
| BEA | Reads current- and next-year PCE and national GDP schedules. |
| ECB / BOJ | Reads policy decision dates using the source's local calendar. |
| Curated policy / industry events | Rechecks their cited source for the configured date. Changed or inaccessible pages are flagged for editorial review. |
| Supported company announcements | Broadcom's official RSS is scanned for explicitly dated future earnings announcements. Additional company feeds can be added to the updater. |
| Uncertain watch themes | Recent related publisher headlines are discovered through Google News RSS. Headlines are context and never become confirmed future dates automatically. |
| Watchlist companies | Queries in `data/watchlist.json` discover up to 25 recent headlines per company. Exact normalized titles and repeated links are deduplicated. Both the updater and browser enforce the 72-hour publication cutoff, even after a failed refresh. |
| Rolling window | The browser uses **America/New_York** and advances from today through the same date three months later, clamping month-end dates correctly. |

### Important coverage limits

This is a maintained event calendar, not an exhaustive global event-discovery service. **New policy deadlines, new companies and new watch themes may need editorial additions.** The daily job does not use an LLM or paid market-data API and does not automatically rewrite the editorial scenarios. It refreshes official schedules, supported announcements, source status and related news.

Re-reading an old source cannot establish that no later announcement superseded it. Confirm policy deadlines against the latest enacted law before relying on them. A missing record is flagged for review rather than falsely declared cancelled. Add explicit cancellations or replacement dates to the curated data when confirmed.

At the first live test, seven official calendar collectors worked. The Oracle page rejected automated retrieval, and the CRS policy deadline is in a PDF that this dependency-free updater does not parse. Those records retain their prior research date and display a review notice. This is intentional failure handling, not a successful re-verification.

## Maintain the project

```bash
# Refresh schedules and news now
python scripts/update_events.py

# Refresh schedules only
python scripts/update_events.py --no-news

# Validate current data
python scripts/update_events.py --validate-only

# Tests (Node 22+ and Python 3.12+; no npm packages required)
npm test

# Build dist/ for hosting
python scripts/build.py
```

`--no-news` retains existing news and its previous verification state; it does not claim a fresh headline check.

To add or change a one-off event, edit **data/curated.json**. Include a stable ID, ISO date, English/Chinese explanation, source URL, certainty and source-matching pattern. For an event superseded or cancelled by an official announcement, set `lifecycle` to `superseded` or `cancelled`; it disappears from the forward calendar. To update watch-theme wording or add collectors, edit **scripts/catalog.py** and **scripts/update_events.py**.

To add a stock, append an entry to **data/watchlist.json** with `ticker`, `name`, `nameZh`, company-name `aliases`, a focused `query`, and `research: null`. The next daily run includes it without interface changes. A ticker alone is not a safe news query (for example, AA is ambiguous). Research may be added with its original `asOf`, `reviewBy`, bilingual rationale and linked sources. Never advance `asOf` merely because the daily job ran. UNH initially tracks headlines without an investment assessment. Existing assessments are marked for review after their checkpoint or after seven days.

RSS coverage is not comprehensive; publisher timestamps can describe new coverage of an older event. Different headlines about the same underlying story may remain. A successful empty feed means only that no matching records were retrieved. This app does not fetch full articles, generate automatic recommendations or provide live quotes. Company-specific calendar entries still require source verification; no future earnings date is inferred from a news headline.

Source failures preserve prior records and verification times. Successful changes to a recurring event's date replace its previous date and appear in **Sources & updates**. All data writes are atomic.

## Project files

| File | Purpose |
|---|---|
| `index.html`, `styles.css`, `app.js` | Dashboard interface |
| `core.js` | Timezone, three-month filtering and calendar-export logic |
| `data/events.json` | Latest published snapshot; updated by the daily job |
| `data/curated.json` | Editable one-off event and source catalog |
| `data/watchlist.json` | Extensible stock list and separately dated editorial assessments |
| `scripts/stock_news.py` | Strict 72-hour company-news filtering and basic deduplication |
| `scripts/catalog.py` | Bilingual explanations and monitored themes |
| `scripts/update_events.py` | Primary-source calendar collectors and news refresh |
| `scripts/build.py` | Allowlisted public output; excludes source scripts and workflows |
| `.github/workflows/daily-update.yml` | Combined daily update and Pages deployment |
| `tests/` | Date-boundary, calendar-export, parsing and reconciliation checks |
| `server.py`, `start.bat` | Local preview |

Bookmarks and language preferences are stored only in the current browser. No brokerage connection, trading function, analytics or account is required. Google Fonts is optional; system fonts are used if unavailable.

## 中文快速开始

1. 解压 **C003_stock.zip**，有Python的Windows电脑可双击 **start.bat** 预览。
2. GitHub中新建 **C003_stock** 仓库，把项目内容放在仓库根目录，保留 **.github/workflows** 文件夹。
3. **Settings → Pages → Source** 选择 **GitHub Actions**。
4. 在 **Actions** 中运行 **Update and deploy C003_stock**，成功后即可打开部署网址。
5. 发布后由GitHub每日更新，电脑无需开机。默认冬令时美东早上7:17、夏令时8:17，GitHub可能延迟运行。

日历自动滚动三个月；不确定事件单独展示。无法重新核实的日期保留旧数据并提示。每日会刷新官方日程和相关新闻，但新增政策事件、公司覆盖及情景分析仍可能需要编辑维护。
