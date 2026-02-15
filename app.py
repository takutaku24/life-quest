import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import random
import json
import time
import pandas as pd
import plotly.express as px

--- 1. 設定とアセット (完全ドット絵 & 視認性強化) ---
★正しいスプレッドシートID
SHEET_ID = "1FvqLUrkR_YYk_azwI35rGr6_Y2swgUp1mawfJget5KU"

ドット絵風アセット
ASSETS = {
"BG_FOREST": "",
"BG_CAVE": "",
"BG_SEA": "",
"BG_VOLCANO": "",
"BG_CASTLE": "",

}

モンスターDB
MONSTER_DB = {
"UR": [
{"name": "伝説のドラゴン", "img": "🐲&font=roboto", "desc": "最強の古龍"},
{"name": "大天使", "img": "👼&font=roboto", "desc": "天界の使者"}
],
"SSR": [
{"name": "魔導ロボ", "img": "🤖&font=roboto", "desc": "古代兵器"},
{"name": "キングライオン", "img": "🦁&font=roboto", "desc": "百獣の王"}
],
"SR": [
{"name": "シルバーウルフ", "img": "🐺&font=roboto", "desc": "孤高の狼"},
{"name": "グリフォン", "img": "🦅&font=roboto", "desc": "空の王者"}
],
"R": [
{"name": "ワイルドボア", "img": "🐗&font=roboto", "desc": "突進攻撃"},
{"name": "スパイダー", "img": "🕷️&font=roboto", "desc": "森の住人"},
{"name": "バット", "img": "🦇&font=roboto", "desc": "吸血コウモリ"}
],
"N": [
{"name": "スライム", "img": "💧&font=roboto", "desc": "プルプルしている"},
{"name": "キノコ", "img": "🍄&font=roboto", "desc": "歩くキノコ"}
]
}

JOBS = {
"novice": {"name": "冒険者", "bonus": {}},
"warrior": {"name": "戦士", "bonus": {"筋トレ": 1.2}},
"mage": {"name": "魔導士", "bonus": {"勉強": 1.2}},
"thief": {"name": "盗賊", "bonus": {"掃除": 1.2}},
"jester": {"name": "遊び人", "bonus": {"all": 0.9}}
}

ミッション定義
MISSIONS = {
"daily": [
{"id": "d_login", "desc": "ログインする", "target": 1, "reward_pt": 50, "label": "50pt"},
{"id": "d_task3", "desc": "タスクを3回完了", "target": 3, "reward_pt": 100, "label": "100pt"},
{"id": "d_gacha", "desc": "ガチャを引く", "target": 1, "reward_pt": 50, "label": "50pt"}
],
"weekly": [
{"id": "w_task20", "desc": "週間タスク20回", "target": 20, "reward_item": "gacha_ticket", "amount": 1, "label": "チケ1枚"},
{"id": "w_boss", "desc": "ボスに1000ダメ", "target": 1000, "reward_item": "sr_ticket", "amount": 1, "label": "SRチケ"}
]
}

--- 2. システム関数 ---
def get_database():
scopes = ["", ""]
creds_dict = dict(st.secrets["gcp_service_account"])
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)
return client.open_by_key(SHEET_ID).sheet1

def load_data():
try:
sheet = get_database()
val = sheet.acell('A1').value
data = json.loads(val) if val else {}
except: data = {}

def save_data(data):
try:
st.toast("💾 Saving...", icon="💾")
sheet = get_database()
sheet.update_acell('A1', json.dumps(data, ensure_ascii=False))
except: pass

def update_mission(data, action_type, val=1):
today = str(datetime.date.today())
week = datetime.date.today().isocalendar()[1]

def check_shop_limit(data, item_key, limit_type, limit_count):
today = str(datetime.date.today())
key = f"{item_key}{limit_type}{today if limit_type=='daily' else ''}"
count = data["shop_counts"].get(key, 0)
return count < limit_count, key

def buy_item(data, key):
data["shop_counts"][key] = data["shop_counts"].get(key, 0) + 1

def calculate_bonus_rate(data, task_name):
rate = 1.0
job_info = JOBS.get(data["job"], JOBS["novice"])
if data["job"] == "jester":
if random.random() < 0.1:
st.toast("🎰 ラッキーパンチ！報酬5倍！", icon="🃏")
return 5.0
else: rate = 0.9
else:
for k, v in job_info["bonus"].items():
if k in task_name: rate += (v - 1.0)
combo = data["mission_progress"].get("combo", 0)
rate += min(combo * 0.01, 0.2)
return rate
--- 3. デザイン設定 (PC視認性改善版) ---
st.set_page_config(page_title="Life Quest: Remaster", page_icon="⚔️", layout="wide")

