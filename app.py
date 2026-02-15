import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import random
import json
import time
import pandas as pd
import plotly.express as px

# --- 1. 設定とデータ定義 ---

# ★正しいスプレッドシートID
SHEET_ID = "1FvqLUrkR_YYk_azwI35rGr6_Y2swgUp1mawfJget5KU"

# 画像素材 (イラスト問題を解決するため、色+絵文字の確実な画像を使用)
# もし好きな画像があれば、ここのURLを書き換えてください
MONSTER_IMGS = {
    "UR_DRAGON": "https://placehold.co/400x400/8B0000/FFFFFF?text=🐲+Dragon",
    "UR_ANGEL": "https://placehold.co/400x400/FFFF00/000000?text=👼+Angel",
    "SSR_ROBOT": "https://placehold.co/400x400/2C3E50/00FFFF?text=🤖+Mecha",
    "SSR_LION": "https://placehold.co/400x400/DAA520/FFFFFF?text=🦁+Lion",
    "SR_WOLF": "https://placehold.co/400x400/A9A9A9/FFFFFF?text=🐺+Wolf",
    "SR_GRIFFIN": "https://placehold.co/400x400/B8860B/FFFFFF?text=🦅+Griffin",
    "R_BOAR": "https://placehold.co/400x400/8B4513/FFFFFF?text=🐗+Boar",
    "R_SPIDER": "https://placehold.co/400x400/000000/00FF00?text=🕷️+Spider",
    "R_BAT": "https://placehold.co/400x400/4B0082/FFFFFF?text=🦇+Bat",
    "N_SLIME": "https://placehold.co/400x400/3498DB/FFFFFF?text=💧+Slime", # 青いスライム
    "N_MUSHROOM": "https://placehold.co/400x400/E74C3C/FFFFFF?text=🍄+Mushroom",
    
    # ガチャ演出用
    "CAPSULE_BLUE": "https://cdn-icons-png.flaticon.com/512/3503/3503202.png",
    "CAPSULE_GOLD": "https://cdn-icons-png.flaticon.com/512/3503/3503222.png",
    "CAPSULE_RAINBOW": "https://cdn-icons-png.flaticon.com/512/8617/8617997.png",
    "GACHA_GIF": "https://media.tenor.com/JdJOQWqH3yUAAAAM/summon-summoning.gif"
}

MONSTER_DB = {
    "UR": [
        {"name": "🐲 伝説のドラゴン", "power": 10000, "skill": {"type": "all_bonus", "val": 0.2}, "desc": "全タスク報酬+20%！最強の古龍。", "img": MONSTER_IMGS["UR_DRAGON"]},
        {"name": "👼 大天使", "power": 9500, "skill": {"type": "task_bonus", "target": "ウォーキング", "val": 0.5}, "desc": "歩行報酬+50%！天界の使者。", "img": MONSTER_IMGS["UR_ANGEL"]}
    ],
    "SSR": [
        {"name": "🤖 未来ロボ", "power": 5500, "skill": {"type": "task_bonus", "target": "コード書き", "val": 0.3}, "desc": "コード報酬+30%！未来の技術。", "img": MONSTER_IMGS["SSR_ROBOT"]},
        {"name": "🦁 百獣の王", "power": 5000, "skill": {"type": "task_bonus", "target": "筋トレ", "val": 0.3}, "desc": "筋トレ報酬+30%！王者の風格。", "img": MONSTER_IMGS["SSR_LION"]}
    ],
    "SR": [
        {"name": "🐺 シルバーウルフ", "power": 3000, "skill": {"type": "task_bonus", "target": "ウォーキング", "val": 0.15}, "desc": "歩行報酬+15%！孤高の狼。", "img": MONSTER_IMGS["SR_WOLF"]},
        {"name": "🦅 グリフォン", "power": 3200, "skill": {"type": "task_bonus", "target": "筋トレ", "val": 0.15}, "desc": "筋トレ報酬+15%！空の王者。", "img": MONSTER_IMGS["SR_GRIFFIN"]}
    ],
    "R": [
        {"name": "🐗 ワイルドボア", "power": 1200, "skill": {"type": "task_bonus", "target": "筋トレ", "val": 0.05}, "desc": "筋トレ報酬+5%！猪突猛進。", "img": MONSTER_IMGS["R_BOAR"]},
        {"name": "🕷️ 巨大グモ", "power": 1100, "skill": {"type": "task_bonus", "target": "コード書き", "val": 0.05}, "desc": "コード報酬+5%！ネットの住人。", "img": MONSTER_IMGS["R_SPIDER"]},
        {"name": "🦇 コウモリ", "power": 900, "skill": {"type": "task_bonus", "target": "ウォーキング", "val": 0.05}, "desc": "歩行報酬+5%！夜行性。", "img": MONSTER_IMGS["R_BAT"]}
    ],
    "N": [
        {"name": "💧 スライム", "power": 100, "skill": {"type": "task_bonus", "target": "掃除", "val": 0.05}, "desc": "掃除報酬+5%！基本の魔物。", "img": MONSTER_IMGS["N_SLIME"]},
        {"name": "🍄 きのこ", "power": 50, "skill": {"type": "task_bonus", "target": "勉強", "val": 0.05}, "desc": "勉強報酬+5%！毒はない。", "img": MONSTER_IMGS["N_MUSHROOM"]}
    ]
}

