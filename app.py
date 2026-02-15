import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import random
import json
import time
import pandas as pd
import plotly.express as px

# --- 1. 設定とアセット定義 ---

# ★正しいスプレッドシートID
SHEET_ID = "1FvqLUrkR_YYk_azwI35rGr6_Y2swgUp1mawfJget5KU"

# ドット絵風アセット
ASSETS = {
    "BG_FOREST": "https://images.unsplash.com/photo-1511497584788-876760111969?w=800&q=80",
    "BG_CAVE": "https://images.unsplash.com/photo-1516934024742-b461fba47600?w=800&q=80",
    "BG_SEA": "https://images.unsplash.com/photo-1494253109108-2e30c049369b?w=800&q=80",
    "BG_VOLCANO": "https://images.unsplash.com/photo-1541103554737-fe33e243b45c?w=800&q=80",
    "BG_CASTLE": "https://images.unsplash.com/photo-1533154683836-84ea7a0bc310?w=800&q=80",
    
    "HERO_1": "https://placehold.co/100x100/555/FFF?text=👕+Novice",
    "HERO_2": "https://placehold.co/100x100/333/0F0?text=🛡️+Soldier",
    "HERO_3": "https://placehold.co/100x100/000/FFD700?text=⚔️+Hero",
    "HERO_4": "https://placehold.co/100x100/222/F0F?text=👑+Legend",
    
    "CHEST_CLOSED": "https://placehold.co/300x200/444/DAA520?text=📦+CHEST",
}

# モンスターDB (名前を以前のデータと一致させるため絵文字付きに戻しました)
MONSTER_DB = {
    "UR": [
        {"name": "🐲 伝説のドラゴン", "img": "https://placehold.co/200x200/800/F00?text=🐲+DRAGON", "skill": {"type": "all_bonus", "val": 0.2}},
        {"name": "👼 大天使", "img": "https://placehold.co/200x200/FFD700/FFF?text=👼+ANGEL", "skill": {"type": "task_bonus", "target": "ウォーキング", "val": 0.5}}
    ],
    "SSR": [
        {"name": "🤖 未来ロボ", "img": "https://placehold.co/200x200/2C3E50/0FF?text=🤖+MECHA", "skill": {"type": "task_bonus", "target": "コード書き", "val": 0.3}},
        {"name": "🦁 百獣の王", "img": "https://placehold.co/200x200/DAA520/FFF?text=🦁+LION", "skill": {"type": "task_bonus", "target": "筋トレ", "val": 0.3}}
    ],
    "SR": [
        {"name": "🐺 シルバーウルフ", "img": "https://placehold.co/200x200/AAA/FFF?text=🐺+WOLF", "skill": {"type": "task_bonus", "target": "ウォーキング", "val": 0.15}},
        {"name": "🦅 グリフォン", "img": "https://placehold.co/200x200/B8860B/FFF?text=🦅+GRIFFIN", "skill": {"type": "task_bonus", "target": "筋トレ", "val": 0.15}}
    ],
    "R": [
        {"name": "🐗 ワイルドボア", "img": "https://placehold.co/200x200/8B4513/FFF?text=🐗+BOAR", "skill": {"type": "task_bonus", "target": "筋トレ", "val": 0.05}},
        {"name": "🕷️ 巨大グモ", "img": "https://placehold.co/200x200/000/0F0?text=🕷️+SPIDER", "skill": {"type": "task_bonus", "target": "コード書き", "val": 0.05}},
        {"name": "🦇 コウモリ", "img": "https://placehold.co/200x200/4B0082/FFF?text=🦇+BAT", "skill": {"type": "task_bonus", "target": "ウォーキング", "val": 0.05}}
    ],
    "N": [
        {"name": "💧 スライム", "img": "https://placehold.co/200x200/3498DB/FFF?text=💧+SLIME", "skill": {"type": "task_bonus", "target": "掃除", "val": 0.05}},
        {"name": "🍄 きのこ", "img": "https://placehold.co/200x200/E74C3C/FFF?text=🍄+MUSHROOM", "skill": {"type": "task_bonus", "target": "勉強", "val": 0.05}}
    ]
}

