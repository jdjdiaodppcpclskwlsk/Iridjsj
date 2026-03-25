import sqlite3
from typing import Optional, Dict, Any, List

GAME_DB = "game.db"

def get_conn():
    conn = sqlite3.connect(GAME_DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_game_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS game_players (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                titan_type TEXT,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                upgrade_points INTEGER DEFAULT 0,
                hp INTEGER DEFAULT 0,
                max_hp INTEGER DEFAULT 0,
                defense INTEGER DEFAULT 0,
                strength INTEGER DEFAULT 0,
                agility INTEGER DEFAULT 0,
                kills INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS active_battles (
                battle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                opponent_id INTEGER,
                battle_type TEXT NOT NULL,
                player_hp INTEGER NOT NULL,
                opponent_hp INTEGER NOT NULL,
                turn INTEGER DEFAULT 0,
                attack_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                rank TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS duel_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenger_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

# ── TITAN BASE STATS ─────────────────────────────────────────────────────────
TITAN_BASE_STATS = {
    "attacking": {"hp": 100, "defense": 20, "strength": 50, "agility": 15},
    "armored":   {"hp": 150, "defense": 50, "strength": 30, "agility": 5},
}
TITAN_UPGRADE_PER_POINT = {
    "attacking": {"hp": 5,  "defense": 5,  "strength": 10, "agility": 5},
    "armored":   {"hp": 10, "defense": 10, "strength": 5,  "agility": 2},
}
SKILL_UNLOCK_LEVELS = {
    "kick":    3,
    "side_strike": 5,
    "suplex":  8,
    "choke":   12,
    "titan_scream": 15,
}
ALL_SKILLS = ["punch", "uppercut", "dodge", "kick", "side_strike", "suplex", "choke", "titan_scream"]
DEFAULT_SKILLS = ["punch", "uppercut", "dodge"]

# ── EXP / LEVEL ───────────────────────────────────────────────────────────────
def exp_for_level(level: int) -> int:
    return level * 100

def add_exp(user_id: int, amount: int) -> Dict[str, Any]:
    player = get_player(user_id)
    if not player:
        return {}
    exp = player["exp"] + amount
    level = player["level"]
    upgrade_points = player["upgrade_points"]
    leveled_up = False
    while exp >= exp_for_level(level):
        exp -= exp_for_level(level)
        level += 1
        upgrade_points += 1
        leveled_up = True
    with get_conn() as conn:
        conn.execute(
            "UPDATE game_players SET exp=?, level=?, upgrade_points=? WHERE user_id=?",
            (exp, level, upgrade_points, user_id)
        )
    return {"new_exp": exp, "new_level": level, "leveled_up": leveled_up, "upgrade_points": upgrade_points}

# ── PLAYER CRUD ───────────────────────────────────────────────────────────────
def get_player(user_id: int) -> Optional[Dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM game_players WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None

def create_player(user_id: int, username: str, first_name: str, titan_type: str) -> Dict:
    base = TITAN_BASE_STATS[titan_type]
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO game_players
            (user_id, username, first_name, titan_type, level, exp, upgrade_points,
             hp, max_hp, defense, strength, agility, kills)
            VALUES (?,?,?,?,1,0,0,?,?,?,?,?,0)
        """, (user_id, username, first_name, titan_type,
              base["hp"], base["hp"], base["defense"], base["strength"], base["agility"]))
    return get_player(user_id)

def update_stat(user_id: int, stat: str, new_value: int):
    allowed = {"hp", "max_hp", "defense", "strength", "agility", "upgrade_points"}
    if stat not in allowed:
        return
    with get_conn() as conn:
        conn.execute(f"UPDATE game_players SET {stat}=? WHERE user_id=?", (new_value, user_id))

def spend_upgrade_points(user_id: int, stat: str, points: int) -> Dict[str, Any]:
    player = get_player(user_id)
    if not player or player["upgrade_points"] < points:
        return {"ok": False, "reason": "not_enough_points"}
    mult = TITAN_UPGRADE_PER_POINT[player["titan_type"]]
    col_map = {"Здоровье": "max_hp", "Защита": "defense", "Сила": "strength", "Ловкость": "agility"}
    col = col_map.get(stat)
    if not col:
        return {"ok": False, "reason": "invalid_stat"}
    gain = mult[col.replace("max_hp", "hp")] * points
    old_val = player[col]
    new_val = old_val + gain
    new_pts = player["upgrade_points"] - points
    with get_conn() as conn:
        conn.execute(f"UPDATE game_players SET {col}=?, upgrade_points=? WHERE user_id=?",
                     (new_val, new_pts, user_id))
        if col == "max_hp":
            new_hp = min(player["hp"] + gain, new_val)
            conn.execute("UPDATE game_players SET hp=? WHERE user_id=?", (new_hp, user_id))
    return {"ok": True, "old_val": old_val, "new_val": new_val, "new_pts": new_pts}

def get_unlocked_skills(player: Dict) -> List[str]:
    lvl = player["level"]
    skills = list(DEFAULT_SKILLS)
    for skill, req_lvl in SKILL_UNLOCK_LEVELS.items():
        if lvl >= req_lvl:
            skills.append(skill)
    return skills

# ── BATTLES ───────────────────────────────────────────────────────────────────
def create_battle(player_id: int, player_hp: int, opponent_hp: int,
                  battle_type: str, rank: str = None, opponent_id: int = None) -> int:
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO active_battles
            (player_id, opponent_id, battle_type, player_hp, opponent_hp, rank)
            VALUES (?,?,?,?,?,?)
        """, (player_id, opponent_id, battle_type, player_hp, opponent_hp, rank))
        return cur.lastrowid

def get_battle(battle_id: int) -> Optional[Dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM active_battles WHERE battle_id=?", (battle_id,)).fetchone()
        return dict(row) if row else None

def get_player_active_battle(player_id: int) -> Optional[Dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM active_battles WHERE player_id=? AND is_active=1 ORDER BY created_at DESC LIMIT 1",
            (player_id,)
        ).fetchone()
        return dict(row) if row else None

def update_battle(battle_id: int, **kwargs):
    if not kwargs:
        return
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [battle_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE active_battles SET {sets} WHERE battle_id=?", vals)

def end_battle(battle_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE active_battles SET is_active=0 WHERE battle_id=?", (battle_id,))

# ── DUEL REQUESTS ─────────────────────────────────────────────────────────────
def create_duel_request(challenger_id: int, target_id: int) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO duel_requests (challenger_id, target_id, status) VALUES (?,?,'pending')",
            (challenger_id, target_id)
        )
        return cur.lastrowid

def get_duel_request(duel_id: int) -> Optional[Dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM duel_requests WHERE id=?", (duel_id,)).fetchone()
        return dict(row) if row else None

def update_duel_status(duel_id: int, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE duel_requests SET status=? WHERE id=?", (status, duel_id))

# ── ENEMY GENERATION ─────────────────────────────────────────────────────────
import random

RANK_ENEMY_RANGES = {
    "E": {"hp": (50, 100),  "defense": (5, 15),   "strength": (10, 25),  "agility": (3, 8)},
    "D": {"hp": (100, 180), "defense": (15, 30),  "strength": (25, 45),  "agility": (8, 15)},
    "C": {"hp": (180, 280), "defense": (30, 50),  "strength": (45, 70),  "agility": (15, 25)},
    "B": {"hp": (280, 400), "defense": (50, 80),  "strength": (70, 100), "agility": (25, 40)},
    "A": {"hp": (400, 550), "defense": (80, 120), "strength": (100, 140),"agility": (40, 60)},
    "S": {"hp": (550, 750), "defense": (120, 180),"strength": (140, 200),"agility": (60, 80)},
}

def generate_enemy(rank: str) -> Dict:
    r = RANK_ENEMY_RANGES.get(rank, RANK_ENEMY_RANGES["E"])
    hp = random.randint(*r["hp"])
    return {
        "hp": hp,
        "max_hp": hp,
        "defense": random.randint(*r["defense"]),
        "strength": random.randint(*r["strength"]),
        "agility": random.randint(*r["agility"]),
    }

def calc_damage(attacker_str: int, defender_def: int, skill: str = "punch") -> int:
    skill_multipliers = {
        "punch": 1.0,
        "uppercut": 1.2,
        "dodge": 0.0,
        "kick": 1.4,
        "side_strike": 1.1,
        "suplex": 1.6,
        "choke": 1.3,
        "titan_scream": 1.8,
        "counter": 1.5,
    }
    mult = skill_multipliers.get(skill, 1.0)
    raw = max(1, attacker_str - defender_def // 2)
    dmg = int(raw * mult * random.uniform(0.85, 1.15))
    return max(1, dmg)

def dodge_chance(agility: int) -> float:
    return min(0.60, agility / 150.0 + 0.05)
