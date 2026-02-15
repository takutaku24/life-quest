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
    # 背景 (エリア)
    "BG_FOREST": "https://images.unsplash.com/photo-1448375240586-dfd8f3793371?auto=format&fit=crop&q=80&w=800", # 森
    "BG_CAVE": "https://images.unsplash.com/photo-1504333638930-c8787321eee0?auto=format&fit=crop&q=80&w=800",   # 洞窟
    "BG_SEA": "https://images.unsplash.com/photo-1505118380757-91f5f5632de0?auto=format&fit=crop&q=80&w=800",    # 海
    "BG_VOLCANO": "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?auto=format&fit=crop&q=80&w=800", # 火山
    "BG_CASTLE": "https://images.unsplash.com/photo-1599696803248-2b0e668c6a5e?auto=format&fit=crop&q=80&w=800",  # 城
    
    # 主人公 (レベル別)
    "HERO_1": "https://placehold.co/100x100/555/FFF?text=👕+Novice",
    "HERO_2": "https://placehold.co/100x100/333/0F0?text=🛡️+Soldier",
    "HERO_3": "https://placehold.co/100x100/000/FFD700?text=⚔️+Hero",
    "HERO_4": "https://placehold.co/100x100/222/F0F?text=👑+Legend",

    # ガチャ演出
    "CHEST_CLOSED": "https://placehold.co/300x200/444/DAA520?text=📦+CHEST",
    "CHEST_OPEN": "https://placehold.co/300x200/444/FFF?text=✨+OPEN!!",

    # その他アイコン
    "ICON_SWORD": "⚔️", "ICON_SHIELD": "🛡️", "ICON_POTION": "🧪", "ICON_TICKET": "🎫"
}

# モンスターDB (ドット絵風テキスト画像)
MONSTER_DB = {
    "UR": [
        {"name": "伝説のドラゴン", "img": "https://placehold.co/200x200/800/F00?text=🐲+DRAGON"},
        {"name": "大天使", "img": "https://placehold.co/200x200/FFD700/FFF?text=👼+ANGEL"}
    ],
    "SSR": [
        {"name": "魔導ロボ", "img": "https://placehold.co/200x200/2C3E50/0FF?text=🤖+MECHA"},
        {"name": "キングライオン", "img": "https://placehold.co/200x200/DAA520/FFF?text=🦁+LION"}
    ],
    "SR": [
        {"name": "シルバーウルフ", "img": "https://placehold.co/200x200/AAA/FFF?text=🐺+WOLF"},
        {"name": "グリフォン", "img": "https://placehold.co/200x200/B8860B/FFF?text=🦅+GRIFFIN"}
    ],
    "R": [
        {"name": "ワイルドボア", "img": "https://placehold.co/200x200/8B4513/FFF?text=🐗+BOAR"},
        {"name": "ジャイアントスパイダー", "img": "https://placehold.co/200x200/000/0F0?text=🕷️+SPIDER"}
    ],
    "N": [
        {"name": "スライム", "img": "https://placehold.co/200x200/3498DB/FFF?text=💧+SLIME"},
        {"name": "おばけキノコ", "img": "https://placehold.co/200x200/E74C3C/FFF?text=🍄+MUSHROOM"}
    ]
}

