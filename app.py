import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import random
import json
import time
import pandas as pd
import plotly.express as px

--- 1. Settings ---
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
"🚶+Novice",
"🗡️+Fighter",
"🛡️+Hero",
"👑+Legend"
]
}
MONSTER_DB = {
"UR": [{"name": "🐲 伝説のドラゴン", "img": "🐲"}],
"SSR": [{"name": "🤖 未来ロボ", "img": "🤖"}],
"SR": [{"name": "🐺 シルバーウルフ", "img": "🐺"}],
"R": [{"name": "🕷️ 巨大グモ", "img": "🕷️"}],
"N": [{"name": "💧 スライム", "img": "💧"}]
}

JOBS = {
"novice": {"name": "冒険者"},
"warrior": {"name": "戦士"},
"mage": {"name": "魔導士"},
"thief": {"name": "盗賊"},
"jester": {"name": "遊び人"}
}

--- 2. Database Functions ---
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
sheet = get_database()
sheet.update_acell('A1', json.dumps(data, ensure_ascii=False))
st.toast("💾 セーブ完了", icon="💾")
except: pass

--- 3. UI and Logic ---
st.set_page_config(page_title="Life Quest", layout="wide")
st.markdown("<style>.stApp{background-color:#0e1117;color:#fff;}.pixel-card{background-color:#1a1c24;border:2px solid #fff;padding:15px;margin-bottom:15px;}h1,h2,h3,p,label{color:#fff !important;}</style>", unsafe_allow_html=True)

if 'data' not in st.session_state: st.session_state.data = load_data()
data = st.session_state.data
today = str(datetime.date.today())
Sidebar
with st.sidebar:
st.image(ASSETS["HERO"][min(data["level"]//20, 3)], width=100)
st.markdown(f"Lv.{data['level']} 勇者\nJob: {JOBS.get(data['job'], {'name':'冒険者'})['name']}")
st.markdown(f"<div class='pixel-card'>💎 Pt: {data['points']}


🎫 チケ: {data['items']['gacha_ticket']}


🔥 コンボ: {data['mission_progress'].get('combo', 0)}日</div>", unsafe_allow_html=True)

Background
fl = data["dungeon"]["floor"]
st.image(ASSETS["BG"][min((fl-1)//10, 4)], use_column_width=True, caption=f"Floor {fl}")

Tabs
t1, t2, t3, t4 = st.tabs(["⚔️ 冒険", "🏪 ショップ", "🎰 ガチャ", "📊 記録"])

with t1:
tasks = {"🧹 掃除": 30, "📚 勉強": 50, "💻 仕事": 80, "💪 筋トレ": 40, "🚶 ウォーキング": 100}
cols = st.columns(2)
for i, (t, base) in enumerate(tasks.items()):
with cols[i%2]:
if st.button(f"{t} (+{base}pt)"):
data["points"] += base
data["point_history"][today] = data["point_history"].get(today, 0) + base
data["task_counts"][t] = data["task_counts"].get(t, 0) + 1
data["dungeon"]["floor"] += 1
# ボス戦
if data["dungeon"]["floor"] % 10 == 0:
if random.randint(1, 6) >= 3: st.success("ボスに勝利！チケGET"); data["items"]["gacha_ticket"] += 1
else: st.error("敗北… 3階層戻る"); data["dungeon"]["floor"] -= 3
save_data(data); st.rerun()

with t2:
if st.button("🎫 ガチャチケ購入 (150pt)"):
if data["points"] >= 150: data["points"] -= 150; data["items"]["gacha_ticket"] += 1; save_data(data); st.rerun()

with t3:
if st.button(f"ガチャを引く (残{data['items']['gacha_ticket']}枚)"):
if data["items"]["gacha_ticket"] > 0:
data["items"]["gacha_ticket"] -= 1
rarity = random.choices(["N", "R", "SR", "SSR", "UR"], weights=[50, 30, 15, 4, 1])[0]
m = random.choice(MONSTER_DB[rarity])
st.image(m["img"], width=150); st.write(f"Get! {m['name']}")
data["monster_levels"][m["name"]] = data["monster_levels"].get(m["name"], 0) + 1
save_data(data)

with t4:
if data["point_history"]:
df = pd.DataFrame(list(data["point_history"].items()), columns=["Date", "Points"])
st.plotly_chart(px.bar(df, x="Date", y="Points", title="日別Pt", template="plotly_dark"))