st.markdown("""

<style>
@import url('');

</style>

""", unsafe_allow_html=True)

if 'data' not in st.session_state: st.session_state.data = load_data()
data = st.session_state.data

today_str = str(datetime.date.today())
update_mission(data, "d_login", 1)

if data["mission_progress"]["last_login"] != today_str:
yesterday = str(datetime.date.today() - datetime.timedelta(days=1))
if data["mission_progress"]["last_login"] == yesterday:
data["mission_progress"]["combo"] = data["mission_progress"].get("combo", 0) + 1
else: data["mission_progress"]["combo"] = 1
data["mission_progress"]["last_login"] = today_str
data["daily_gacha_done"] = False
data["points"] += 100
save_data(data)
st.toast(f"🎁 Login Bonus! Combo: {data['mission_progress']['combo']}日目", icon="🔥")

--- 4. サイドバー ---
with st.sidebar:
lv = data["level"]
hero_img = ASSETS["HERO_1"]
if lv >= 10: hero_img = ASSETS["HERO_2"]
if lv >= 30: hero_img = ASSETS["HERO_3"]
if lv >= 50: hero_img = ASSETS["HERO_4"]

--- 5. メイン画面 ---
fl = data["dungeon"]["floor"]
bg_url = ASSETS["BG_FOREST"]
area_name = "森"
if 11 <= fl <= 20: bg_url = ASSETS["BG_CAVE"]; area_name = "洞窟"
elif 21 <= fl <= 30: bg_url = ASSETS["BG_SEA"]; area_name = "海"
elif 31 <= fl <= 40: bg_url = ASSETS["BG_VOLCANO"]; area_name = "火山"
elif fl >= 41: bg_url = ASSETS["BG_CASTLE"]; area_name = "魔王城"

st.image(bg_url, use_column_width=True, caption=f"Floor {fl} : {area_name}")
if data["pet"]["active"]: st.info(f"🐶 {data['pet']['active']} がついている！")

t1, t2, t3, t4, t5, t6 = st.tabs(["⚔️ 冒険", "🏪 店", "📅 任務", "🎰 ガチャ", "📊 記録", "📖 図鑑"])

