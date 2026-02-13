import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import random
import json
import time

# --- 1. 設定とデータ定義 ---
SHEET_NAME = "life_quest_db"

# ★ここが重要！画像のURLリスト
# 自分の好きな画像があれば、ここのURLを書き換えるだけで変わります！
MONSTER_IMGS = {
    "UR_DRAGON": "https://images.unsplash.com/photo-1599725427295-584a96319d69?auto=format&fit=crop&q=80&w=400", # ドラゴン風
    "SSR_ROBOT": "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&q=80&w=400", # ロボット風
    "SR_WOLF": "https://images.unsplash.com/photo-1590420485404-f86f2f12c6a0?auto=format&fit=crop&q=80&w=400", # オオカミ
    "N_SLIME": "https://images.unsplash.com/photo-1518020382113-a7e8fc38eac9?auto=format&fit=crop&q=80&w=400", # スライムっぽい液体
    "GACHA_GIF": "https://media.tenor.com/JdJOQWqH3yUAAAAM/summon-summoning.gif" # 召喚の魔法陣GIF
}

MONSTER_DB = {
    "UR": [
        {"name": "🐲 伝説のドラゴン", "power": 10000, "skill": {"type": "all_bonus", "val": 0.2}, "desc": "全タスク報酬+20%！最強の古龍。", "img": MONSTER_IMGS["UR_DRAGON"]},
        {"name": "👼 大天使", "power": 9500, "skill": {"type": "task_bonus", "target": "ウォーキング", "val": 0.5}, "desc": "歩行報酬+50%！天界の使者。", "img": "https://placehold.co/400x400/f1c40f/ffffff?text=Archangel"}
    ],
    "SSR": [
        {"name": "🤖 未来ロボ", "power": 5500, "skill": {"type": "task_bonus", "target": "コード書き", "val": 0.3}, "desc": "コード報酬+30%！未来の技術。", "img": MONSTER_IMGS["SSR_ROBOT"]},
        {"name": "🦁 百獣の王", "power": 5000, "skill": {"type": "task_bonus", "target": "筋トレ", "val": 0.3}, "desc": "筋トレ報酬+30%！王者の風格。", "img": "https://placehold.co/400x400/f39c12/2c3e50?text=Lion+King"}
    ],
    "SR": [
        {"name": "🐺 シルバーウルフ", "power": 3000, "skill": {"type": "task_bonus", "target": "ウォーキング", "val": 0.15}, "desc": "歩行報酬+15%！孤高の狼。", "img": MONSTER_IMGS["SR_WOLF"]},
        {"name": "🦅 グリフォン", "power": 3200, "skill": {"type": "task_bonus", "target": "筋トレ", "val": 0.15}, "desc": "筋トレ報酬+15%！空の王者。", "img": "https://placehold.co/400x400/d35400/f1c40f?text=Griffon"}
    ],
    "N": [
        {"name": "💧 スライム", "power": 100, "skill": {"type": "task_bonus", "target": "掃除", "val": 0.05}, "desc": "掃除報酬+5%！基本の魔物。", "img": MONSTER_IMGS["N_SLIME"]},
        {"name": "🍄 きのこ", "power": 50, "skill": {"type": "task_bonus", "target": "勉強", "val": 0.05}, "desc": "勉強報酬+5%！毒はない。", "img": "https://placehold.co/400x400/e67e22/ecf0f1?text=Mushroom"}
    ]
}

GACHA_RATES = {"UR": 1, "SSR": 4, "SR": 15, "R": 30, "N": 50}
ACHIEVEMENTS = [
    {"id": "clean_master", "name": "🧹 掃除の達人", "cond": lambda d: d["task_counts"].get("掃除", 0) >= 10},
    {"id": "rich_man", "name": "💰 大富豪", "cond": lambda d: d["total_points"] >= 5000},
    {"id": "collector", "name": "📦 コレクター", "cond": lambda d: len(d["monster_levels"]) >= 5},
    {"id": "slayer", "name": "🗡️ 魔王殺し", "cond": lambda d: d["raid_boss"]["defeat_count"] >= 1}
]

# データベース接続
def get_database():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