# ジョブ定義
JOBS = {
    "novice": {"name": "冒険者(無職)", "desc": "ボーナスなし", "bonus": {}},
    "warrior": {"name": "戦士", "desc": "筋トレ報酬 UP", "bonus": {"筋トレ": 1.2}},
    "mage": {"name": "魔導士", "desc": "勉強報酬 UP", "bonus": {"勉強": 1.2}},
    "thief": {"name": "盗賊", "desc": "掃除報酬 UP", "bonus": {"掃除": 1.2}},
    "jester": {"name": "遊び人", "desc": "基本0.9倍 / 稀に5倍", "bonus": {"all": 0.9}} # 特殊処理
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
    
    # 初期データ構造の保証 (トップレベル)
    defaults = {
        "points": 0, "total_points": 0, "xp": 0, "level": 1,
        "job": "novice", "last_job_change": "",
        "dungeon": {"floor": 1, "max_floor": 1, "status": "exploring", "history": []},
        "pet": {"active": None, "friendship": 0},
        "monster_levels": {},
        "items": {"gacha_ticket": 0, "sr_ticket": 0},
        "raid_boss": {"hp": 5000, "max_hp": 5000, "name": "魔王・怠惰", "defeat_count": 0, "reset_date": ""},
        "mission_progress": {"daily": {}, "weekly": {}, "last_login": "", "last_week": 0, "combo": 0},
        "task_counts": {}, "point_history": {}, "shop_counts": {},
        "active_buffs": {}
    }
    
    for k, v in defaults.items():
        if k not in data: data[k] = v
        
    # ★重要修正: ネストされたデータの不足キーを補完する処理
    # (ここがないと古いデータ読み込み時にエラーになる)
    if "combo" not in data["mission_progress"]:
        data["mission_progress"]["combo"] = 0
    if "status" not in data["dungeon"]:
        data["dungeon"]["status"] = "exploring"
    if "active" not in data["pet"]:
        data["pet"]["active"] = None

    return data

def save_data(data):
    try:
        # オートセーブ演出
        st.toast("💾 Saving...", icon="💾")
        sheet = get_database()
        sheet.update_acell('A1', json.dumps(data, ensure_ascii=False))
    except Exception as e:
        st.error(f"Save Error: {e}")

# 週次リセット (月曜更新)
def check_weekly_reset(data):
    today = datetime.date.today()
    current_week = today.isocalendar()[1]
    
    if data["mission_progress"].get("last_week", 0) != current_week:
        # 月曜リセット処理
        data["mission_progress"]["weekly"] = {}
        data["mission_progress"]["last_week"] = current_week
        data["shop_counts"] = {k:v for k,v in data["shop_counts"].items() if "weekly" not in k}
        
        # ボス復活
        data["raid_boss"] = {
            "hp": 5000 + (data["level"] * 100), 
            "max_hp": 5000 + (data["level"] * 100),
            "name": random.choice(["魔王・怠惰", "魔王・傲慢", "魔王・憤怒"]),
            "defeat_count": data["raid_boss"].get("defeat_count", 0),
            "reset_date": str(today)
        }
        st.toast("📅 新しい週が始まりました！ボスとミッションが更新されました。", icon="🔄")
        save_data(data)

# ボーナス計算 (ジョブ + ペット + コンボ)
def calculate_bonus_rate(data, task_name):
    rate = 1.0
    
    # 1. ジョブ補正
    job_info = JOBS.get(data["job"], JOBS["novice"])
    if data["job"] == "jester":
        # 遊び人: 10%で5倍、それ以外0.9倍
        if random.random() < 0.1:
            st.toast("🎰 遊び人のラッキーパンチ！報酬5倍！", icon="🃏")
            return 5.0
        else:
            rate = 0.9
    else:
        for key, bonus in job_info["bonus"].items():
            if key in task_name: rate += (bonus - 1.0)

    # 2. コンボ補正 (最大+20%)
    combo = data["mission_progress"].get("combo", 0)
    rate += min(combo * 0.01, 0.2)
    
    # 3. 負傷デバフ
    now = datetime.datetime.now().isoformat()
    if "injury" in data["active_buffs"]:
        if now < data["active_buffs"]["injury"]:
            rate *= 0.5 # 怪我で半減
    
    return rate

# --- 3. アプリ設定とCSS ---

st.set_page_config(page_title="Life Quest: Pixel", page_icon="⚔️", layout="wide")

# ダークモード & ドット絵風フォントのCSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');
    
    /* 全体設定 */
    .stApp {
        background-color: #1a1a2e;
        color: #e0e0e0;
        font-family: 'Courier New', Courier, monospace; 
    }
    
    /* ステータスカード */
    .pixel-card {
        background-color: #16213e;
        border: 4px solid #4a5568;
        padding: 15px;
        border-radius: 4px; /* 角を丸くしない */
        box-shadow: 4px 4px 0px #000;
        margin-bottom: 10px;
    }
    
    /* ボタンのゲーム化 */
    .stButton>button {
        background-color: #0f3460;
        color: #fff;
        border: 2px solid #e94560;
        border-radius: 0px;
        box-shadow: 3px 3px 0px #000;
        font-weight: bold;
        transition: all 0.1s;
    }
    .stButton>button:active {
        transform: translate(2px, 2px);
        box-shadow: 1px 1px 0px #000;
    }
    
    /* ボスHPバー */
    .boss-container {
        border: 4px solid #fff;
        background: #333;
        height: 30px;
        position: relative;
    }
    .boss-fill {
        background: #e94560;
        height: 100%;
        transition: width 0.3s;
    }
</style>
""", unsafe_allow_html=True)

# データロード
if 'data' not in st.session_state:
    st.session_state.data = load_data()
data = st.session_state.data

# 定期処理
check_weekly_reset(data)
today_str = str(datetime.date.today())

# ログインボーナス & コンボ処理
if data["mission_progress"]["last_login"] != today_str:
    # 昨日の日付
    yesterday = str(datetime.date.today() - datetime.timedelta(days=1))
    if data["mission_progress"]["last_login"] == yesterday:
        data["mission_progress"]["combo"] = data["mission_progress"].get("combo", 0) + 1 # 連続ログイン
    else:
        data["mission_progress"]["combo"] = 1 # 途切れた
        
    data["mission_progress"]["last_login"] = today_str
    data["points"] += 100
    save_data(data)
    st.toast(f"🎁 Login Bonus! Combo: {data['mission_progress']['combo']}日目", icon="🔥")

# --- 4. サイドバー (ステータス & メニュー) ---
with st.sidebar:
    # 主人公立ち絵
    lv = data["level"]
    hero_img = ASSETS["HERO_1"]
    if lv >= 10: hero_img = ASSETS["HERO_2"]
    if lv >= 30: hero_img = ASSETS["HERO_3"]
    if lv >= 50: hero_img = ASSETS["HERO_4"]
    
    col_av, col_st = st.columns([1, 2])
    with col_av:
        st.image(hero_img, width=80)
    with col_st:
        st.markdown(f"**Lv.{lv} {st.session_state.get('user_name', '勇者')}**")
        st.caption(f"Job: {JOBS.get(data['job'], {}).get('name')}")
    
    # ステータス詳細
    st.markdown(f"""
    <div class="pixel-card">
        💎 Pt: <b>{data['points']}</b><br>
        🎫 チケ: <b>{data['items'].get('gacha_ticket', 0)}</b><br>
        🔥 コンボ: <b>{data['mission_progress'].get('combo', 0)}日</b>
    </div>
    """, unsafe_allow_html=True)

    # ジョブチェンジ (1日1回)
    st.markdown("---")
    st.subheader("🦸 Job Change")
    if data["last_job_change"] != today_str:
        new_job = st.selectbox("職業選択", list(JOBS.keys()), format_func=lambda x: JOBS[x]["name"])
        st.caption(JOBS[new_job]["desc"])
        if st.button("転職する"):
            data["job"] = new_job
            data["last_job_change"] = today_str
            save_data(data)
            st.success(f"{JOBS[new_job]['name']} に転職した！")
            st.rerun()
    else:
        st.info(f"本日の職業: {JOBS[data['job']]['name']}\n(転職は明日まで不可)")

    # BGM / SE (モック)
    st.markdown("---")
    bgm_on = st.checkbox("🔊 BGM/SE", value=True)

# --- 5. メイン画面 (動的背景) ---

# 背景決定ロジック
fl = data["dungeon"]["floor"]
bg_url = ASSETS["BG_FOREST"]
if 11 <= fl <= 20: bg_url = ASSETS["BG_CAVE"]
elif 21 <= fl <= 30: bg_url = ASSETS["BG_SEA"]
elif 31 <= fl <= 40: bg_url = ASSETS["BG_VOLCANO"]
elif fl >= 41: bg_url = ASSETS["BG_CASTLE"]

# 背景表示コンテナ
st.markdown(f"""
<div style="
    background-image: linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)), url('{bg_url}');
    background-size: cover;
    background-position: center;
    padding: 20px;
    border-radius: 10px;
    color: white;
    text-align: center;
    margin-bottom: 20px;
    border: 4px solid #fff;