GACHA_RATES = {"UR": 1, "SSR": 4, "SR": 15, "R": 30, "N": 50}

# ミッション定義
MISSIONS = {
    "daily": [
        {"id": "d_login", "desc": "ログインする", "target": 1, "reward_pt": 50},
        {"id": "d_task3", "desc": "タスクを3回完了", "target": 3, "reward_pt": 100},
        {"id": "d_gacha", "desc": "ガチャを引く", "target": 1, "reward_pt": 50}
    ],
    "weekly": [
        {"id": "w_task20", "desc": "週間タスク20回", "target": 20, "reward_item": "gacha_ticket", "amount": 1},
        {"id": "w_boss", "desc": "ボスに1000ダメ", "target": 1000, "reward_item": "gacha_ticket", "amount": 1}
    ]
}

# データベース接続
def get_database():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

# データ読み込み
def load_data():
    try:
        sheet = get_database()
        data_str = sheet.acell('A1').value
        if data_str:
            data = json.loads(data_str)
            # データの初期化・補正
            if "point_history" not in data: data["point_history"] = {} # 日別ポイント記録
            if "shop_counts" not in data: data["shop_counts"] = {} # ショップ購入記録(日/週/月)
            if "items" not in data: data["items"] = {"gacha_ticket": 0, "sr_ticket": 0, "ssr_ticket": 0}
            if "monster_levels" not in data: data["monster_levels"] = {}
            if "raid_boss" not in data: data["raid_boss"] = {"hp": 5000, "max_hp": 5000, "name": "魔王・怠惰", "defeat_count": 0}
            if "achievements" not in data: data["achievements"] = []
            if "task_counts" not in data: data["task_counts"] = {}
            if "total_points" not in data: data["total_points"] = data["points"]
            if "expedition" not in data: data["expedition"] = {"active": False, "end_time": None, "monster": ""}
            if "equipment" not in data: data["equipment"] = {"weapon": None, "armor": None}
            if "active_buffs" not in data: data["active_buffs"] = {}
            if "mission_progress" not in data: data["mission_progress"] = {"daily": {}, "weekly": {}, "last_login": "", "last_week": 0}
            if "bg_theme" not in data: data["bg_theme"] = "default"
            
            return data
    except Exception as e:
        print(f"Load Error: {e}")
        pass
    
    # 初期データ
    return {
        "points": 0, "total_points": 0, "xp": 0, "level": 1, 
        "last_login": "", 
        "monster_levels": {}, 
        "items": {"gacha_ticket": 0, "sr_ticket": 0, "ssr_ticket": 0},
        "raid_boss": {"hp": 5000, "max_hp": 5000, "name": "魔王・怠惰", "defeat_count": 0},
        "achievements": [],
        "task_counts": {},
        "point_history": {},
        "shop_counts": {},
        "expedition": {"active": False, "end_time": None, "monster": ""},
        "equipment": {"weapon": None, "armor": None},
        "active_buffs": {},
        "mission_progress": {"daily": {}, "weekly": {}, "last_login": "", "last_week": 0},
        "bg_theme": "default"
    }

