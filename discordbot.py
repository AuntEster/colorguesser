import discord
import mysql.connector
import re
import os
from datetime import datetime

BOT_TOKEN = os.environ["BOT_TOKEN"]
SCORE_CHANNEL = os.environ["SCORE_CHANNEL"]
DB_HOST = os.environ["DB_HOST"]
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_NAME = os.environ["DB_NAME"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]

def get_db():
    return mysql.connector.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASSWORD
    )

def init_db():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id VARCHAR(30) NOT NULL PRIMARY KEY,
            username VARCHAR(100) NOT NULL,
            updated_at DATETIME NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(30) NOT NULL,
            puzzle_num SMALLINT NOT NULL,
            total_score SMALLINT NOT NULL,
            round_scores VARCHAR(50) NOT NULL,
            submitted_at DATETIME NOT NULL,
            UNIQUE KEY uq_user_puzzle (user_id, puzzle_num),
            CONSTRAINT fk_scores_user FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    db.commit()
    cursor.close()
    db.close()

def save_score(user_id, username, puzzle_num, total_score, round_scores):
    db = get_db()
    cursor = db.cursor()
    try:
        # update username so it stays current 
        cursor.execute("""
            INSERT INTO users (user_id, username, updated_at)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE username = VALUES(username), updated_at = VALUES(updated_at)
        """, (str(user_id), username, datetime.now()))

        cursor.execute("""
            INSERT INTO scores (user_id, puzzle_num, total_score, round_scores, submitted_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (str(user_id), puzzle_num, total_score, ",".join(map(str, round_scores)), datetime.now()))

        db.commit()
        return True
    except mysql.connector.IntegrityError:
        db.rollback()
        return False
    finally:
        cursor.close()
        db.close()

def get_leaderboard_today(puzzle_num):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT u.username, s.total_score, s.round_scores
        FROM scores s
        JOIN users u ON s.user_id = u.user_id
        WHERE s.puzzle_num = %s
        ORDER BY s.total_score DESC
    """, (puzzle_num,))
    results = cursor.fetchall()
    cursor.close()
    db.close()
    return results

def get_leaderboard_monkey():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT u.username,
               ROUND(AVG(s.total_score), 1) AS avg_score,
               MAX(s.total_score) AS best_score,
               COUNT(*) AS games_played
        FROM scores s
        JOIN users u ON s.user_id = u.user_id
        GROUP BY s.user_id
        ORDER BY avg_score ASC
    """)
    results = cursor.fetchall()
    cursor.close()
    db.close()
    return results

def get_user_stats(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT s.puzzle_num, s.total_score, s.round_scores, s.submitted_at
        FROM scores s
        WHERE s.user_id = %s
        ORDER BY s.puzzle_num DESC
    """, (str(user_id),))
    results = cursor.fetchall()
    cursor.close()
    db.close()
    return results

def parse_scores(content):
    header = re.search(r'Colorle\s+#(\d+)\s+(\d+)/500', content)
    if not header:
        return None

    puzzle_num  = int(header.group(1))
    total_score = int(header.group(2))
    round_scores = [int(m) for m in re.findall(r'(\d+)/100', content)]

    return puzzle_num, total_score, round_scores

def score_bar(score):
    filled = round(score / 10)
    return "🟩" * filled + "⬜" * (10 - filled)

# discord client setup

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    init_db()
    print(f"Logged in as {client.user} | watching #{SCORE_CHANNEL}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    # !lb command
    if message.content.startswith("!lb"):
        rows = get_leaderboard_monkey()
        if not rows:
            await message.channel.send("No scores yet!")
            return

        lines  = ["**Most Colorblind Monkey**"]
        medals = ["🥇", "🥈", "🥉"]
        for i, (username, avg, best, games) in enumerate(rows):
            medal = medals[i] if i < 3 else f"`{i+1}.`"
            lines.append(
                f"{medal} **{username}** — Avg: {avg}, Best: {best}, "
                f"Game{'s' if games != 1 else ''}: {games}"
            )
        await message.channel.send("\n".join(lines))
        return

    # !today command
    if message.content.startswith("!today"):
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT MAX(puzzle_num) FROM scores")
        result = cursor.fetchone()
        cursor.close()
        db.close()

        if not result or result[0] is None:
            await message.channel.send("No scores yet!")
            return

        puzzle_num = result[0]
        rows = get_leaderboard_today(puzzle_num)

        lines  = [f"**Colorle #{puzzle_num} Leaderboard**"]
        medals = ["🥇", "🥈", "🥉"]
        for i, (username, total_score, round_scores) in enumerate(rows):
            medal = medals[i] if i < 3 else f"`{i+1}.`"
            lines.append(f"{medal} **{username}** {total_score}/500")

        await message.channel.send("\n".join(lines))
        return

    # !stats command
    if message.content.startswith("!stats"):
        rows = get_user_stats(message.author.id)
        if not rows:
            await message.channel.send("You haven't submitted any scores yet!")
            return

        lines = [f"**{message.author.display_name}'s Colorle Stats**"]
        for puzzle_num, total_score, round_scores, submitted_at in rows:
            lines.append(
                f"**Puzzle #{puzzle_num}** — {total_score}/500 on "
                f"{submitted_at.strftime('%Y-%m-%d')}"
            )

        await message.channel.send("\n".join(lines))
        return

    # !help command
    if message.content.startswith("!help"):
        await message.channel.send(
            "**Colorle Bot Commands:**\n"
            "`!today` — Today's puzzle leaderboard\n"
            "`!lb`    — All-time most-colorblind leaderboard\n"
            "`!stats` — Your personal score history\n"
            "`!help`  — Show this message"
        )
        return

    # score submission 
    if message.channel.name != SCORE_CHANNEL:
        return

    parsed = parse_scores(message.content)
    if not parsed:
        return

    puzzle_num, total_score, round_scores = parsed
    is_new = save_score(
        message.author.id, message.author.display_name,
        puzzle_num, total_score, round_scores
    )

    if is_new:
        await message.add_reaction("✅")
    else:
        await message.add_reaction("❌")

client.run(BOT_TOKEN)