# データ読み込み
def load_data():
    try:
        sheet = get_database()
        data_str = sheet.acell('A1').value
        if data_str:
            data = json.loads(data_str)
            # データ補正 (V10用)
            if "monster_levels" not in data:
                new_levels = {}
                for m_name in data.get("collection", []):
                    new_levels[m_name] = new_levels.get(m_name, 0) + 1
                data["monster_levels"] = new_levels
            if "raid_boss" not in data:
                data["raid_boss"] = {"hp": 5000, "max_hp": 5000, "name": "魔王・怠惰", "defeat_count": 0}
            if "achievements" not in data: data["achievements"] = []
            if "task_counts" not in data: data["task_counts"] = {}
            if "total_points" not in data: data["total_points"] = data["points"]
            
            # ★新機能用データ
            if "expedition" not in data: data["expedition"] = {"active": False, "end_time": None, "monster": ""}
            if "daily_shop_counts" not in data: data["daily_shop_counts"] = {"ticket": 0} # 購入回数制限用
            
            return data
    except: pass
    
    return {
        "points": 0, "total_points": 0, "xp": 0, "level": 1, 
        "last_login": "", 
        "monster_levels": {}, 
        "daily_gacha_done": False,
        "items": {"gacha_ticket": 0},
        "raid_boss": {"hp": 5000, "max_hp": 5000, "name": "魔王・怠惰", "defeat_count": 0},
        "achievements": [],
        "task_counts": {},
        "expedition": {"active": False, "end_time": None, "monster": ""},
        "daily_shop_counts": {"ticket": 0}
    }

# データ保存
def save_data(data):
    try:
        for ach in ACHIEVEMENTS:
            if ach["id"] not in data["achievements"]:
                if ach["cond"](data):
                    data["achievements"].append(ach["id"])
                    st.toast(f"実績解除！【{ach['name']}】", icon="🏆")
        
        sheet = get_database()
        json_str = json.dumps(data, ensure_ascii=False)
        sheet.update_acell('A1', json_str)
    except Exception as e:
        if "200" in str(e): return 
        st.error(f"セーブ失敗: {e}")

# パッシブスキル計算
def calculate_bonus(data, task_name_part):
    bonus_rate = 0.0
    for m_name, level in data["monster_levels"].items():
        monster_info = None
        for rarity in MONSTER_DB:
            for m in MONSTER_DB[rarity]:
                if m["name"] == m_name:
                    monster_info = m
                    break
        
        if monster_info and "skill" in monster_info:
            skill = monster_info["skill"]
            level_factor = 1.0 + (level - 1) * 0.1
            
            if skill["type"] == "all_bonus":
                bonus_rate += skill["val"] * level_factor
            elif skill["type"] == "task_bonus":
                if skill.get("target") in task_name_part:
                    bonus_rate += skill["val"] * level_factor
                    
    return bonus_rate

# ガチャロジック
def pull_gacha():
    rarity = random.choices(list(GACHA_RATES.keys()), weights=list(GACHA_RATES.values()), k=1)[0]
    monster_obj = random.choice(MONSTER_DB[rarity])
    return rarity, monster_obj

# ログインボーナス（ショップ回数リセット機能付き）
def check_login_bonus(data):
    today = str(datetime.date.today())
    if data["last_login"] != today:
        data["last_login"] = today
        data["daily_gacha_done"] = False
        data["daily_shop_counts"] = {"ticket": 0} # ★購入回数リセット
        data["points"] += 100
        data["total_points"] += 100
        save_data(data)
        return True, 100
    return False, 0

# --- 3. アプリ画面構築 ---
st.set_page_config(page_title="Life Quest V10", page_icon="⚔️")

