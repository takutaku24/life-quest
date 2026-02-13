import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import random
import json
import time

# --- 1. 設定とデータ定義 ---
SHEET_NAME = "life_quest_db"

# モンスター図鑑（パッシブスキルを追加！）
# skill_type: "task_bonus" (特定タスク報酬UP), "all_bonus" (全タスク報酬UP)
MONSTER_DB = {
    "UR": [
        {"name": "🐲 伝説のドラゴン", "power": 10000, "skill": {"type": "all_bonus", "val": 0.2}, "desc": "全タスク報酬+20%！最強の古龍。", "img": "https://placehold.co/400x400/1a1a1a/e74c3c?text=Legendary+Dragon"},
        {"name": "🦄 虹色のユニコーン", "power": 9000, "skill": {"type": "task_bonus", "target": "勉強", "val": 0.5}, "desc": "勉強報酬+50%！幸運の幻獣。", "img": "https://placehold.co/400x400/ecf0f1/9b59b6?text=Rainbow+Unicorn"},
        {"name": "👼 大天使", "power": 9500, "skill": {"type": "task_bonus", "target": "ウォーキング", "val": 0.5}, "desc": "歩行報酬+50%！天界の使者。", "img": "https://placehold.co/400x400/f1c40f/ffffff?text=Archangel"}
    ],
    "SSR": [
        {"name": "🦁 百獣の王", "power": 5000, "skill": {"type": "task_bonus", "target": "筋トレ", "val": 0.3}, "desc": "筋トレ報酬+30%！王者の風格。", "img": "https://placehold.co/400x400/f39c12/2c3e50?text=Lion+King"},
        {"name": "🧛 ヴァンパイア", "power": 4800, "skill": {"type": "task_bonus", "target": "コード書き", "val": 0.3}, "desc": "コード報酬+30%！夜の貴族。", "img": "https://placehold.co/400x400/2c3e50/8e44ad?text=Vampire"},
        {"name": "🤖 未来ロボ", "power": 5500, "skill": {"type": "task_bonus", "target": "コード書き", "val": 0.3}, "desc": "コード報酬+30%！未来の技術。", "img": "https://placehold.co/400x400/34495e/3498db?text=Future+Robot"}
    ],
    "SR": [
        {"name": "🐺 シルバーウルフ", "power": 3000, "skill": {"type": "task_bonus", "target": "ウォーキング", "val": 0.15}, "desc": "歩行報酬+15%！孤高の狼。", "img": "https://placehold.co/400x400/95a5a6/ecf0f1?text=Silver+Wolf"},
        {"name": "🦅 グリフォン", "power": 3200, "skill": {"type": "task_bonus", "target": "筋トレ", "val": 0.15}, "desc": "筋トレ報酬+15%！空の王者。", "img": "https://placehold.co/400x400/d35400/f1c40f?text=Griffon"},
        {"name": "👻 ゴーストキング", "power": 2800, "skill": {"type": "task_bonus", "target": "掃除", "val": 0.15}, "desc": "掃除報酬+15%！お化けの王。", "img": "https://placehold.co/400x400/8e44ad/ecf0f1?text=Ghost+King"}
    ],
    "R": [
        {"name": "🐗 ワイルドボア", "power": 1200, "skill": {"type": "task_bonus", "target": "筋トレ", "val": 0.05}, "desc": "筋トレ報酬+5%！猪突猛進。", "img": "https://placehold.co/400x400/7f8c8d/c0392b?text=Wild+Boar"},
        {"name": "🕷️ 巨大グモ", "power": 1100, "skill": {"type": "task_bonus", "target": "コード書き", "val": 0.05}, "desc": "コード報酬+5%！ネットの住人。", "img": "https://placehold.co/400x400/2c3e50/27ae60?text=Giant+Spider"},
        {"name": "🦇 コウモリ", "power": 900, "skill": {"type": "task_bonus", "target": "ウォーキング", "val": 0.05}, "desc": "歩行報酬+5%！夜行性。", "img": "https://placehold.co/400x400/34495e/f1c40f?text=Bat"}
    ],
    "N": [
        {"name": "💧 スライム", "power": 100, "skill": {"type": "task_bonus", "target": "掃除", "val": 0.05}, "desc": "掃除報酬+5%！基本の魔物。", "img": "https://placehold.co/400x400/3498db/ffffff?text=Slime"},
        {"name": "🍄 きのこ", "power": 50, "skill": {"type": "task_bonus", "target": "勉強", "val": 0.05}, "desc": "勉強報酬+5%！毒はない。", "img": "https://placehold.co/400x400/e67e22/ecf0f1?text=Mushroom"},
        {"name": "🐛 けむし", "power": 30, "skill": {"type": "task_bonus", "target": "掃除", "val": 0.05}, "desc": "掃除報酬+5%！成長待ち。", "img": "https://placehold.co/400x400/27ae60/2c3e50?text=Caterpillar"}
    ]
}

