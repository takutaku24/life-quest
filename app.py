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

# ★最新の正しいIDです！
SHEET_ID = "1FvqLUrkR_YYk_azwI35rGr6_Y2swgUp1mawfJget5KU"

# 画像素材
IMGS = {
    "CAPSULE_BLUE": "https://cdn-icons-png.flaticon.com/512/3503/3503202.png", # 青カプセル
    "CAPSULE_GOLD": "https://cdn-icons-png.flaticon.com/512/3503/3503222.png", # 金カプセル
    "CAPSULE_RAINBOW": "https://cdn-icons-png.flaticon.com/512/8617/8617997.png", # 虹カプセル
    "POTION": "https://cdn-icons-png.flaticon.com/512/867/867927.png",
    "MEAT": "https://cdn-icons-png.flaticon.com/512/1046/1046774.png",
    "SWORD": "https://cdn-icons-png.flaticon.com/512/867/867375.png",
    "SHIELD": "https://cdn-icons-png.flaticon.com/512/2553/2553641.png",
    "GACHA_GIF": "https://media.tenor.com/JdJOQWqH3yUAAAAM/summon-summoning.gif"
}

# モンスターDB
MONSTER_DB = {
    "UR": [
        {"name": "🐲 伝説のドラゴン", "power": 10000, "skill": {"type": "all_bonus", "val": 0.2}, "desc": "全タスク報酬+20%！最強の古龍。", "img": "https://images.unsplash.com/photo-1599725427295-584a96319d69?w=400"},
        {"name": "👼 大天使", "power": 9500, "skill": {"type": "task_bonus", "target": "ウォーキング", "val": 0.5}, "desc": "歩行報酬+50%！天界の使者。", "img": "https://placehold.co/400x400/f1c40f/ffffff?text=Archangel"}
    ],
    "SSR": [
        {"name": "🤖 未来ロボ", "power": 5500, "skill": {"type": "task_bonus", "target": "コード書き", "val": 0.3}, "desc": "コード報酬+30%！未来の技術。", "img": "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=400"},
        {"name": "🦁 百獣の王", "power": 5000, "skill": {"type": "task_bonus", "target": "筋トレ", "val": 0.3}, "desc": "筋トレ報酬+30%！王者の風格。", "img": "https://placehold.co/400x400/f39c12/2c3e50?text=Lion+King"}
    ],
    "SR": [
        {"name": "🐺 シルバーウルフ", "power": 3000, "skill": {"type": "task_bonus", "target": "ウォーキング", "val": 0.15}, "desc": "歩行報酬+15%！孤高の狼。", "img": "https://images.unsplash.com/photo-1590420485404-f86f2f12c6a0?w=400"},
        {"name": "🦅 グリフォン", "power": 3200, "skill": {"type": "task_bonus", "target": "筋トレ", "val": 0.15}, "desc": "筋トレ報酬+15%！空の王者。", "img": "https://placehold.co/400x400/d35400/f1c40f?text=Griffon"}
    ],
    "R": [
        {"name": "🐗 ワイルドボア", "power": 1200, "skill": {"type": "task_bonus", "target": "筋トレ", "val": 0.05}, "desc": "筋トレ報酬+5%！猪突猛進。", "img": "https://images.unsplash.com/photo-1588636402377-59f63567a216?w=400"},
        {"name": "🕷️ 巨大グモ", "power": 1100, "skill": {"type": "task_bonus", "target": "コード書き", "val": 0.05}, "desc": "コード報酬+5%！ネットの住人。", "img": "https://placehold.co/400x400/2c3e50/27ae60?text=Giant+Spider"},
        {"name": "🦇 コウモリ", "power": 900, "skill": {"type": "task_bonus", "target": "ウォーキング", "val": 0.05}, "desc": "歩行報酬+5%！夜行性。", "img": "https://placehold.co/400x400/34495e/f1c40f?text=Bat"}
    ],
    "N": [
        {"name": "💧 スライム", "power": 100, "skill": {"type": "task_bonus", "target": "掃除", "val": 0.05}, "desc": "掃除報酬+5%！基本の魔物。", "img": "https://images.unsplash.com/photo-1518020382113-a7e8fc38eac9?w=400"},
        {"name": "🍄 きのこ", "power": 50, "skill": {"type": "task_bonus", "target": "勉強", "val": 0.05}, "desc": "勉強報酬+5%！毒はない。", "img": "https://placehold.co/400x400/e67e22/ecf0f1?text=Mushroom"}
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

# データ読み込み（構造更新対応）
def load_data():
    try:
        sheet = get_database()
        data_str = sheet.acell('A1').value
        if data_str:
            data = json.loads(data_str)
            # --- 新機能用のデータ初期化 ---
            if "items" not in data: data["items"] = {"gacha_ticket": 0}
            if "monster_levels" not in data: data["monster_levels"] = {}
            if "raid_boss" not in data: data["raid_boss"] = {"hp": 5000, "max_hp": 5000, "name": "魔王・怠惰", "defeat_count": 0}
            if "achievements" not in data: data["achievements"] = []
            if "task_counts" not in data: data["task_counts"] = {}
            if "total_points" not in data: data["total_points"] = data["points"]
            if "expedition" not in data: data["expedition"] = {"active": False, "end_time": None, "monster": ""}
            if "daily_shop_counts" not in data: data["daily_shop_counts"] = {"ticket": 0}
            
            # V12追加項目
            if "equipment" not in data: data["equipment"] = {"weapon": None, "armor": None} # 装備
            if "active_buffs" not in data: data["active_buffs"] = {} # ポーション効果
            if "mission_progress" not in data: data["mission_progress"] = {"daily": {}, "weekly": {}, "last_login": "", "last_week": 0}
            if "bg_theme" not in data: data["bg_theme"] = "default"
            
            return data
    except Exception as e:
        print(f"Load Error: {e}")
        pass
    
    # 完全初期データ
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
        "daily_shop_counts": {"ticket": 0},
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

# ボーナス計算 (ポーション + 装備 + モンスター)
def calculate_bonus(data, task_name_part):
    bonus_rate = 0.0
    
    # 1. モンスターパッシブ
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

    # 2. 装備ボーナス
    if data["equipment"]["weapon"] == "勇者の剣": bonus_rate += 0.1
    if data["equipment"]["armor"] == "王者の盾": bonus_rate += 0.05
    
    # 3. ポーション効果 (時間制限)
    now = datetime.datetime.now().isoformat()
    if "potion" in data["active_buffs"]:
        end_time = data["active_buffs"]["potion"]
        if now < end_time:
            bonus_rate += 1.0 # +100% (2倍)
        else:
            del data["active_buffs"]["potion"] # 期限切れ削除
            
    return bonus_rate

# ミッション更新
def update_mission(data, action_type, val=1):
    today = str(datetime.date.today())
    week_num = datetime.date.today().isocalendar()[1]
    
    # デイリーリセット
    if data["mission_progress"]["last_login"] != today:
        data["mission_progress"]["daily"] = {}
        data["mission_progress"]["last_login"] = today
        
    # ウィークリーリセット
    if data["mission_progress"]["last_week"] != week_num:
        data["mission_progress"]["weekly"] = {}
        data["mission_progress"]["last_week"] = week_num

    # 進捗加算
    prog = data["mission_progress"]
    prog["daily"][action_type] = prog["daily"].get(action_type, 0) + val
    prog["weekly"][action_type] = prog["weekly"].get(action_type, 0) + val
    
    # 報酬チェックはUI側で行う
    return data

# ガチャロジック
def pull_gacha():
    rarity = random.choices(list(GACHA_RATES.keys()), weights=list(GACHA_RATES.values()), k=1)[0]
    monster_obj = random.choice(MONSTER_DB[rarity])
    return rarity, monster_obj

# --- アプリ画面構築 ---
st.set_page_config(page_title="Life Quest: Ultimate", page_icon="⚔️")

# CSS (テーマ適用)
if 'data' not in st.session_state: st.session_state.data = load_data()
data = st.session_state.data
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
update_mission(data, "d_login", 1) # ログインミッション
today = str(datetime.date.today())
if data["last_login"] != today:
    data["last_login"] = today
    data["daily_gacha_done"] = False
    data["daily_shop_counts"] = {"ticket": 0}
    data["points"] += 100
    st.balloons()
    st.success("🎁 ログインボーナス！ +100pt")
    save_data(data)

# サイドバー
with st.sidebar:
    st.title("🛡️ ステータス")
    # 装備表示
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
    
    # バフ表示
    now = datetime.datetime.now().isoformat()
    if "potion" in data["active_buffs"]:
        if now < data["active_buffs"]["potion"]:
            st.warning("🔥 やる気ポーション有効中！ (報酬2倍)")
    
    if st.button("🔄 データ手動保存"): 
        save_data(data)
        st.success("保存しました")

st.title("⚔️ Life Quest: Ultimate")

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

# タブメニュー
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
                data["points"] += final
                data["total_points"] += final
                data["xp"] += 10
                data["task_counts"][t_name] = data["task_counts"].get(t_name, 0) + 1
                
                # ボスダメージ
                dmg = 50 + (data["level"] * 5)
                if boss["hp"] > 0: boss["hp"] -= dmg
                
                # ミッション更新
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
    
    st.write("▼ **デイリー**")
    for m in MISSIONS["daily"]:
        prog = data["mission_progress"]["daily"].get(m["id"], 0)
        done = prog >= m["target"]
        claimed = f"{m['id']}_claimed" in data["mission_progress"]["daily"]
        
        col_m1, col_m2 = st.columns([3, 1])
        col_m1.progress(min(prog/m["target"], 1.0), text=f"{m['desc']} ({prog}/{m['target']})")
        
        if done and not claimed:
            if col_m2.button("受取", key=m["id"]):
                data["points"] += m["reward_pt"]
                data["mission_progress"]["daily"][f"{m['id']}_claimed"] = True
                save_data(data)
                st.rerun()
        elif claimed:
            col_m2.caption("受取済")
            
    st.write("▼ **ウィークリー**")
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

# --- 3. ショップ ---
with tabs[2]:
    st.subheader("🏪 雑貨屋")
    c1, c2 = st.columns(2)
    
    # ガチャチケ
    with c1:
        st.markdown(f"**🎫 ガチャチケ** (150pt)")
        if st.button("購入", key="buy_ticket", disabled=data["points"]<150):
            data["points"] -= 150
            data["items"]["gacha_ticket"] = data["items"].get("gacha_ticket", 0) + 1
            save_data(data)
            st.rerun()
            
    # ポーション
    with c2:
        st.markdown(f"**🧪 やる気ポーション** (300pt)<br>1時間獲得ポイント2倍", unsafe_allow_html=True)
        if st.button("購入＆使用", key="buy_potion", disabled=data["points"]<300):
            data["points"] -= 300
            end_time = datetime.datetime.now() + datetime.timedelta(hours=1)
            data["active_buffs"]["potion"] = end_time.isoformat()
            save_data(data)
            st.success("ポーションを使用した！やる気がみなぎる！")
            st.rerun()
            
    st.markdown("---")
    st.subheader("⚔️ 装備ショップ")
    e1, e2 = st.columns(2)
    with e1:
        st.image(IMGS["SWORD"], width=50)
        if st.button("勇者の剣 (2000pt)", disabled=data["points"]<2000 or data["equipment"]["weapon"]=="勇者の剣"):
            data["points"] -= 2000
            data["equipment"]["weapon"] = "勇者の剣"
            save_data(data)
            st.rerun()
    with e2:
        st.image(IMGS["SHIELD"], width=50)
        if st.button("王者の盾 (1500pt)", disabled=data["points"]<1500 or data["equipment"]["armor"]=="王者の盾"):
            data["points"] -= 1500
            data["equipment"]["armor"] = "王者の盾"
            save_data(data)
            st.rerun()
            
    st.markdown("---")
    st.subheader("🏠 テーマ変更")
    if st.button("ダークモード (500pt)", disabled=data["points"]<500):
        data["points"] -= 500
        data["bg_theme"] = "dark"
        save_data(data)
        st.rerun()

# --- 4. 冒険 (6時間) ---
with tabs[3]:
    st.subheader("🗺️ 冒険")
    now = datetime.datetime.now()
    exp = data.get("expedition", {"active": False})
    
    if exp["active"]:
        end_time = datetime.datetime.fromisoformat(exp["end_time"])
        if now >= end_time:
            # 帰還処理
            is_success = random.randint(1, 100) <= 30 # 30%で大成功
            base_reward = 500
            
            st.balloons()
            if is_success:
                st.success(f"大成功！！ {exp['monster']} が宝箱を見つけた！")
                st.write("獲得: 1000pt + ガチャチケット1枚")
                data["points"] += 1000
                data["items"]["gacha_ticket"] = data["items"].get("gacha_ticket", 0) + 1
            else:
                st.info(f"おかえり！ {exp['monster']} が帰ってきた。")
                st.write("獲得: 500pt")
                data["points"] += 500
            
            # ミッション
            update_mission(data, "w_task20", 1) # 冒険もタスク扱いで加算(簡易)
            
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
            st.write("所要時間: **6時間**")
            if st.button("出発！"):
                end = now + datetime.timedelta(hours=6)
                data["expedition"] = {"active": True, "end_time": end.isoformat(), "monster": sel}
                save_data(data)
                st.rerun()

# --- 5. ガチャ (演出強化) ---
with tabs[4]:
    st.subheader("召喚の間")
    
    # ガチャ実行関数
    def run_gacha_anim(rarity):
        placeholder = st.empty()
        # 1. 回す動画
        placeholder.image(IMGS["GACHA_GIF"], use_column_width=True)
        time.sleep(2.5)
        
        # 2. カプセル落下
        capsule_img = IMGS["CAPSULE_BLUE"]
        if rarity == "UR": capsule_img = IMGS["CAPSULE_RAINBOW"]
        elif rarity in ["SSR", "SR"]: capsule_img = IMGS["CAPSULE_GOLD"]
        
        placeholder.markdown(f"<div style='text-align:center;'><img src='{capsule_img}' width='200'></div>", unsafe_allow_html=True)
        time.sleep(1.0)
        return placeholder

    c1, c2 = st.columns(2)
    with c1:
        if st.button("無料 (1日1回)", disabled=data["daily_gacha_done"]):
            data["daily_gacha_done"] = True
            rarity, m = pull_gacha()
            ph = run_gacha_anim(rarity)
            
            # 結果
            ph.empty()
            st.image(m["img"], width=300)
            st.markdown(f"## {rarity} {m['name']}")
            data["monster_levels"][m["name"]] = data["monster_levels"].get(m["name"], 0) + 1
            update_mission(data, "d_gacha", 1)
            save_data(data)
            st.balloons()
            
    with c2:
        ticket = data["items"].get("gacha_ticket", 0)
        label = f"チケットで引く (残り{ticket})" if ticket > 0 else "200ptで引く"
        can_play = ticket > 0 or data["points"] >= 200
        
        if st.button(label, disabled=not can_play):
            if ticket > 0: data["items"]["gacha_ticket"] -= 1
            else: data["points"] -= 200
            
            rarity, m = pull_gacha()
            ph = run_gacha_anim(rarity)
            
            ph.empty()
            st.image(m["img"], width=300)
            st.markdown(f"## {rarity} {m['name']}")
            data["monster_levels"][m["name"]] = data["monster_levels"].get(m["name"], 0) + 1
            update_mission(data, "d_gacha", 1)
            save_data(data)
            st.balloons()

# --- 6. 記録 (グラフ) ---
with tabs[5]:
    st.subheader("📊 活動ログ")
    if data["task_counts"]:
        df = pd.DataFrame(list(data["task_counts"].items()), columns=["Task", "Count"])
        fig = px.pie(df, values='Count', names='Task', title='タスク比率')
        st.plotly_chart(fig)
    else:
        st.info("データがまだありません。")

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
