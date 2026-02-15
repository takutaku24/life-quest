import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime, random, json, time
import pandas as pd
import plotly.express as px

SHEET_ID = "1FvqLUrkR_YYk_azwI35rGr6_Y2swgUp1mawfJget5KU"

ASSETS = {
"BG": ["",
"",
"",
"",
""],
"HERO": ["",
"",
"",
""]
}

MONSTER = {
"UR": [{"name": "伝説のドラゴン", "img": ""}],
"N": [{"name": "スライム", "img": ""}]
}

JOBS = {"novice": "冒険者", "warrior": "戦士", "mage": "魔導士", "thief": "盗賊"}
def load_data():
try:
creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]),
scopes=["", ""])
sheet = gspread.authorize(creds).open_by_key(SHEET_ID).sheet1
val = sheet.acell('A1').value
data = json.loads(val) if val else {}
except: data = {}
defaults = {"points": 0, "xp": 0, "level": 1, "job": "novice", "dungeon": {"floor": 1},
"items": {"gacha_ticket": 0}, "mission_progress": {"last_login": "", "combo": 0},
"monster_levels": {}, "task_counts": {}, "point_history": {}}
for k, v in defaults.items():
if k not in data: data[k] = v
if "combo" not in data["mission_progress"]: data["mission_progress"]["combo"] = 0
return data

def save_data(data):
try:
creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]),
scopes=["", ""])
gspread.authorize(creds).open_by_key(SHEET_ID).sheet1.update_acell('A1', json.dumps(data, ensure_ascii=False))
st.toast("Saved")
except: pass

st.set_page_config(page_title="Life Quest", layout="wide")
st.markdown("<style>.stApp{background-color:#0e1117;color:#fff;}.pixel-card{background-color:#1a1c24;border:1px solid #fff;padding:10px;margin-bottom:10px;}</style>", unsafe_allow_html=True)

if 'data' not in st.session_state: st.session_state.data = load_data()
data = st.session_state.data
today = str(datetime.date.today())
with st.sidebar:
st.image(ASSETS["HERO"][min(data["level"]//10, 3)], width=100)
st.markdown(f"Lv.{data['level']} {JOBS.get(data['job'], '冒険者')}")
st.markdown(f"<div class='pixel-card'>💎 Pt: {data['points']}


🎫 Ticket: {data['items']['gacha_ticket']}


🔥 Combo: {data['mission_progress'].get('combo', 0)}日</div>", unsafe_allow_html=True)
if st.button("転職(戦士)"): data["job"] = "warrior"; save_data(data); st.rerun()

st.image(ASSETS["BG"][min((data["dungeon"]["floor"]-1)//10, 4)], use_column_width=True, caption=f"Floor {data['dungeon']['floor']}")

t1, t2, t3, t4 = st.tabs(["⚔️ 冒険", "🏪 店", "🎰 ガチャ", "📊 記録"])

with t1:
tasks = {"🧹 掃除": 30, "📚 勉強": 50, "💻 仕事": 80, "💪 筋トレ": 40, "🚶 ウォーキング": 100}
cols = st.columns(2)
for i, (name, base) in enumerate(tasks.items()):
with cols[i%2]:
if st.button(f"{name} (+{base})"):
data["points"] += base
data["point_history"][today] = data["point_history"].get(today, 0) + base
data["task_counts"][name] = data["task_counts"].get(name, 0) + 1
data["dungeon"]["floor"] += 1
if data["dungeon"]["floor"] % 10 == 0:
if random.random() > 0.4: st.success("Boss Win!"); data["items"]["gacha_ticket"] += 1
else: st.error("Lose..."); data["dungeon"]["floor"] -= 2
save_data(data); st.rerun()
with t2:
if st.button("🎫 チケ購入 (150pt)"):
if data["points"] >= 150:
data["points"] -= 150
data["items"]["gacha_ticket"] += 1
save_data(data)
st.rerun()

with t3:
if st.button(f"召喚 (残{data['items']['gacha_ticket']})"):
if data["items"]["gacha_ticket"] > 0:
data["items"]["gacha_ticket"] -= 1
m = random.choice(MONSTER["UR"] if random.random() > 0.8 else MONSTER["N"])
st.image(m["img"], width=150)
st.write(f"Get: {m['name']}")
data["monster_levels"][m["name"]] = data["monster_levels"].get(m["name"], 0) + 1
save_data(data)

with t4:
if data["point_history"]:
df = pd.DataFrame(list(data["point_history"].items()), columns=["Date", "Points"])
st.plotly_chart(px.bar(df, x="Date", y="Points", template="plotly_dark"))
with t2:
if st.button("🎫 チケ購入 (150pt)"):
if data["points"] >= 150:
data["points"] -= 150
data["items"]["gacha_ticket"] += 1
save_data(data)
st.rerun()

with t3:
if st.button(f"召喚 (残{data['items']['gacha_ticket']})"):
if data["items"]["gacha_ticket"] > 0:
data["items"]["gacha_ticket"] -= 1
m = random.choice(MONSTER["UR"] if random.random() > 0.8 else MONSTER["N"])
st.image(m["img"], width=150)
st.write(f"Get: {m['name']}")
data["monster_levels"][m["name"]] = data["monster_levels"].get(m["name"], 0) + 1
save_data(data)

with t4:
if data["point_history"]:
df = pd.DataFrame(list(data["point_history"].items()), columns=["Date", "Points"])
st.plotly_chart(px.bar(df, x="Date", y="Points", template="plotly_dark"))