with t1:
if fl % 10 == 0 and data["dungeon"]["status"] != "boss_cleared":
st.error(f"⚠️ {fl}階の門番が現れた！")
c1, c2 = st.columns(2)
with c1: st.write(f"勇者 Power: {10 + lv}")
with c2: st.write(f"門番 Power: {10 + fl}")
if st.button("ダイス勝負！"):
h_roll = random.randint(1, 6) + 10 + lv
e_roll = random.randint(1, 6) + 10 + fl
st.write(f"結果: {h_roll} vs {e_roll}")
if h_roll >= e_roll:
st.balloons(); st.success("勝利！先へ進む！")
data["dungeon"]["floor"] += 1
data["dungeon"]["status"] = "exploring"
data["items"]["gacha_ticket"] += 1
save_data(data); st.rerun()
else:
st.error("敗北… キャンプに戻る")
data["dungeon"]["floor"] = max(1, (fl // 5) * 5)
save_data(data); st.rerun()
else:
tasks = {"🧹 掃除": 30, "📚 勉強": 50, "💻 仕事": 80, "💪 筋トレ": 40, "🚶 ウォーキング": 100}
cols = st.columns(2)
for i, (t, base) in enumerate(tasks.items()):
rate = calculate_bonus_rate(data, t)
pt = int(base * rate)
with cols[i%2]:
label = f"{t} (+{pt}pt)"
if rate > 1.0: label += " 🔥"
if st.button(label, key=f"t_{i}"):
data["points"] += pt
data["total_points"] += pt
data["xp"] += 10
data["task_counts"][t] = data["task_counts"].get(t, 0) + 1
data["point_history"][today_str] = data["point_history"].get(today_str, 0) + pt
data["dungeon"]["floor"] += 1
if data["dungeon"]["floor"] % 10 == 0: data["dungeon"]["status"] = "boss"
if data["xp"] >= lv * 100: data["level"] += 1; data["xp"] = 0; st.toast("Level Up!")
if data["raid_boss"]["hp"] > 0: data["raid_boss"]["hp"] -= pt
update_mission(data, "d_task3", 1); update_mission(data, "w_task20", 1)
save_data(data); st.rerun()

with t2:
st.subheader("🏪 ドット屋")
can_buy, key = check_shop_limit(data, "ticket", "daily", 1)
label = "🎫 ガチャチケ (150pt)" + (" 【売切】" if not can_buy else "")
if st.button(label, disabled=not can_buy or data["points"]<150):
data["points"] -= 150; data["items"]["gacha_ticket"] += 1; buy_item(data, key); save_data(data); st.success("購入！"); st.rerun()
c1, c2 = st.columns(2)
with c1:
if st.button("🧪 ポーション (300pt)", disabled=data["points"]<300):
data["points"] -= 300; end = datetime.datetime.now() + datetime.timedelta(hours=1); data["active_buffs"]["potion"] = end.isoformat(); save_data(data); st.success("やる気UP！"); st.rerun()
with c2:
if st.button("⏳ 砂時計 (500pt)", disabled=data["points"]<500):
data["points"] -= 500; data["mission_progress"]["daily"] = {}; save_data(data); st.success("時間を戻した！"); st.rerun()
can_sr, key_sr = check_shop_limit(data, "sr", "weekly", 1)
if st.button(f"🎫 SR確定 (1000pt) {'【売切】' if not can_sr else ''}", disabled=not can_sr or data["points"]<1000):
data["points"] -= 1000; data["items"]["sr_ticket"] += 1; buy_item(data, key_sr); save_data(data); st.rerun()

with t3:
st.subheader("📅 ミッション")
st.write("▼ デイリー")
for m in MISSIONS["daily"]:
prog = data["mission_progress"]["daily"].get(m["id"], 0)
claimed = data["mission_progress"]["daily"].get(f"{m['id']}_claimed", False)
st.write(f"・{m['desc']} ({prog}/{m['target']})")
if prog >= m["target"] and not claimed:
if st.button("受取", key=m["id"]):
data["points"] += m["reward_pt"]; data["mission_progress"]["daily"][f"{m['id']}_claimed"] = True; save_data(data); st.rerun()
st.write("▼ 週間レイドボス")
boss = data["raid_boss"]
st.write(f"😈 {boss['name']} (HP: {max(0,boss['hp'])})")
st.progress(max(0, boss["hp"]/boss["max_hp"]))
if boss["hp"] <= 0 and not boss.get("reward_claimed"):
if st.button("報酬 (SRチケ)"):
data["items"]["sr_ticket"] = data["items"].get("sr_ticket", 0) + 1; data["raid_boss"]["reward_claimed"] = True; save_data(data); st.rerun()

with t4:
st.subheader("🎰 召喚")
anim_box = st.empty()
c1, c2 = st.columns(2)
with c1:
done = data.get("daily_gacha_done", False)
if st.button("無料 (1日1回)", disabled=done):
data["daily_gacha_done"] = True; anim_box.image(ASSETS["CHEST_CLOSED"], width=200); time.sleep(1); anim_box.image(ASSETS["CHEST_OPEN"], width=200)
rarity = random.choices(["N", "R"], weights=[80, 20])[0]; m = random.choice(MONSTER_DB[rarity])
st.image(m["img"], width=100); st.write(f"Get! {m['name']}"); data["monster_levels"][m["name"]] = data["monster_levels"].get(m["name"], 0) + 1; update_mission(data, "d_gacha", 1); save_data(data)
with c2:
n = data["items"].get("gacha_ticket", 0)
if st.button(f"チケ召喚 (残{n})", disabled=n==0):
data["items"]["gacha_ticket"] -= 1; anim_box.image(ASSETS["CHEST_CLOSED"], width=200); time.sleep(1); anim_box.image(ASSETS["CHEST_OPEN"], width=200)
rarity = random.choices(["N", "R", "SR", "SSR", "UR"], weights=[50, 30, 15, 4, 1])[0]; m = random.choice(MONSTER_DB[rarity])
st.image(m["img"], width=100); st.write(f"Get! {m['name']}"); data["monster_levels"][m["name"]] = data["monster_levels"].get(m["name"], 0) + 1; update_mission(data, "d_gacha", 1); save_data(data)

with t5:
st.subheader("📊 記録")
if data["point_history"]:
df = pd.DataFrame(list(data["point_history"].items()), columns=["Date", "Points"])
st.plotly_chart(px.bar(df, x="Date", y="Points", title="日別Pt"), use_container_width=True)
if data["task_counts"]:
df2 = pd.DataFrame(list(data["task_counts"].items()), columns=["Task", "Count"])
st.plotly_chart(px.pie(df2, values='Count', names='Task', title="タスク比率"), use_container_width=True)

with t6:
st.subheader("📖 図鑑")
cols = st.columns(4)
i = 0
for r in ["UR", "SSR", "SR", "R", "N"]:
for m in MONSTER_DB[r]:
if m["name"] in data["monster_levels"]:
with cols[i%4]:
st.image(m["img"], width=60)
if st.button(m["name"], key=f"sel_{m['name']}"):
data["pet"]["active"] = m["name"]; save_data(data); st.success(f"相棒: {m['name']}"); st.rerun()
i+=1