GACHA_RATES = {"UR": 1, "SSR": 4, "SR": 15, "R": 30, "N": 50}

# 実績リスト
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

# データ読み込み（構造が変わるのでマイグレーション処理付き）
def load_data():
    try:
        sheet = get_database()
        data_str = sheet.acell('A1').value
        if data_str:
            data = json.loads(data_str)
            # --- データ構造のアップデート ---
            if "monster_levels" not in data:
                # 旧データ(list)から新データ(dict)へ移行
                new_levels = {}
                for m_name in data.get("collection", []):
                    new_levels[m_name] = new_levels.get(m_name, 0) + 1
                data["monster_levels"] = new_levels
            if "raid_boss" not in data:
                data["raid_boss"] = {"hp": 5000, "max_hp": 5000, "name": "魔王・怠惰", "defeat_count": 0}
            if "achievements" not in data: data["achievements"] = []
            if "task_counts" not in data: data["task_counts"] = {}
            if "total_points" not in data: data["total_points"] = data["points"]
            return data
    except: pass
    
    # 初期データ
    return {
        "points": 0, "total_points": 0, "xp": 0, "level": 1, 
        "last_login": "", 
        "monster_levels": {}, # {名前: レベル}
        "daily_gacha_done": False,
        "items": {"gacha_ticket": 0},
        "raid_boss": {"hp": 5000, "max_hp": 5000, "name": "魔王・怠惰", "defeat_count": 0},
        "achievements": [],
        "task_counts": {} # {タスク名: 回数}
    }

# データ保存
def save_data(data):
    try:
        # 実績解除チェック
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
        # モンスターデータを検索
        monster_info = None
        for rarity in MONSTER_DB:
            for m in MONSTER_DB[rarity]:
                if m["name"] == m_name:
                    monster_info = m
                    break
        
        if monster_info and "skill" in monster_info:
            skill = monster_info["skill"]
            # レベル補正: Lv1で1倍, Lv10で2倍
            level_factor = 1.0 + (level - 1) * 0.1
            
            if skill["type"] == "all_bonus":
                bonus_rate += skill["val"] * level_factor
            elif skill["type"] == "task_bonus":
                # タスク名にキーワードが含まれていれば適用（"掃除" in "掃除 (5分)"）
                if skill.get("target") in task_name_part:
                    bonus_rate += skill["val"] * level_factor
                    
    return bonus_rate

# ガチャロジック
def pull_gacha():
    rarity = random.choices(list(GACHA_RATES.keys()), weights=list(GACHA_RATES.values()), k=1)[0]
    monster_obj = random.choice(MONSTER_DB[rarity])
    return rarity, monster_obj

# ログインボーナス
def check_login_bonus(data):
    today = str(datetime.date.today())
    if data["last_login"] != today:
        data["last_login"] = today
        data["daily_gacha_done"] = False
        data["points"] += 100
        data["total_points"] += 100
        save_data(data)
        return True, 100
    return False, 0

# --- 3. アプリ画面構築 ---
st.set_page_config(page_title="Life Quest V9", page_icon="⚔️")

# CSS
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
if "items" not in data: data["items"] = {"gacha_ticket": 0} 

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
    
    st.write("🏆 **獲得した実績**")
    unlocked_names = []
    for ach in ACHIEVEMENTS:
        if ach["id"] in data["achievements"]:
            st.caption(f"✅ {ach['name']}")
    
    st.write("---")
    if st.button("🔄 データ更新"): st.rerun()

st.title("⚔️ Life Quest: Ultimate")

# ログインボーナス
is_new_day, bonus = check_login_bonus(data)
if is_new_day:
    st.balloons()
    st.success(f"🎁 ログインボーナス！ +{bonus}pt")

# --- レイドボス表示 ---
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
        boss["max_hp"] += 2000 # 次は強くなる
        boss["hp"] = boss["max_hp"]
        save_data(data)
        st.toast("討伐報酬: ガチャチケット GET!")
        st.rerun()

# タブ
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📜 クエスト", "🏪 ショップ", "🗺️ 冒険", "🔮 ガチャ", "📖 図鑑"])