# ジョブ定義
JOBS = {
    "novice": {"name": "冒険者(無職)", "desc": "ボーナスなし", "bonus": {}},
    "warrior": {"name": "戦士", "desc": "筋トレ報酬 UP", "bonus": {"筋トレ": 1.2}},
    "mage": {"name": "魔導士", "desc": "勉強報酬 UP", "bonus": {"勉強": 1.2}},
    "thief": {"name": "盗賊", "desc": "掃除報酬 UP", "bonus": {"掃除": 1.2}},
    "jester": {"name": "遊び人", "desc": "基本0.9倍 / 稀に5倍", "bonus": {"all": 0.9}}
}

# ミッション定義
MISSIONS = {
    "daily": [
        {"id": "d_login", "desc": "ログインする", "target": 1, "reward_pt": 50},
        {"id": "d_task3", "desc": "タスクを3回完了", "target": 3, "reward_pt": 100},
        {"id": "d_gacha", "desc": "ガチャを引く", "target": 1, "reward_pt": 50}
    ],
    "weekly": [
        {"id": "w_task20", "desc": "週間タスク20回", "target": 20, "reward_item": "gacha_ticket", "amount": 1},
        {"id": "w_boss", "desc": "ボスに1000ダメ", "target": 1000, "reward_item": "sr_ticket", "amount": 1}
    ]
}

# --- 2. システム関数 ---

def get_database():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

def load_data():
    try:
        sheet = get_database()
        val = sheet.acell('A1').value
        data = json.loads(val) if val else {}
    except:
        data = {}
    
    defaults = {
        "points": 0, "total_points": 0, "xp": 0, "level": 1,
        "job": "novice", "last_job_change": "",
        "dungeon": {"floor": 1, "status": "exploring"},
        "pet": {"active": None},
        "monster_levels": {},
        "items": {"gacha_ticket": 0, "sr_ticket": 0, "ssr_ticket": 0},
        "raid_boss": {"hp": 5000, "max_hp": 5000, "name": "魔王・怠惰", "defeat_count": 0},
        "mission_progress": {"daily": {}, "weekly": {}, "last_login": "", "last_week": 0, "combo": 0},
        "task_counts": {}, "point_history": {}, "shop_counts": {}, "active_buffs": {},
        "daily_gacha_done": False
    }
    
    for k, v in defaults.items():
        if k not in data: data[k] = v
        
    # 不足キーの補完 (エラー防止)
    if "combo" not in data["mission_progress"]: data["mission_progress"]["combo"] = 0
    if "status" not in data["dungeon"]: data["dungeon"]["status"] = "exploring"
    if "active" not in data["pet"]: data["pet"]["active"] = None
    if "shop_counts" not in data: data["shop_counts"] = {}
    
    return data

def save_data(data):
    try:
        st.toast("💾 Saving...", icon="💾")
        sheet = get_database()
        sheet.update_acell('A1', json.dumps(data, ensure_ascii=False))
    except Exception as e:
        pass # エラー表示を抑制して没入感を優先

def update_mission(data, action_type, val=1):
    today = str(datetime.date.today())
    week_num = datetime.date.today().isocalendar()[1]
    
    if data["mission_progress"]["last_login"] != today:
        data["mission_progress"]["daily"] = {}
        data["mission_progress"]["last_login"] = today
        data["daily_gacha_done"] = False # ガチャリセット
        
    if data["mission_progress"]["last_week"] != week_num:
        data["mission_progress"]["weekly"] = {}
        data["mission_progress"]["last_week"] = week_num

    prog = data["mission_progress"]
    prog["daily"][action_type] = prog["daily"].get(action_type, 0) + val
    prog["weekly"][action_type] = prog["weekly"].get(action_type, 0) + val
    return data

