# giphy-bot

A Mastodon bot that brings Slack-style `/giphy` lookups to your instance. Mention the bot with `/giphy <keyword>` and it privately DMs you GIF options to pick from — nothing spams your followers until you choose to post.

## Features

- Mention the bot with a keyword — search Giphy and receive options via DM
- `shuffle` — post a random GIF immediately (no selection loop)
- Navigate results with `next`, pick with `send N`, or mention the bot with a new keyword
- `block` — permanently ban a GIF from ever appearing again
- Local GIF library — drop your own GIFs in `local_gifs/`, they are fuzzy-matched and shown first when relevant
- Runs as a Docker container with auto-restart

## How it works

1. You mention the bot with a keyword: `@giphybot excited dog`
2. The bot DMs you a numbered list of GIFs (local matches first, then Giphy results)
3. You reply:
   - `send 2` — posts GIF #2 as an unlisted reply to your original toot
   - `next` — fetches the next batch of results
   - `block` — permanently bans the current GIF, shows the next one
   - `cancel` — ends the session
   - Mention the bot with new text — searches a new keyword

## Setup

### Prerequisites

- Docker and Docker Compose
- A bot account on your Mastodon instance
- A [Giphy API key](https://developers.giphy.com) (free tier)

### 1. Clone and configure

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

### 2. Add your own GIFs (optional)

Drop `.gif` (or `.webp`, `.mp4`) files into the `local_gifs/` folder. Name them descriptively — the filename is used for fuzzy matching:

```
local_gifs/
  excited-dog-jumping.gif
  party time confetti.gif
  facepalm oh no.gif
```

If `LOCAL_GIF_BASE_URL` is set in `.env`, GIFs are served from that URL. Otherwise the bot sends the local file path (useful for testing).

### 3. Run

```bash
docker compose up -d
docker compose logs -f
```

## Configuration reference

All settings live in `.env`. See `.env.example` for the full list with defaults.

| Variable | Default | Description |
|---|---|---|
| `GIPHY_RESULT_COUNT` | `3` | GIFs per batch |
| `GIPHY_RATING` | `g` | Giphy content rating (`g`, `pg`, `pg-13`, `r`) |
| `SESSION_TTL_SECONDS` | `600` | How long an inactive session stays open (seconds) |
| `RATE_LIMIT_PER_USER_SECONDS` | `30` | Minimum gap between `/giphy` triggers per user |
| `FUZZY_MATCH_THRESHOLD` | `65` | Fuzzy match sensitivity for local GIFs (0–100, lower = fuzzier) |

## License

MIT — see [LICENSE](LICENSE).