# --- クエスト ---
with tab1:
    st.subheader("本日の任務")
    st.caption("モンスターを持っていると応援ボーナスがつきます！")
    
    col1, col2 = st.columns(2)
    tasks = {
        "🧹 掃除": 30, "📚 勉強": 50, "💻 コード書き": 80, 
        "💪 筋トレ": 40, "🚶 ウォーキング": 100
    }
    
    for i, (task_name, base_reward) in enumerate(tasks.items()):
        with col1 if i%2==0 else col2:
            # パッシブボーナス計算
            bonus_rate = calculate_bonus(data, task_name)
            final_reward = int(base_reward * (1 + bonus_rate))
            
            label = f"{task_name}\n(+{final_reward}pt)"
            if bonus_rate > 0:
                label += f" 🔥+{int(bonus_rate*100)}%"
            
            if st.button(label):
                data["points"] += final_reward
                data["total_points"] += final_reward
                data["xp"] += 10
                
                # タスク回数記録
                data["task_counts"][task_name] = data["task_counts"].get(task_name, 0) + 1
                
                # ボスダメージ
                if boss["hp"] > 0:
                    dmg = 50 + (data["level"] * 5)
                    boss["hp"] -= dmg
                    st.toast(f"ボスに {dmg} ダメージ！")
                
                if data["xp"] // 100 > data["level"]:
                    data["level"] += 1
                    st.toast(f"レベルアップ！ Lv.{data['level']}")
                    
                save_data(data)
                st.rerun()

# --- ショップ ---
with tab2:
    st.subheader("🏪 アイテムショップ")
    c1, c2 = st.columns(2)
    with c1:
        st.info("🎫 ガチャチケット (150pt)")
        if st.button("購入する", disabled=data["points"] < 150):
            data["points"] -= 150
            data["items"]["gacha_ticket"] = data["items"].get("gacha_ticket", 0) + 1
            save_data(data)
            st.success("購入しました！")
            st.rerun()

# --- 冒険 ---
with tab3:
    st.subheader("🗺️ モンスター派遣")
    if not data["monster_levels"]:
        st.warning("仲間がいません。")
    else:
        # ドロップダウン用リスト作成
        monster_names = list(data["monster_levels"].keys())
        selected_name = st.selectbox("派遣する仲間", monster_names)
        
        # 戦闘力計算
        base_power = 100
        for r in MONSTER_DB:
            for m in MONSTER_DB[r]:
                if m["name"] == selected_name:
                    base_power = m["power"]
        
        lv = data["monster_levels"][selected_name]
        final_power = base_power * (1 + (lv * 0.1)) # レベルで強くなる
        
        st.write(f"Lv.{lv} / 戦闘力: **{int(final_power)}**")
        
        if st.button("出発！"):
            with st.spinner("探索中..."):
                time.sleep(1.5)
                success_rate = 30 + (lv * 5) # レベルが高いほど成功しやすい
                if random.randint(1, 100) <= min(success_rate, 90):
                    reward = int(final_power / 10)
                    data["points"] += reward
                    data["total_points"] += reward
                    st.balloons()
                    st.success(f"大成功！ +{reward}pt")
                    save_data(data)
                else:
                    st.error("失敗... 何もなかった。")

# --- ガチャ ---
with tab4:
    st.subheader("召喚の間")
    c1, c2 = st.columns(2)
    
    # ガチャ実行関数
    def do_gacha(cost_pt=0, use_ticket=False):
        if use_ticket:
            data["items"]["gacha_ticket"] -= 1
        else:
            data["points"] -= cost_pt
            
        with st.spinner("召喚魔法詠唱中..."):
            time.sleep(2)
        
        rarity, m = pull_gacha()
        
        # 被り判定
        is_new = m["name"] not in data["monster_levels"]
        current_lv = data["monster_levels"].get(m["name"], 0)
        data["monster_levels"][m["name"]] = current_lv + 1
        
        save_data(data)
        
        st.balloons()
        if is_new:
            st.markdown(f"## ✨ NEW! {rarity} {m['name']}")
        else:
            st.markdown(f"## ⚡ 限界突破! {m['name']}")
            st.info(f"レベルが {current_lv} → {current_lv+1} に上がった！")
        
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
                    with st.expander("能力"):
                        st.write(f"基礎戦闘力: {m['power']}")
                        s = m['skill']
                        if s['type'] == 'all_bonus':
                            st.write(f"🔥 全報酬 +{int(s['val']*100)}%")
                        else:
                            st.write(f"✨ {s['target']}報酬 +{int(s['val']*100)}%")
                i += 1