def calculate_bonus_rate(data, task_name):
    rate = 1.0
    # 1. ジョブ
    job_info = JOBS.get(data["job"], JOBS["novice"])
    if data["job"] == "jester":
        if random.random() < 0.1:
            st.toast("🎰 ラッキーパンチ！報酬5倍！", icon="🃏")
            return 5.0
        else: rate = 0.9
    else:
        for key, bonus in job_info["bonus"].items():
            if key in task_name: rate += (bonus - 1.0)
    # 2. コンボ
    combo = data["mission_progress"].get("combo", 0)
    rate += min(combo * 0.01, 0.2)
    # 3. 負傷
    now = datetime.datetime.now().isoformat()
    if "injury" in data["active_buffs"]:
        if now < data["active_buffs"]["injury"]: rate *= 0.5
    # 4. ポーション
    if "potion" in data["active_buffs"]:
        if now < data["active_buffs"]["potion"]: rate += 1.0

    return rate

# --- 3. アプリ設定とCSS ---

st.set_page_config(page_title="Life Quest: Pixel", page_icon="⚔️", layout="wide")

# CSS (PCでの視認性向上)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');
    
    /* ベース */
    .stApp {
        background-color: #1a1a2e;
        color: #f0f0f0; 
        font-family: 'Courier New', monospace;
    }
    
    /* カード類 */
    .pixel-card {
        background-color: #16213e;
        border: 2px solid #4a5568;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 10px;
        color: #fff; /* 文字色を白に強制 */
    }
    
    /* ボタン */
    .stButton>button {
        background-color: #0f3460;
        color: #fff;
        border: 2px solid #e94560;
        border-radius: 5px;
        font-weight: bold;
    }
    
    /* 入力フォームの文字色対策 */
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: #16213e;
        color: #fff;
    }
    .stSelectbox label {
        color: #fff !important;
    }
</style>
""", unsafe_allow_html=True)

# データロード
if 'data' not in st.session_state:
    st.session_state.data = load_data()
data = st.session_state.data

# 定期処理
today_str = str(datetime.date.today())
update_mission(data, "d_login", 1) # ログイン処理

if data["mission_progress"]["last_login"] != today_str:
    yesterday = str(datetime.date.today() - datetime.timedelta(days=1))
    if data["mission_progress"]["last_login"] == yesterday:
        data["mission_progress"]["combo"] = data["mission_progress"].get("combo", 0) + 1
    else:
        data["mission_progress"]["combo"] = 1
    data["mission_progress"]["last_login"] = today_str
    data["daily_gacha_done"] = False
    data["points"] += 100
    save_data(data)
    st.toast(f"🎁 Login Bonus! Combo: {data['mission_progress']['combo']}日目", icon="🔥")

# --- 4. サイドバー ---
with st.sidebar:
    lv = data["level"]
    hero_img = ASSETS["HERO_1"]
    if lv >= 10: hero_img = ASSETS["HERO_2"]
    if lv >= 30: hero_img = ASSETS["HERO_3"]
    
    col_av, col_st = st.columns([1, 2])
    with col_av: st.image(hero_img, width=80)
    with col_st:
        st.markdown(f"**Lv.{lv} 勇者**")
        st.caption(f"Job: {JOBS.get(data['job'], {}).get('name')}")
    
    st.markdown(f"""
    <div class="pixel-card">
        💎 Pt: <b>{data['points']}</b><br>
        🎫 チケ: <b>{data['items'].get('gacha_ticket', 0)}</b><br>
        🔥 コンボ: <b>{data['mission_progress'].get('combo', 0)}日</b>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("🦸 Job Change")
    if data["last_job_change"] != today_str:
        new_job = st.selectbox("職業選択", list(JOBS.keys()), format_func=lambda x: JOBS[x]["name"])
        if st.button("転職する"):
            data["job"] = new_job
            data["last_job_change"] = today_str
            save_data(data)
            st.rerun()
    else:
        st.info(f"現在の職業: {JOBS[data['job']]['name']}")

# --- 5. メイン画面 ---

