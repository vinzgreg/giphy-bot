# giphy-bot

A Mastodon bot that brings Slack-style `/giphy` lookups to your instance. Mention the bot with a keyword and it privately DMs you GIF options to pick from — nothing spams your followers until you choose to post.

## Features

- Mention the bot with a keyword — search Giphy and receive options via DM
- `shuffle` — post a random GIF immediately (no selection loop)
- Navigate results with `next`, pick with `send N`, or mention the bot with a new keyword
- `block` — permanently ban a GIF from ever appearing again
- Local GIF library — drop your own GIFs in `local_gifs/`, they are fuzzy-matched and shown first when relevant, with a preview DM'd to you before you pick
- GIFs are uploaded as inline media attachments (play in the timeline, not just a link card)
- **Auto follow-back** — anyone who follows the bot gets followed back automatically (so DMs work in both directions)
- **Safety circuit breaker** — auto-pauses if the bot tries to post too many messages per minute, with admin DM notification
- Configurable logging level, polling interval, rate limit, and cool-down
- Runs as a Docker container with auto-restart

## How it works

1. You mention the bot with a keyword: `@giphybot excited dog`
2. The bot DMs you a numbered list of GIFs (local matches first, then Giphy results)
3. You reply:
   - `send 2` — posts GIF #2 as a standalone toot with inline playback, attributed to you at the end (`via @you`)
   - `next` — fetches the next batch of results
   - `block` — permanently bans the current GIF, shows the next one
   - `cancel` — ends the session
   - Mention the bot with new text — searches a new keyword

## Setup

### Prerequisites

- Docker and Docker Compose
- A bot account on your Mastodon instance
- A [Giphy API key](https://developers.giphy.com) (free tier)

### 1. Follow each other

For DMs to work, both accounts need to follow each other. The bot auto-follows back anyone who follows it (controlled by `AUTO_FOLLOW_BACK`), so you only need to:

- Log in as your main account and follow the bot

The bot will follow you back automatically once it's running.

### 2. Clone and configure

```bash
git clone https://github.com/vinzgreg/giphy-bot
cd giphy-bot
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Description |
|---|---|
| `MASTODON_ACCESS_TOKEN` | Bot account access token (Settings → Development → New Application) |
| `MASTODON_CLIENT_ID` | From the same application page |
| `MASTODON_CLIENT_SECRET` | From the same application page |
| `MASTODON_API_BASE_URL` | Your instance URL, e.g. `https://mastodon.example.com` |
| `BOT_ACCOUNT_ID` | Numeric ID of the bot account — run `curl "https://your.instance/api/v1/accounts/lookup?acct=yourbotname" -H "Authorization: Bearer YOUR_TOKEN"` and look for `"id"` |
| `GIPHY_API_KEY` | Your Giphy API key |
| `BOT_VISIBILITY` | Visibility of posted GIFs: `unlisted` (default), `public`, or `private` |

### 3. Add your own GIFs (optional)

Drop `.gif` (or `.webp`, `.mp4`) files into the `local_gifs/` folder. Name them descriptively — the filename is used for fuzzy matching:

```
local_gifs/
  excited-dog-jumping.gif
  party time confetti.gif
  facepalm oh no.gif
```

If `LOCAL_GIF_BASE_URL` is set in `.env`, GIFs are served from that URL. Otherwise the bot sends the local file path (useful for testing).

### 4. Run

```bash
docker compose up -d
docker compose logs -f
```

## Configuration reference

All settings live in `.env`. See `.env.example` for the full list with defaults.

### Bot behaviour

| Variable | Default | Description |
|---|---|---|
| `GIPHY_RESULT_COUNT` | `3` | GIFs per batch |
| `GIPHY_RATING` | `g` | Giphy content rating (`g`, `pg`, `pg-13`, `r`) |
| `SESSION_TTL_SECONDS` | `600` | How long an inactive session stays open (seconds) |
| `RATE_LIMIT_PER_USER_SECONDS` | `30` | Minimum gap between requests per user |
| `FUZZY_MATCH_THRESHOLD` | `65` | Fuzzy match sensitivity for local GIFs (0–100, lower = fuzzier) |
| `AUTO_FOLLOW_BACK` | `true` | If `true`, the bot follows back anyone who follows it (so DMs work both ways automatically) |

### Logging & polling

| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `POLL_INTERVAL_SECONDS` | `10` | How often to check for new mentions |

### Safety circuit breaker

If the bot would post more than `MAX_MESSAGES_PER_MINUTE` messages in any rolling 60-second window, the breaker opens. All outgoing messages are dropped for `COOLDOWN_SECONDS`, and the admin (`ADMIN_ACCT`) gets a DM. After cool-down, the bot resumes and DMs the admin again.

| Variable | Default | Description |
|---|---|---|
| `MAX_MESSAGES_PER_MINUTE` | `6` | Hard cap on outgoing messages per rolling minute |
| `COOLDOWN_SECONDS` | `300` | How long to pause after the breaker trips |
| `ADMIN_ACCT` | _(empty)_ | Your handle (without `@`) to receive breaker alerts. Leave blank to disable admin notifications. |

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

## License

MIT — see [LICENSE](LICENSE).