">
    <h2>🏰 Dungeon Floor {fl}</h2>
    <p>Area: {["森", "洞窟", "海岸", "火山", "魔王城"][min((fl-1)//10, 4)]}</p>
</div>
""", unsafe_allow_html=True)

# ペット (相棒)
if data["pet"]["active"]:
    pet_name = data["pet"]["active"]
    # 時間帯でセリフ変化
    hour = datetime.datetime.now().hour
    msg = "お供します、マスター！"
    if 6 <= hour < 12: msg = "おはようございます！今日も進みましょう！"
    elif 12 <= hour < 18: msg = "調子はどうですか？"
    elif 18 <= hour < 24: msg = "今日も一日お疲れ様でした。"
    
    st.info(f"🐶 {pet_name}: 「{msg}」")

# タブ
t1, t2, t3, t4, t5 = st.tabs(["⚔️ 冒険(タスク)", "😈 ボス & ミッション", "🎰 ガチャ", "📊 記録", "📖 図鑑"])

# --- タブ1: 冒険 (タスク & ダンジョン進行) ---
with t1:
    # ボス戦チェック (10階ごと)
    if fl % 10 == 0 and data["dungeon"]["status"] != "boss_cleared":
        st.error("⚠️ BOSS BATTLE!! 門番が現れた！")
        st.markdown(f"**Floor {fl} Boss**")
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("勇者 (あなた)")
            # ジョブ補正
            base_power = 10 + (data["level"] // 2)
            if data["job"] == "warrior": base_power += 5
            st.markdown(f"<h1>🎲 {st.session_state.get('hero_dice', '?')}</h1>", unsafe_allow_html=True)
            
        with c2:
            st.write("門番")
            boss_power = 10 + (fl // 2)
            st.markdown(f"<h1>🎲 {st.session_state.get('enemy_dice', '?')}</h1>", unsafe_allow_html=True)
            
        if st.button("勝負する！ (ダイスロール)"):
            # ダイスロール演出
            with st.spinner("🎲 Rolling..."):
                time.sleep(1.5)
            
            h_roll = random.randint(1, 6)
            e_roll = random.randint(1, 6)
            
            hero_score = h_roll + base_power
            enemy_score = e_roll + boss_power
            
            st.session_state['hero_dice'] = hero_score
            st.session_state['enemy_dice'] = enemy_score
            
            if hero_score >= enemy_score:
                st.balloons()
                st.success("勝利！！ 先へ進めます！")
                data["dungeon"]["floor"] += 1
                data["dungeon"]["status"] = "exploring"
                data["items"]["gacha_ticket"] += 1
                save_data(data)
                st.rerun()
            else:
                st.error("敗北... 近くのキャンプまで戻されます...")
                # ペナルティ: 直前の5の倍数の階に戻る
                back_floor = (fl // 5) * 5
                if back_floor == fl: back_floor -= 5
                data["dungeon"]["floor"] = max(1, back_floor)
                # デバフ
                end_time = datetime.datetime.now() + datetime.timedelta(hours=1)
                data["active_buffs"]["injury"] = end_time.isoformat()
                save_data(data)
                st.rerun()
                
    else:
        # 通常探索 (タスク)
        # 負傷チェック
        if "injury" in data["active_buffs"]:
            if datetime.datetime.now().isoformat() < data["active_buffs"]["injury"]:
                st.warning("🩹 負傷中... (獲得報酬 半減)")

        c1, c2 = st.columns(2)
        tasks = {"🧹 掃除": 30, "📚 勉強": 50, "💻 仕事": 80, "💪 筋トレ": 40}
        
        for i, (t, base) in enumerate(tasks.items()):
            rate = calculate_bonus_rate(data, t)
            final_pt = int(base * rate)
            
            with c1 if i%2==0 else c2:
                label = f"{t} (+{final_pt}pt)"
                if rate > 1.0: label += f" 🔥x{rate:.1f}"
                if rate < 1.0: label += f" 📉x{rate:.1f}"
                
                if st.button(label, key=f"task_{i}"):
                    data["points"] += final_pt
                    data["total_points"] += final_pt
                    data["xp"] += 10
                    
                    # 履歴記録
                    today = str(datetime.date.today())
                    data["point_history"][today] = data["point_history"].get(today, 0) + final_pt
                    data["task_counts"][t] = data["task_counts"].get(t, 0) + 1
                    
                    # ダンジョン進行
                    data["dungeon"]["floor"] += 1
                    if data["dungeon"]["floor"] % 10 == 0:
                        data["dungeon"]["status"] = "boss_encounter"
                    
                    # レベルアップ
                    if data["xp"] >= data["level"] * 100:
                        data["level"] += 1
                        data["xp"] = 0
                        st.toast(f"Level Up! Lv.{data['level']}", icon="🆙")
                    
                    # レイドボスダメージ
                    if data["raid_boss"]["hp"] > 0:
                        data["raid_boss"]["hp"] -= final_pt
                    
                    save_data(data)
                    st.toast(f"Floor {data['dungeon']['floor']} に到達！", icon="👣")
                    st.rerun()

# --- タブ2: レイドボス & ミッション ---
with t2:
    st.subheader("😈 週間レイドボス")
    boss = data["raid_boss"]
    
    # 残り時間計算 (月曜まで)
    now = datetime.datetime.now()
    next_monday = (now + datetime.timedelta(days=(7 - now.weekday()))).replace(hour=0, minute=0, second=0, microsecond=0)
    remain = next_monday - now
    
    col_b1, col_b2 = st.columns([3, 1])
    with col_b1:
        st.write(f"**{boss['name']}** (HP: {max(0, boss['hp'])} / {boss['max_hp']})")
        hp_pct = max(0, boss["hp"] / boss["max_hp"]) * 100
        st.markdown(f"""
        <div class="boss-container">
            <div class="boss-fill" style="width: {hp_pct}%;"></div>
        </div>
        """, unsafe_allow_html=True)
        st.caption(f"リセットまで: {remain.days}日 {remain.seconds//3600}時間")
        
    with col_b2:
        if st.button("🎁 報酬確認"):
            st.toast("討伐報酬: SR確定チケット x1 + 1000pt", icon="🎁")
            
    if boss["hp"] <= 0:
        st.success("討伐完了！！")
        if boss.get("reward_claimed") != True:
            if st.button("報酬を受け取る"):
                data["items"]["sr_ticket"] = data["items"].get("sr_ticket", 0) + 1
                data["points"] += 1000
                data["raid_boss"]["reward_claimed"] = True
                save_data(data)
                st.balloons()
                st.rerun()
                
    st.markdown("---")
    st.subheader("📅 ミッション")
    # (既存のミッション表示ロジックと同じため省略なしで実装)
    for m in [{"id": "d_login", "name": "ログイン", "pt": 50}]:
        if data["mission_progress"]["daily"].get(f"{m['id']}_claimed"):
            st.caption(f"✅ {m['name']} (受取済)")
        else:
            if st.button(f"受取: {m['name']}", key=m["id"]):
                data["points"] += m["pt"]
                data["mission_progress"]["daily"][f"{m['id']}_claimed"] = True
                save_data(data)
                st.rerun()

# --- タブ3: ガチャ (アニメーション) ---
with t3:
    st.subheader("🎰 召喚の間")
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.image(ASSETS["CHEST_CLOSED"], width=200)
    
    with col_g2:
        st.write("チケットで仲間を召喚！")
        n_tic = data["items"].get("gacha_ticket", 0)
        
        if st.button(f"引く (残り{n_tic}枚)", disabled=n_tic==0):
            data["items"]["gacha_ticket"] -= 1
            
            # 演出
            placeholder = st.empty()
            placeholder.info("箱が揺れている...")
            time.sleep(1)
            placeholder.warning("光が溢れ出す...！")
            time.sleep(1)
            placeholder.empty()
            
            # 抽選
            rarity = random.choices(["N", "R", "SR", "SSR", "UR"], weights=[50, 30, 15, 4, 1])[0]
            m = random.choice(MONSTER_DB[rarity])
            
            st.image(m["img"], width=200)
            st.markdown(f"## {rarity} {m['name']}")
            
            # データ保存
            data["monster_levels"][m["name"]] = data["monster_levels"].get(m["name"], 0) + 1
            save_data(data)
            st.balloons()

# --- タブ4: 記録 (グラフ) ---
with t4:
    st.subheader("📊 冒険の記録")
    
    # 棒グラフ (過去7日間)
    if data["point_history"]:
        df = pd.DataFrame(list(data["point_history"].items()), columns=["Date", "Points"])
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").tail(7) # 最新7日
        
        fig = px.bar(df, x="Date", y="Points", title="Daily Points (Last 7 Days)", template="plotly_dark")
        fig.update_traces(marker_color='#e94560')
        st.plotly_chart(fig, use_container_width=True)
        
        # VS先週比 (簡易ロジック)
        total_this_week = df["Points"].sum()
        st.metric("今週の合計", f"{total_this_week} pt", delta="Keep going!")

# --- タブ5: 図鑑 & 相棒設定 ---
with t5:
    st.subheader("📖 モンスター図鑑")
    st.caption("クリックして相棒(ペット)に設定")
    
    cols = st.columns(3)
    idx = 0
    for r in ["UR", "SSR", "SR", "R", "N"]:
        for m in MONSTER_DB[r]:
            if m["name"] in data["monster_levels"]:
                with cols[idx % 3]:
                    st.image(m["img"], width=100)
                    if st.button(f"{m['name']} (Lv.{data['monster_levels'][m['name']]})", key=f"set_{m['name']}"):
                        data["pet"]["active"] = m["name"]
                        save_data(data)
                        st.success(f"{m['name']} を相棒にした！")
                        st.rerun()
                idx += 1
