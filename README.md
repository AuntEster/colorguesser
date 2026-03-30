# Colorle Discord Bot

A Discord bot that tracks and displays scores from [Colorle](https://colorguesser.com) for my friend group. 

---

## Features

- **Auto-detects scores** posted in a designated channel and saves them to a MySQL database
- **Duplicate prevention** — each user can only submit once per puzzle
- **Today's leaderboard** — ranked results for the current puzzle with score bars
- **All-time leaderboard** — ranked by average score across all puzzles
- **Monkey leaderboard** — ranked worst-to-best (banter)
- **Personal stats** — view your full submission history

---

## Commands

| Command | Description |
|---------|-------------|
| `!today` | Show the leaderboard for the latest puzzle |
| `!lb` | Show the all-time "most colorblind" leaderboard |
| `!stats` | Show your personal score history |
| `!help` | Show all available commands |

Scores are submitted automatically after user shares their scores in designated channel.

---

## Setup

### Prerequisites

- Python 3.8+
- MySQL database
- Discord bot token ([Discord Developer Portal](https://discord.com/developers/applications))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/colorle-discord-bot.git
   cd colorle-discord-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**

   The bot requires the following environment variables:

   | Variable | Description |
   |----------|-------------|
   | `BOT_TOKEN` | Your Discord bot token |
   | `SCORE_CHANNEL` | Name of the channel to watch for scores (e.g. `colorle`) |
   | `DB_HOST` | MySQL host |
   | `DB_PORT` | MySQL port (default: `3306`) |
   | `DB_NAME` | MySQL database name |
   | `DB_USER` | MySQL username |
   | `DB_PASSWORD` | MySQL password |

   You can set these in a `.env` file or export them in your shell.

4. **Run the bot**
   ```bash
   python discordbot.py
   ```

---

## Railway deployment

1. Push your code to a GitHub repository
2. Create a new project on [Railway](https://railway.com) and connect your repo
3. Set all required environment variables (7 total) in the Railway dashboard under **Variables** tab
    - Database connection info goes here
4. Railway will automatically detect the `Procfile` and run the bot as a worker

---

## Database

The bot automatically creates the required table on startup. The schema looks like this:

```sql
CREATE TABLE colorguesser_scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(30) NOT NULL,
    username VARCHAR(100) NOT NULL,
    puzzle_num INT NOT NULL,
    total_score INT NOT NULL,
    round_score VARCHAR(50) NOT NULL,
    submitted_at DATETIME NOT NULL,
    UNIQUE KEY unique_entry (user_id, puzzle_num)
);
```

---

## Score Format

The bot parses scores that match the Colorle share format, for example:

```
Colorle #1007 358/500
🟩🟩🟩🟩🟩🟩⬜⬜⬜⬜ 69/100
🟩🟩🟩⬜⬜⬜⬜⬜⬜⬜ 31/100
🟩🟩🟩🟩🟩🟩🟩🟩⬜⬜ 88/100
🟩🟩🟩🟩🟩🟩🟩🟩⬜⬜ 81/100
🟩🟩🟩🟩🟩🟩🟩🟩⬜⬜ 89/100
```

---