# データ保存
def save_data(data):
    try:
        sheet = get_database()
        json_str = json.dumps(data, ensure_ascii=False)
        sheet.update_acell('A1', json_str)
    except Exception as e:
        if "200" in str(e): return 
        st.error(f"セーブ失敗: {e}")

# ポイント加算（同時に履歴も更新）
def add_points(data, amount):
    data["points"] += amount
    data["total_points"] += amount
    
    # 日別履歴の更新
    today = str(datetime.date.today())
    data["point_history"][today] = data["point_history"].get(today, 0) + amount
    return data

# ショップ購入制限チェック
def check_shop_limit(data, item_key, limit_type, limit_count):
    today = str(datetime.date.today())
    week = f"{datetime.date.today().year}-W{datetime.date.today().isocalendar()[1]}"
    month = f"{datetime.date.today().year}-{datetime.date.today().month}"
    
    counts = data["shop_counts"]
    
    if limit_type == "daily":
        key = f"{item_key}_{today}"
        return counts.get(key, 0) < limit_count, key
    elif limit_type == "weekly":
        key = f"{item_key}_{week}"
        return counts.get(key, 0) < limit_count, key
    elif limit_type == "monthly":
        key = f"{item_key}_{month}"
        return counts.get(key, 0) < limit_count, key
    return True, None

def use_shop_limit(data, key):
    data["shop_counts"][key] = data["shop_counts"].get(key, 0) + 1

# ボーナス計算
def calculate_bonus(data, task_name_part):
    bonus_rate = 0.0
    # モンスター
    for m_name, level in data["monster_levels"].items():
        monster_info = None
        for rarity in MONSTER_DB:
            for m in MONSTER_DB[rarity]:
                if m["name"] == m_name: monster_info = m
        if monster_info and "skill" in monster_info:
            skill = monster_info["skill"]
            lv_factor = 1.0 + (level - 1) * 0.1
            if skill["type"] == "all_bonus": bonus_rate += skill["val"] * lv_factor
            elif skill["type"] == "task_bonus" and skill.get("target") in task_name_part:
                bonus_rate += skill["val"] * lv_factor
    # 装備
    if data["equipment"]["weapon"] == "勇者の剣": bonus_rate += 0.1
    if data["equipment"]["armor"] == "王者の盾": bonus_rate += 0.05
    # ポーション
    now = datetime.datetime.now().isoformat()
    if "potion" in data["active_buffs"]:
        if now < data["active_buffs"]["potion"]: bonus_rate += 1.0
        else: del data["active_buffs"]["potion"]
            
    return bonus_rate

# ミッション更新
def update_mission(data, action_type, val=1):
    today = str(datetime.date.today())
    week_num = datetime.date.today().isocalendar()[1]
    
    if data["mission_progress"]["last_login"] != today:
        data["mission_progress"]["daily"] = {}
        data["mission_progress"]["last_login"] = today
    if data["mission_progress"]["last_week"] != week_num:
        data["mission_progress"]["weekly"] = {}
        data["mission_progress"]["last_week"] = week_num

    prog = data["mission_progress"]
    prog["daily"][action_type] = prog["daily"].get(action_type, 0) + val
    prog["weekly"][action_type] = prog["weekly"].get(action_type, 0) + val
    return data

