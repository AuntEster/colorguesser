import discord
import mysql.connector
import re
import os
from datetime import datetime

BOT_TOKEN = os.environ["BOT_TOKEN"]
SCORE_CHANNEL = os.environ["general"]
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
            submitted_at DATETIME NOT NULL
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