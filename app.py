import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import random
import json
import time
import pandas as pd
import plotly.express as px

SHEET_ID = "1FvqLUrkR_YYk_azwI35rGr6_Y2swgUp1mawfJget5KU"

ASSETS = {
"BG": [
"",
"",
"",
"",
""
],
"HERO": [
"",
"",
"",
""
]
}

MONSTER_DB = {
"UR": [{"name": "伝説のドラゴン", "img": ""}],
"SSR": [{"name": "未来ロボ", "img": ""}],
"SR": [{"name": "シルバーウルフ", "img": ""}],
"R": [{"name": "巨大グモ", "img": ""}],
"N": [{"name": "スライム", "img": ""}]
}

JOBS = { "novice": {"name": "冒険者", "bonus": {}}, "warrior": {"name": "戦士", "bonus": {"筋トレ": 1.2}}, "mage": {"name": "魔導士", "bonus": {"勉強": 1.2}}, "thief": {"name": "盗賊", "bonus": {"掃除": 1.2}} }


def get_database():
try:
creds_dict = dict(st.secrets["gcp_service_account"])
creds = Credentials.from_service_account_info(creds_dict,
scopes=["", ""])
return gspread.authorize(creds).open_by_key(SHEET_ID).sheet1
except: return None

def load_data():
sheet = get_database()
if not sheet: return {}
try:
val = sheet.acell('A1').value
data = json.loads(val) if val else {}
except: data = {}

def save_data(data):
try:
sheet = get_database()
if sheet:
sheet.update_acell('A1', json.dumps(data, ensure_ascii=False))
st.toast("Saved")
except: pass

st.set_page_config(page_title="Life Quest", layout="wide")
st.markdown("<style>.stApp{background-color:#0e1117;color:#fff;}.pixel-card{background-color:#1a1c24;border:2px solid #fff;padding:10px;margin-bottom:10px;}</style>", unsafe_allow_html=True)

if 'data' not in st.session_state: st.session_state.data = load_data()
data = st.session_state.data
today = str(datetime.date.today())

--- 3. UI AND GAMEPLAY ---
with st.sidebar:
st.image(ASSETS["HERO"][min(data["level"]//20, 3)], width=100)
st.markdown(f"Lv.{data['level']} 勇者")
st.markdown(f"<div class='pixel-card'>Pt: {data['points']}


Combo: {data['mission_progress']['combo']}日</div>", unsafe_allow_html=True)

fl = data["dungeon"]["floor"]
st.image(ASSETS["BG"][min((fl-1)//10, 4)], use_column_width=True, caption=f"Floor {fl}")

t1, t2, t3, t4, t5 = st.tabs(["⚔️ 冒険", "🏪 ショップ", "🎰 ガチャ", "📊 記録", "👹 レイド"])

with t1:
tasks = {"🧹 掃除": 30, "📚 勉強": 50, "💻 仕事": 80, "💪 筋トレ": 40, "🚶 ウォーキング": 100}
cols = st.columns(2)
for i, (name, base) in enumerate(tasks.items()):
bonus = 1.2 if name in JOBS.get(data["job"], {})["bonus"] else 1.0
val = int(base * bonus)
with cols[i%2]:
if st.button(f"{name} (+{val}pt)"):
data["points"] += val
data["point_history"][today] = data["point_history"].get(today, 0) + val
data["dungeon"]["floor"] += 1
if data["raid_boss"]["hp"] > 0: data["raid_boss"]["hp"] -= val
if data["dungeon"]["floor"] % 10 == 0:
if random.randint(1, 6) >= 3:
st.success("Win!"); data["items"]["gacha_ticket"] += 1
else:
st.error("Lose..."); data["dungeon"]["floor"] = max(1, data["dungeon"]["floor"] - 3)
save_data(data); st.rerun()

with t2:
if st.button("🎫 ガチャチケ (150pt)"):
if data["points"] >= 150:
data["points"] -= 150; data["items"]["gacha_ticket"] += 1
save_data(data); st.rerun()

with t3:
if st.button(f"召喚 (残:{data['items']['gacha_ticket']})"):
if data["items"]["gacha_ticket"] > 0:
data["items"]["gacha_ticket"] -= 1
rarity = random.choices(["N", "R", "SR", "SSR", "UR"], weights=[50, 30, 15, 4, 1])[0]
m = random.choice(MONSTER_DB[rarity])
st.image(m["img"], width=200); st.write(f"🎉 {m['name']}!")
data["monster_levels"][m["name"]] = data["monster_levels"].get(m["name"], 0) + 1
save_data(data)

with t4:
if data["point_history"]:
df = pd.DataFrame(list(data["point_history"].items()), columns=["Date", "Points"])
st.plotly_chart(px.bar(df, x="Date", y="Points", template="plotly_dark"))

with t5:
boss = data["raid_boss"]
st.subheader(f"Boss: {boss['name']}")
st.write(f"HP: {max(0, boss['hp'])} / {boss['max_hp']}")
st.progress(max(0, boss["hp"] / boss["max_hp"]))
st.info("タスクをこなすとボスのHPを削れます！")