# ガチャロジック (チケット対応)
def pull_gacha(min_rarity="N"):
    rates = GACHA_RATES.copy()
    
    # 確定ガチャ用の確率操作
    if min_rarity == "SR":
        rates = {"UR": 5, "SSR": 15, "SR": 80} # SR以上のみ
    elif min_rarity == "SSR":
        rates = {"UR": 20, "SSR": 80} # SSR以上のみ

    rarity = random.choices(list(rates.keys()), weights=list(rates.values()), k=1)[0]
    monster_obj = random.choice(MONSTER_DB[rarity])
    return rarity, monster_obj

# --- アプリ画面構築 ---
st.set_page_config(page_title="Life Quest: Legend", page_icon="⚔️")

if 'data' not in st.session_state: st.session_state.data = load_data()
data = st.session_state.data

# テーマ
theme_color = "#f0f2f6"
if data.get("bg_theme") == "dark": theme_color = "#2c3e50"
elif data.get("bg_theme") == "gold": theme_color = "#fff8dc"

st.markdown(f"""
<style>
    .stApp {{ background-color: {theme_color}; }}
    .stButton>button {{ width: 100%; border-radius: 12px; font-weight: bold; border: 2px solid #333; }}
    .status-box {{ padding: 15px; border-radius: 10px; background-color: #fff; border: 2px solid #ccc; margin-bottom: 20px; color: #333; }}
    .card {{ background-color: #fff; padding: 10px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); border: 1px solid #ddd; text-align: center; margin-bottom: 10px; color: #333; }}
    .boss-bar {{ width: 100%; background-color: #ddd; border-radius: 10px; height: 20px; overflow: hidden; margin-bottom: 10px; }}
    .boss-hp {{ height: 100%; background-color: #e74c3c; transition: width 0.5s; }}
</style>
""", unsafe_allow_html=True)

# ログイン処理
update_mission(data, "d_login", 1)
today = str(datetime.date.today())
if data["last_login"] != today:
    data["last_login"] = today
    add_points(data, 100) # ログインボーナス
    st.balloons()
    st.success("🎁 ログインボーナス！ +100pt")
    save_data(data)