st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; border: 2px solid #333; }
    .status-box { padding: 15px; border-radius: 10px; background-color: #f0f2f6; border: 2px solid #ccc; margin-bottom: 20px; }
    .card { background-color: #fff; padding: 10px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); border: 1px solid #ddd; text-align: center; margin-bottom: 10px;}
    .boss-bar { width: 100%; background-color: #ddd; border-radius: 10px; height: 20px; overflow: hidden; margin-bottom: 10px; }
    .boss-hp { height: 100%; background-color: #e74c3c; transition: width 0.5s; }
</style>
""", unsafe_allow_html=True)

if 'data' not in st.session_state: st.session_state.data = load_data()
data = st.session_state.data
if "daily_shop_counts" not in data: data["daily_shop_counts"] = {"ticket": 0} # 補正

# サイドバー
with st.sidebar:
    st.title("🛡️ 勇者のステータス")
    st.markdown(f"""
    <div class="status-box">
        <h3>Lv. {data['level']}</h3>
        <p>💎 Pt: <b>{data['points']}</b></p>
        <p>🎫 チケ: <b>{data['items'].get('gacha_ticket', 0)}</b></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("🏆 **実績**")
    for ach in ACHIEVEMENTS:
        if ach["id"] in data["achievements"]:
            st.caption(f"✅ {ach['name']}")
    
    st.write("---")
    if st.button("🔄 データ更新"): st.rerun()

st.title("⚔️ Life Quest: X (V10)")

is_new_day, bonus = check_login_bonus(data)
if is_new_day:
    st.balloons()
    st.success(f"🎁 ログインボーナス！ +{bonus}pt & 購入回数リセット")

# レイドボス
boss = data["raid_boss"]
if boss["hp"] > 0:
    st.markdown(f"### 😈 レイドボス: {boss['name']} (Lv.{boss['defeat_count']+1})")
    hp_per = max(0, boss["hp"] / boss["max_hp"])
    st.markdown(f"""
    <div class="boss-bar"><div class="boss-hp" style="width: {hp_per*100}%;"></div></div>
    <p style="text-align:right;">HP: {boss['hp']} / {boss['max_hp']}</p>
    """, unsafe_allow_html=True)
else:
    st.success(f"🎉 {boss['name']} を討伐しました！")
    if st.button("報酬を受け取って次のボスへ"):
        data["items"]["gacha_ticket"] += 1
        boss["defeat_count"] += 1
        boss["max_hp"] += 2000
        boss["hp"] = boss["max_hp"]
        save_data(data)
        st.toast("討伐報酬: ガチャチケット GET!")
        st.rerun()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📜 クエスト", "🏪 ショップ", "🗺️ 冒険", "🔮 ガチャ", "📖 図鑑"])

# --- クエスト ---
with tab1:
    st.subheader("本日の任務")
    col1, col2 = st.columns(2)
    tasks = {
        "🧹 掃除": 30, "📚 勉強": 50, "💻 コード書き": 80, 
        "💪 筋トレ": 40, "🚶 ウォーキング": 100
    }
    
    for i, (task_name, base_reward) in enumerate(tasks.items()):
        with col1 if i%2==0 else col2:
            bonus_rate = calculate_bonus(data, task_name)
            final_reward = int(base_reward * (1 + bonus_rate))
            
            label = f"{task_name}\n(+{final_reward}pt)"
            if bonus_rate > 0:
                label += f" 🔥+{int(bonus_rate*100)}%"
            
            if st.button(label):
                data["points"] += final_reward
                data["total_points"] += final_reward
                data["xp"] += 10
                data["task_counts"][task_name] = data["task_counts"].get(task_name, 0) + 1
                
                if boss["hp"] > 0:
                    dmg = 50 + (data["level"] * 5)
                    boss["hp"] -= dmg
                    st.toast(f"ボスに {dmg} ダメージ！")
                
                if data["xp"] // 100 > data["level"]:
                    data["level"] += 1
                    st.toast(f"レベルアップ！ Lv.{data['level']}")
                    
                save_data(data)
                st.rerun()

# --- ショップ (1日1回制限) ---
with tab2:
    st.subheader("🏪 アイテムショップ")
    c1, c2 = st.columns(2)
    with c1:
        bought_count = data["daily_shop_counts"].get("ticket", 0)
        limit = 1 # ★購入制限数
        
        st.info(f"🎫 ガチャチケット (150pt)\n残り: {limit - bought_count}回")
        
        can_buy_ticket = (data["points"] >= 150) and (bought_count < limit)
        
        if st.button("購入する", disabled=not can_buy_ticket):
            data["points"] -= 150
            data["items"]["gacha_ticket"] = data["items"].get("gacha_ticket", 0) + 1
            data["daily_shop_counts"]["ticket"] = bought_count + 1
            save_data(data)
            st.success("購入しました！")
            st.rerun()

# --- 冒険 (クールタイム実装) ---
with tab3:
    st.subheader("🗺️ モンスター派遣")
    
    # 冒険中かどうかチェック
    now = datetime.datetime.now()
    exp = data.get("expedition", {"active": False})
    
    if exp["active"]:
        # 終了時間を復元
        end_time = datetime.datetime.fromisoformat(exp["end_time"])
        
        if now >= end_time:
            # 帰還！
            st.success(f"おかえりなさい！ {exp['monster']} が帰還しました！")
            if st.button("報酬を受け取る"):
                reward = random.randint(100, 300) # 報酬
                data["points"] += reward
                data["expedition"] = {"active": False, "end_time": None, "monster": ""}
                save_data(data)
                st.balloons()
                st.toast(f"冒険報酬: {reward}pt")
                st.rerun()
        else:
            # 探索中
            remain = end_time - now
            mins = remain.seconds // 60
            secs = remain.seconds % 60
            st.info(f"🚀 {exp['monster']} が探索中です...")
            st.warning(f"帰還まで: {mins}分 {secs}秒")
            if st.button("更新"): st.rerun()
            
    else:
        # 出発画面
        if not data["monster_levels"]:
            st.warning("仲間がいません。")
        else:
            monster_names = list(data["monster_levels"].keys())
            selected_name = st.selectbox("派遣する仲間", monster_names)
            
            st.write("所要時間: **30分**")
            
            if st.button("出発！ (30分後に帰還)"):
                end_time = now + datetime.timedelta(minutes=30) # ★30分後
                data["expedition"] = {
                    "active": True, 
                    "end_time": end_time.isoformat(), 
                    "monster": selected_name
                }
                save_data(data)
                st.success("いってらっしゃい！")
                st.rerun()

# --- ガチャ (動画演出) ---
with tab4:
    st.subheader("召喚の間")
    c1, c2 = st.columns(2)
    
    def do_gacha(cost_pt=0, use_ticket=False):
        if use_ticket:
            data["items"]["gacha_ticket"] -= 1
        else:
            data["points"] -= cost_pt
            
        # ★動画演出★
        placeholder = st.empty()
        with placeholder.container():
            st.image(MONSTER_IMGS["GACHA_GIF"], caption="召喚中...", use_column_width=True)
            time.sleep(3.5) # 動画の長さに合わせて待つ
        placeholder.empty() # 動画を消す
        
        rarity, m = pull_gacha()
        
        current_lv = data["monster_levels"].get(m["name"], 0)
        data["monster_levels"][m["name"]] = current_lv + 1
        save_data(data)
        
        st.balloons()
        st.markdown(f"## ✨ {rarity} {m['name']}")
        if current_lv > 0:
            st.info(f"限界突破！ Lv.{current_lv} → Lv.{current_lv+1}")
        
        st.image(m["img"], width=250)
        st.caption(m["desc"])

    with c1:
        st.info("無料召喚 (1日1回)")
        if st.button("引く！", disabled=data["daily_gacha_done"], key="free"):
            data["daily_gacha_done"] = True
            do_gacha(0)
            st.rerun()
            
    with c2:
        has_ticket = data["items"].get("gacha_ticket", 0) > 0
        btn_label = "チケットで引く" if has_ticket else "200ptで引く"
        can_play = has_ticket or (data["points"] >= 200)
        
        if st.button(btn_label, disabled=not can_play, key="paid"):
            do_gacha(200, use_ticket=has_ticket)
            st.rerun()

# --- 図鑑 ---
with tab5:
    st.subheader("仲間の記録")
    cols = st.columns(3)
    my_monsters = data["monster_levels"]
    
    i = 0
    for rarity in ["UR", "SSR", "SR", "R", "N"]:
        for m in MONSTER_DB[rarity]:
            if m["name"] in my_monsters:
                lv = my_monsters[m["name"]]
                with cols[i % 3]:
                    st.markdown(f"""
                    <div class="card">
                        <div style="color:#888;">{rarity}</div>
                        <b>{m['name']}</b><br>
                        <span style="color:red;font-weight:bold;">Lv.{lv}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    st.image(m["img"], use_column_width=True)
                i += 1