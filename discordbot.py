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
    return mysql.connector.connect(host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)

def init_db():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS colorguesser_scores (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(30) NOT NULL,
            username VARCHAR(100) NOT NULL,
            puzzle_num INT NOT NULL,
            total_score INT NOT NULL,
            round_score INT NOT NULL,
            submitted_at DATETIME NOT NULL,
            UNIQUE KEY unique_entry (user_id, puzzle_num)
        )
    """)
    db.commit()
    cursor.close()
    db.close()
    
def save_score(user_id, username, puzzle_num, total_score, round_score):
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("""
            INSERT INTO colorguesser_scores 
            (user_id, username, puzzle_num, total_score, round_score, submitted_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (str(user_id), username, puzzle_num, total_score, ",".join(map(str, round_score)), datetime.now()))
        db.commit()
        return True
    except mysql.connector.IntegrityError:
        return False
    finally:
        cursor.close()
        db.close()
        
def get_leaderboard_today(puzzle_num):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT username, total_score, round_score
        FROM colorguesser_scores 
        WHERE puzzle_num = %s 
        ORDER BY total_score DESC
    """, (puzzle_num,))
    results = cursor.fetchall()
    cursor.close()
    db.close()
    return results

def get_leaderboard_alltime():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT username, 
            ROUND(AVG(total_score), 1) AS avg_score,
            MAX(total_score) AS best_score,
            COUNT(*) AS games_played
        FROM colorguesser_scores 
        GROUP BY user_id 
        ORDER BY avg_score DESC
    """)
    results = cursor.fetchall()
    cursor.close()
    db.close()
    return results

def get_user_stats(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT puzzle_num, total_score, round_score, submitted_at
        FROM colorguesser_scores 
        WHERE user_id = %s 
        ORDER BY puzzle_num DESC
    """, (str(user_id),))
    results = cursor.fetchall()
    cursor.close()
    db.close()
    return results

def parse_scores(content):
    header = re.search(r'Colorle\s+#(\d+)\s+(\d+)/500', content)
    if not header:
        return None
    
    puzzle_num = int(header.group(1))
    total_score = int(header.group(2))
    
    round_scores = [int(m) for m in re.findall(r'(\d+)/100', content)]
    
    return puzzle_num, total_score, round_scores

def score_bar(score):
    filled = round(score / 10)
    return "✅" * filled + "⬜" * (10 - filled) # replace with emoji 

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    init_db()
    print(f"logged in as {client.user} watching {SCORE_CHANNEL}")
    
@client.event
async def on_message(message):
    if message.author.bot:
        return 
    
    if message.content.startswith("!lb"):
        rows = get_leaderboard_alltime()
        if not rows:
            await message.channel.send("No scores yet!")
            return
        
        lines = ["**Worst Colorblind Monkey**"]
        medals = ["🥇", "🥈", "🥉"]
        for i, (username, avg, best, games) in enumerate(rows):
            medal = medals[i] if i < 3 else f"`{i+1}.`"
            lines.append(f"{medal} **{username}** - Avg: {avg}, Best: {best}, Game{'s' if games != 1 else ''}: {games}")
            
        await message.channel.send("\n".join(lines))
        return
    
    if message.content.startswith("!today"):
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT MAX(puzzle_num) FROM colorguesser_scores")
        result = cursor.fetchone()
        cursor.close()
        db.close()
        
        if not result or result[0] is None:
            await message.channel.send("No scores yet!")
            return
        
        puzzle_num = result[0]
        rows = get_leaderboard_today(puzzle_num)
        
        lines = [f"**Colorle #{puzzle_num} Leaderboard**"]
        medals = ["🥇", "🥈", "🥉"]
        
        for i, (username, total_score, round_score) in enumerate(rows):
            medal = medals[i] if i < 3 else f"`{i+1}.`"
            round_list = round_score.split(",") if round_score else []
            bars = " ".join(score_bar(int(s)) for s in round_list) if round_list else ""
            lines.append(f"{medal} **{username}** {total_score}/500")
            if bars:
                lines.append(f"    {bars}")
                
        await message.channel.send("\n".join(lines))
        return
    
    if message.content.startswith("!stats"):
        rows = get_user_stats(message.author.id)
        if not rows:
            await message.channel.send("You haven't submitted any scores yet!")
            return
        
        lines = [f"**{message.author.name}'s Colorle Stats**"]
        for puzzle_num, total_score, round_score, submitted_at in rows:
            round_list = round_score.split(",") if round_score else []
            bars = " ".join(score_bar(int(s)) for s in round_list) if round_list else ""
            lines.append(f"**Puzzle #{puzzle_num}** - {total_score}/500 on {submitted_at.strftime('%Y-%m-%d')}")
            if bars:
                lines.append(f"    {bars}")
        
        await message.channel.send("\n".join(lines))
        return
    
    if message.content.startswith("!help"):
        help_text = (
            "**Colorle Bot Commands:**\n"
            "`!lb` - Show all-time leaderboard\n"
            "`!today` - Show today's puzzle leaderboard\n"
            "`!stats` - Show your personal stats\n"
            "`!help` - Show this help message\n\n"
        )
        await message.channel.send(help_text)
        return
    
    if message.channel.name != SCORE_CHANNEL:
        return
    
    parsed = parse_scores(message.content)
    if not parsed:
        return
    
    puzzle_num, total_score, round_scores = parsed
    username = message.author.display_name
    is_new = save_score(message.author.id, username, puzzle_num, total_score, round_scores)
    
    if is_new:
        await message.add_reaction("✅")
        rows = get_leaderboard_today(puzzle_num)
        rank = next((i + 1 for i, (u, s, _) in enumerate(rows) if s == total_score and u == username), None)
        total_players = len(rows)
        rank_str = f"#{rank} of {total_players}" if rank else ""
    else:
        await message.add_reaction("❌")
        await message.reply("You have already submitted a score for this puzzle!", mention_author=False)
        
client.run(BOT_TOKEN)