# サイドバー
with st.sidebar:
    st.title("🛡️ ステータス")
    wpn = data["equipment"]["weapon"] or "なし"
    arm = data["equipment"]["armor"] or "なし"
    
    st.markdown(f"""
    <div class="status-box">
        <h3>Lv. {data['level']}</h3>
        <p>💎 Pt: <b>{data['points']}</b></p>
        <p>🎫 チケ: <b>{data['items'].get('gacha_ticket', 0)}</b></p>
        <hr>
        <p>⚔️ 武器: {wpn}</p>
        <p>🛡️ 防具: {arm}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # バフ
    now = datetime.datetime.now().isoformat()
    if "potion" in data["active_buffs"]:
        if now < data["active_buffs"]["potion"]:
            st.warning("🔥 やる気ポーション有効中！")
    
    if st.button("🔄 データ手動保存"): 
        save_data(data)
        st.success("保存しました")

st.title("⚔️ Life Quest: Legend")

# レイドボス
boss = data["raid_boss"]
if boss["hp"] > 0:
    st.markdown(f"### 😈 {boss['name']} (Lv.{boss['defeat_count']+1})")
    hp_per = max(0, boss["hp"] / boss["max_hp"])
    st.markdown(f"""<div class="boss-bar"><div class="boss-hp" style="width: {hp_per*100}%;"></div></div>""", unsafe_allow_html=True)
    st.caption(f"HP: {boss['hp']} / {boss['max_hp']}")
else:
    st.success(f"🎉 {boss['name']} 討伐完了！")
    if st.button("次のボスへ挑む"):
        data["items"]["gacha_ticket"] += 1
        boss["defeat_count"] += 1
        boss["max_hp"] += 2000
        boss["hp"] = boss["max_hp"]
        save_data(data)
        st.rerun()

tabs = st.tabs(["📜 クエスト", "📅 ミッション", "🏪 ショップ", "🗺️ 冒険", "🔮 ガチャ", "📊 記録", "📖 図鑑"])

# --- 1. クエスト ---
with tabs[0]:
    st.subheader("本日の任務")
    c1, c2 = st.columns(2)
    tasks = {"🧹 掃除": 30, "📚 勉強": 50, "💻 コード書き": 80, "💪 筋トレ": 40, "🚶 ウォーキング": 100}
    
    for i, (t_name, base) in enumerate(tasks.items()):
        with c1 if i%2==0 else c2:
            bonus = calculate_bonus(data, t_name)
            final = int(base * (1 + bonus))
            label = f"{t_name}\n(+{final}pt)"
            if bonus > 0: label += f" 🔥+{int(bonus*100)}%"
            
            if st.button(label):
                add_points(data, final)
                data["xp"] += 10
                data["task_counts"][t_name] = data["task_counts"].get(t_name, 0) + 1
                
                dmg = 50 + (data["level"] * 5)
                if boss["hp"] > 0: boss["hp"] -= dmg
                
                update_mission(data, "d_task3", 1)
                update_mission(data, "w_task20", 1)
                update_mission(data, "w_boss", dmg)

                if data["xp"] // 100 > data["level"]: data["level"] += 1
                save_data(data)
                st.toast(f"完了！ +{final}pt")
                st.rerun()

# --- 2. ミッション ---
with tabs[1]:
    st.subheader("📅 ミッションボード")
    
    # デイリー
    st.markdown("##### 🌞 デイリー")
    for m in MISSIONS["daily"]:
        prog = data["mission_progress"]["daily"].get(m["id"], 0)
        done = prog >= m["target"]
        claimed = f"{m['id']}_claimed" in data["mission_progress"]["daily"]
        
        col_m1, col_m2 = st.columns([3, 1])
        col_m1.progress(min(prog/m["target"], 1.0), text=f"{m['desc']} ({prog}/{m['target']})")
        
        if done and not claimed:
            if col_m2.button("受取", key=m["id"]):
                add_points(data, m["reward_pt"])
                data["mission_progress"]["daily"][f"{m['id']}_claimed"] = True
                save_data(data)
                st.rerun()
        elif claimed:
            col_m2.caption("受取済")

    # ウィークリー
    st.markdown("##### 📅 ウィークリー")
    for m in MISSIONS["weekly"]:
        prog = data["mission_progress"]["weekly"].get(m["id"], 0)
        done = prog >= m["target"]
        claimed = f"{m['id']}_claimed" in data["mission_progress"]["weekly"]
        
        col_m1, col_m2 = st.columns([3, 1])
        col_m1.progress(min(prog/m["target"], 1.0), text=f"{m['desc']} ({prog}/{m['target']})")
        
        if done and not claimed:
            if col_m2.button("受取", key=m["id"]):
                data["items"][m["reward_item"]] = data["items"].get(m["reward_item"], 0) + m["amount"]
                data["mission_progress"]["weekly"][f"{m['id']}_claimed"] = True
                save_data(data)
                st.rerun()
        elif claimed:
            col_m2.caption("受取済")

# --- 3. ショップ (制限機能付き) ---
with tabs[2]:
    st.subheader("🏪 雑貨屋")
    
    # 1. デイリーガチャチケ
    can_buy, key = check_shop_limit(data, "ticket", "daily", 1)
    st.markdown(f"**🎫 ガチャチケ** (150pt) `残り: {1 if can_buy else 0}`")
    if st.button("購入", disabled=not can_buy or data["points"]<150):
        data["points"] -= 150
        data["items"]["gacha_ticket"] += 1
        use_shop_limit(data, key)
        save_data(data)
        st.success("購入しました！")
        st.rerun()
            
    # 2. SR確定 (週1)
    can_buy_sr, key_sr = check_shop_limit(data, "sr_ticket", "weekly", 1)
    st.markdown(f"**🎫 SR確定チケット** (1000pt) `週残り: {1 if can_buy_sr else 0}`")
    if st.button("購入 (SR)", disabled=not can_buy_sr or data["points"]<1000):
        data["points"] -= 1000
        data["items"]["sr_ticket"] = data["items"].get("sr_ticket", 0) + 1
        use_shop_limit(data, key_sr)
        save_data(data)
        st.success("SRチケット購入！")
        st.rerun()

    # 3. SSR確定 (月1)
    can_buy_ssr, key_ssr = check_shop_limit(data, "ssr_ticket", "monthly", 1)
    st.markdown(f"**🎫 SSR確定チケット** (3000pt) `月残り: {1 if can_buy_ssr else 0}`")
    if st.button("購入 (SSR)", disabled=not can_buy_ssr or data["points"]<3000):
        data["points"] -= 3000
        data["items"]["ssr_ticket"] = data["items"].get("ssr_ticket", 0) + 1
        use_shop_limit(data, key_ssr)
        save_data(data)
        st.success("SSRチケット購入！")
        st.rerun()

    st.markdown("---")
    # 特殊アイテム
    if st.button("⏳ 時の砂時計 (500pt) - ミッションリセット", disabled=data["points"]<500):
        data["points"] -= 500
        data["mission_progress"]["daily"] = {} # リセット
        save_data(data)
        st.success("時間が巻き戻った... ミッションが復活！")
        st.rerun()

    if st.button("🧪 やる気ポーション (300pt)", disabled=data["points"]<300):
        data["points"] -= 300
        end_time = datetime.datetime.now() + datetime.timedelta(hours=1)
        data["active_buffs"]["potion"] = end_time.isoformat()
        save_data(data)
        st.success("やる気がみなぎる！")
        st.rerun()

# --- 4. 冒険 (6時間) ---
with tabs[3]:
    st.subheader("🗺️ 冒険 (6時間)")
    now = datetime.datetime.now()
    exp = data.get("expedition", {"active": False})
    
    if exp["active"]:
        end_time = datetime.datetime.fromisoformat(exp["end_time"])
        if now >= end_time:
            is_success = random.randint(1, 100) <= 30
            st.balloons()
            if is_success:
                st.success(f"大成功！！ {exp['monster']} が宝箱を見つけた！")
                add_points(data, 1000)
                data["items"]["gacha_ticket"] += 1
            else:
                st.info(f"おかえり！ {exp['monster']} が帰ってきた。")
                add_points(data, 500)
            
            update_mission(data, "w_task20", 1)
            data["expedition"] = {"active": False, "end_time": None, "monster": ""}
            save_data(data)
            if st.button("OK"): st.rerun()
        else:
            remain = end_time - now
            h, rem = divmod(remain.seconds, 3600)
            m, s = divmod(rem, 60)
            st.info(f"🚀 {exp['monster']} が探索中... 残り {h}時間{m}分")
            if st.button("更新"): st.rerun()
    else:
        if not data["monster_levels"]:
            st.warning("仲間がいません。")
        else:
            m_list = list(data["monster_levels"].keys())
            sel = st.selectbox("派遣する", m_list)
            if st.button("出発！"):
                end = now + datetime.timedelta(hours=6)
                data["expedition"] = {"active": True, "end_time": end.isoformat(), "monster": sel}
                save_data(data)
                st.rerun()

# --- 5. ガチャ (演出強化) ---
with tabs[4]:
    st.subheader("召喚の間")
    
    def run_gacha_anim(rarity):
        placeholder = st.empty()
        placeholder.image(MONSTER_IMGS["GACHA_GIF"], use_column_width=True)
        time.sleep(2.5)
        
        capsule_img = MONSTER_IMGS["CAPSULE_BLUE"]
        if rarity == "UR": capsule_img = MONSTER_IMGS["CAPSULE_RAINBOW"]
        elif rarity in ["SSR", "SR"]: capsule_img = MONSTER_IMGS["CAPSULE_GOLD"]
        
        placeholder.markdown(f"<div style='text-align:center;'><img src='{capsule_img}' width='200'></div>", unsafe_allow_html=True)
        time.sleep(1.0)
        return placeholder

    c1, c2 = st.columns(2)
    with c1:
        if st.button("無料 (1日1回)", disabled=data["daily_gacha_done"]):
            data["daily_gacha_done"] = True
            rarity, m = pull_gacha()
            ph = run_gacha_anim(rarity)
            ph.empty()
            st.image(m["img"], width=300)
            st.markdown(f"## {rarity} {m['name']}")
            data["monster_levels"][m["name"]] = data["monster_levels"].get(m["name"], 0) + 1
            update_mission(data, "d_gacha", 1)
            save_data(data)
            st.balloons()
            
    with c2:
        t_n = data["items"].get("gacha_ticket", 0)
        t_sr = data["items"].get("sr_ticket", 0)
        t_ssr = data["items"].get("ssr_ticket", 0)
        
        # 通常チケット
        if st.button(f"通常チケ ({t_n}) / 200pt", disabled=(t_n==0 and data["points"]<200)):
            if t_n > 0: data["items"]["gacha_ticket"] -= 1
            else: data["points"] -= 200
            rarity, m = pull_gacha("N")
            ph = run_gacha_anim(rarity)
            ph.empty()
            st.image(m["img"], width=300)
            st.markdown(f"## {rarity} {m['name']}")
            data["monster_levels"][m["name"]] = data["monster_levels"].get(m["name"], 0) + 1
            update_mission(data, "d_gacha", 1)
            save_data(data)
            st.balloons()

        # 確定チケット
        if t_sr > 0:
            if st.button(f"SR確定チケを使用 ({t_sr})"):
                data["items"]["sr_ticket"] -= 1
                rarity, m = pull_gacha("SR")
                ph = run_gacha_anim(rarity)
                ph.empty()
                st.image(m["img"], width=300)
                st.markdown(f"## {rarity} {m['name']}")
                data["monster_levels"][m["name"]] = data["monster_levels"].get(m["name"], 0) + 1
                save_data(data)
                st.balloons()
                
        if t_ssr > 0:
            if st.button(f"SSR確定チケを使用 ({t_ssr})"):
                data["items"]["ssr_ticket"] -= 1
                rarity, m = pull_gacha("SSR")
                ph = run_gacha_anim(rarity)
                ph.empty()
                st.image(m["img"], width=300)
                st.markdown(f"## {rarity} {m['name']}")
                data["monster_levels"][m["name"]] = data["monster_levels"].get(m["name"], 0) + 1
                save_data(data)
                st.balloons()

# --- 6. 記録 (グラフ) ---
with tabs[5]:
    st.subheader("📊 活動ログ")
    
    # 1. 日別ポイント推移 (棒グラフ)
    if data["point_history"]:
        history_df = pd.DataFrame(list(data["point_history"].items()), columns=["Date", "Points"])
        history_df["Date"] = pd.to_datetime(history_df["Date"])
        history_df = history_df.sort_values("Date")
        
        st.markdown("##### 📅 日別の獲得ポイント")
        fig_bar = px.bar(history_df, x="Date", y="Points", title="毎日の頑張り")
        st.plotly_chart(fig_bar)
    else:
        st.info("データ収集中... タスクをこなすとここにグラフが出ます。")

    st.markdown("---")
    
    # 2. タスク比率 (円グラフ)
    if data["task_counts"]:
        df_pie = pd.DataFrame(list(data["task_counts"].items()), columns=["Task", "Count"])
        st.markdown("##### 🧹 タスクの内訳")
        fig_pie = px.pie(df_pie, values='Count', names='Task')
        st.plotly_chart(fig_pie)

# --- 7. 図鑑 ---
with tabs[6]:
    st.subheader("図鑑")
    cols = st.columns(3)
    my_mons = data["monster_levels"]
    i = 0
    for r in ["UR", "SSR", "SR", "R", "N"]:
        for m in MONSTER_DB[r]:
            if m["name"] in my_mons:
                with cols[i%3]:
                    st.image(m["img"], use_column_width=True)
                    st.caption(f"{m['name']} (Lv.{my_mons[m['name']]})")
                i+=1