# 背景
fl = data["dungeon"]["floor"]
bg_url = ASSETS["BG_FOREST"]
if 11 <= fl <= 20: bg_url = ASSETS["BG_CAVE"]
elif 21 <= fl <= 30: bg_url = ASSETS["BG_SEA"]
elif 31 <= fl <= 40: bg_url = ASSETS["BG_VOLCANO"]
elif fl >= 41: bg_url = ASSETS["BG_CASTLE"]

st.image(bg_url, use_column_width=True, caption=f"Floor {fl} - Area: {['森','洞窟','海','火山','城'][min((fl-1)//10, 4)]}")

# ペット
if data["pet"]["active"]:
    pet_name = data["pet"]["active"]
    st.info(f"🐶 {pet_name} が一緒についてきている！")

# タブ (ショップとミッションを復活)
t1, t2, t3, t4, t5, t6 = st.tabs(["⚔️ 冒険", "🏪 ショップ", "📅 ミッション", "🎰 ガチャ", "📊 記録", "📖 図鑑"])

# --- T1: 冒険 ---
with t1:
    if fl % 10 == 0 and data["dungeon"]["status"] != "boss_cleared":
        st.error("⚠️ BOSS BATTLE!!")
        c1, c2 = st.columns(2)
        with c1: st.markdown(f"**勇者** (パワー: {10 + data['level']})")
        with c2: st.markdown(f"**門番** (パワー: {10 + fl})")
        
        if st.button("勝負する！ (ダイス)"):
            h_roll = random.randint(1, 6) + 10 + data["level"]
            e_roll = random.randint(1, 6) + 10 + fl
            st.write(f"勇者: {h_roll} vs 門番: {e_roll}")
            if h_roll >= e_roll:
                st.success("勝利！")
                data["dungeon"]["floor"] += 1
                data["dungeon"]["status"] = "exploring"
                data["items"]["gacha_ticket"] += 1
                save_data(data)
                st.rerun()
            else:
                st.error("敗北... キャンプに戻ります")
                data["dungeon"]["floor"] = max(1, (fl // 5) * 5)
                save_data(data)
                st.rerun()
    else:
        # タスク (ウォーキング復活)
        c1, c2 = st.columns(2)
        tasks = {"🧹 掃除": 30, "📚 勉強": 50, "💻 仕事": 80, "💪 筋トレ": 40, "🚶 ウォーキング": 100}
        
        for i, (t, base) in enumerate(tasks.items()):
            rate = calculate_bonus_rate(data, t)
            final_pt = int(base * rate)
            with c1 if i%2==0 else c2:
                if st.button(f"{t} (+{final_pt}pt)", key=f"t_{i}"):
                    data["points"] += final_pt
                    data["total_points"] += final_pt
                    data["xp"] += 10
                    data["task_counts"][t] = data["task_counts"].get(t, 0) + 1
                    
                    today = str(datetime.date.today())
                    data["point_history"][today] = data["point_history"].get(today, 0) + final_pt
                    
                    data["dungeon"]["floor"] += 1
                    if data["dungeon"]["floor"] % 10 == 0: data["dungeon"]["status"] = "boss"
                    
                    if data["xp"] >= data["level"] * 100:
                        data["level"] += 1
                        data["xp"] = 0
                        st.toast("Level Up!")
                    
                    if data["raid_boss"]["hp"] > 0: data["raid_boss"]["hp"] -= final_pt
                    
                    update_mission(data, "d_task3", 1)
                    update_mission(data, "w_task20", 1)
                    save_data(data)
                    st.rerun()

# --- T2: ショップ (復活) ---
with t2:
    st.subheader("🏪 雑貨屋")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**🎫 ガチャチケ (150pt)**")
        if st.button("購入", disabled=data["points"]<150):
            data["points"] -= 150
            data["items"]["gacha_ticket"] += 1
            save_data(data)
            st.success("購入！")
            st.rerun()
    with c2:
        st.write("**🧪 ポーション (300pt)**")
        if st.button("購入＆使用", disabled=data["points"]<300):
            data["points"] -= 300
            end = datetime.datetime.now() + datetime.timedelta(hours=1)
            data["active_buffs"]["potion"] = end.isoformat()
            save_data(data)
            st.success("やる気UP！")
            st.rerun()
            
    st.markdown("---")
    st.write("**🎫 レア確定チケット**")
    if st.button("SR確定 (1000pt)", disabled=data["points"]<1000):
        data["points"] -= 1000
        data["items"]["sr_ticket"] += 1
        save_data(data)
        st.rerun()

# --- T3: ミッション (復活) ---
with t3:
    st.subheader("📅 ミッション")
    st.write("▼ デイリー")
    for m in MISSIONS["daily"]:
        prog = data["mission_progress"]["daily"].get(m["id"], 0)
        claimed = data["mission_progress"]["daily"].get(f"{m['id']}_claimed", False)
        st.progress(min(prog/m["target"], 1.0), text=f"{m['desc']} ({prog}/{m['target']})")
        if prog >= m["target"] and not claimed:
            if st.button("受取", key=m["id"]):
                data["points"] += m["reward_pt"]
                data["mission_progress"]["daily"][f"{m['id']}_claimed"] = True
                save_data(data)
                st.rerun()

# --- T4: ガチャ (無料分復活) ---
with t4:
    st.subheader("🎰 召喚の間")
    c1, c2 = st.columns(2)
    with c1:
        # 無料ガチャ
        done = data.get("daily_gacha_done", False)
        st.write("▼ **無料 (1日1回)**")
        if st.button("無料召喚！", disabled=done):
            data["daily_gacha_done"] = True
            rarity = random.choices(["N", "R"], weights=[80, 20])[0]
            m = random.choice(MONSTER_DB[rarity])
            st.image(m["img"], width=150)
            st.write(f"{rarity} {m['name']}")
            data["monster_levels"][m["name"]] = data["monster_levels"].get(m["name"], 0) + 1
            update_mission(data, "d_gacha", 1)
            save_data(data)
            st.balloons()
            
    with c2:
        # チケット
        n = data["items"].get("gacha_ticket", 0)
        st.write(f"▼ **チケット (残り{n}枚)**")
        if st.button("チケット召喚", disabled=n==0):
            data["items"]["gacha_ticket"] -= 1
            rarity = random.choices(["N", "R", "SR", "SSR", "UR"], weights=[50, 30, 15, 4, 1])[0]
            m = random.choice(MONSTER_DB[rarity])
            st.image(m["img"], width=150)
            st.write(f"{rarity} {m['name']}")
            data["monster_levels"][m["name"]] = data["monster_levels"].get(m["name"], 0) + 1
            update_mission(data, "d_gacha", 1)
            save_data(data)
            st.balloons()

# --- T5: 記録 (円グラフ復活) ---
with t5:
    st.subheader("📊 記録")
    # 棒グラフ
    if data["point_history"]:
        df = pd.DataFrame(list(data["point_history"].items()), columns=["Date", "Points"])
        fig1 = px.bar(df, x="Date", y="Points", title="日別ポイント")
        st.plotly_chart(fig1, use_container_width=True)
        
    # 円グラフ (復活)
    if data["task_counts"]:
        df2 = pd.DataFrame(list(data["task_counts"].items()), columns=["Task", "Count"])
        fig2 = px.pie(df2, values='Count', names='Task', title="タスク比率")
        st.plotly_chart(fig2, use_container_width=True)

# --- T6: 図鑑 (選択機能復活) ---
with t6:
    st.subheader("📖 図鑑 & 相棒選択")
    st.caption("ボタンを押して相棒にする")
    cols = st.columns(3)
    idx = 0
    for r in ["UR", "SSR", "SR", "R", "N"]:
        for m in MONSTER_DB[r]:
            # 名前が一致するかチェック (旧データ対応)
            if m["name"] in data["monster_levels"]:
                with cols[idx % 3]:
                    st.image(m["img"], width=80)
                    if st.button(f"{m['name']}", key=f"p_{m['name']}"):
                        data["pet"]["active"] = m["name"]
                        save_data(data)
                        st.success(f"{m['name']} を相棒にしました！")
                        st.rerun()
                idx += 1
