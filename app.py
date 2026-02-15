import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime, random, json, time
import pandas as pd
import plotly.express as px

1. SETTINGS
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
],
"CHEST_CLOSED": "📦+CHEST",
"CHEST_OPEN": "✨+GET!!"
}

MONSTER_DB = {
"UR": [{"name": "🐲 伝説のドラゴン", "img": "🐲"}],
"SSR": [{"name": "🤖 未来ロボ", "img": "🤖"}],
"SR": [{"name": "🐺 シルバーウルフ", "img": "🐺"}],
"R": [{"name": "🕷️ 巨大グモ", "img": "🕷️"}],
"N": [{"name": "💧 スライム", "img": "💧"}]
}

JOBS = {
"novice": {"name": "冒険者", "bonus": {}},
"warrior": {"name": "戦士", "bonus": {"筋トレ": 1.2}},
"mage": {"name": "魔導士", "bonus": {"勉強": 1.2}},
"thief": {"name": "盗賊", "bonus": {"掃除": 1.2}},
"jester": {"name": "遊び人", "bonus": {"all": 0.9}}
} template="plotly_dark"))
承知いたしました。順調ですね！
それでは、**【パート2：裏側の仕組み】**をお送りします。

この部分は、スプレッドシートへの接続、データの自動修復、レベルアップやショップの制限などを司る、ゲームの「心臓部」になります。
さきほどのコードのすぐ下に続けて貼り付けてください。

--- 2. CORE FUNCTIONS ---
def get_database():
creds_dict = dict(st.secrets["gcp_service_account"])
creds = Credentials.from_service_account_info(creds_dict,
scopes=["", ""])
return gspread.authorize(creds).open_by_key(SHEET_ID).sheet1

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
st.toast("💾 Data Synced to Cloud")
except: pass

def check_shop_limit(data, item_key, limit_type, limit_count):
today = str(datetime.date.today())
key = f"{item_key}{limit_type}{today if limit_type=='daily' else ''}"
count = data["shop_counts"].get(key, 0)
return count < limit_count, key

def calculate_bonus(data, task_name):
rate = 1.0
job_info = JOBS.get(data["job"], JOBS["novice"])
for k, v in job_info.get("bonus", {}).items():
if k in task_name: rate += (v - 1.0)
rate += min(data["mission_progress"].get("combo", 0) * 0.01, 0.2)
return rate
お待たせしました。いよいよ最後、**【パート3：画面表示とゲームプレイ】**です。

ここには、PCとスマホ両方で見やすくするためのデザイン設定、冒険、ショップ、ガチャ、記録のすべての画面ロジックが含まれています。
さきほどのコードの一番下に、そのまま貼り付けて保存してください。

--- 3. UI AND GAMEPLAY ---
st.set_page_config(page_title="Life Quest", layout="wide")

CSS for Dark Mode & Pixel Style
st.markdown("""

<style>
.stApp { background-color: #0e1117; color: #ffffff; }
.pixel-card { background-color: #1a1c24; border: 2px solid #ffffff; padding: 15px; border-radius: 4px; margin-bottom: 15px; }
.stButton>button { width: 100%; border-radius: 0px; border: 2px solid #fff; background-color: #2b313e; color: #fff; }
h1, h2, h3, p, label { color: #ffffff !important; }
</style>

""", unsafe_allow_html=True)

if 'data' not in st.session_state: st.session_state.data = load_data()
data = st.session_state.data
today = str(datetime.date.today())

Login Logic
if data["mission_progress"]["last_login"] != today:
yesterday = str(datetime.date.today() - datetime.timedelta(days=1))
data["mission_progress"]["combo"] = data["mission_progress"]["combo"] + 1 if data["mission_progress"]["last_login"] == yesterday else 1
data["mission_progress"]["last_login"] = today
data["points"] += 100
save_data(data)

Sidebar
with st.sidebar:
st.image(ASSETS["HERO"][min(data["level"]//20, 3)], width=100)
st.markdown(f"### Lv.{data['level']} {JOBS[data['job']]['name']}")
st.markdown(f"""<div class='pixel-card'>
💎 Pt: {data['points']}



🎫 チケ: {data['items']['gacha_ticket']}



🔥 コンボ: {data['mission_progress']['combo']}日
</div>""", unsafe_allow_html=True)

Main Display
fl = data["dungeon"]["floor"]
st.image(ASSETS["BG"][min((fl-1)//10, 4)], use_column_width=True, caption=f"Floor {fl}")

t1, t2, t3, t4, t5 = st.tabs(["⚔️ 冒険", "🏪 ショップ", "🎰 ガチャ", "📊 記録", "📖 図鑑"])

with t1:
tasks = {"🧹 掃除": 30, "📚 勉強": 50, "💻 仕事": 80, "💪 筋トレ": 40, "🚶 ウォーキング": 100}
cols = st.columns(2)
for i, (name, base) in enumerate(tasks.items()):
rate = calculate_bonus(data, name)
val = int(base * rate)
with cols[i%2]:
if st.button(f"{name} (+{val}pt)"):
data["points"] += val
data["point_history"][today] = data["point_history"].get(today, 0) + val
data["task_counts"][name] = data["task_counts"].get(name, 0) + 1
data["xp"] += 20
data["dungeon"]["floor"] += 1
if data["xp"] >= data["level"] * 100:
data["level"] += 1; data["xp"] = 0; st.balloons()
if data["dungeon"]["floor"] % 10 == 0:
if random.randint(1, 6) >= 3:
st.success("ボス撃破！チケット獲得"); data["items"]["gacha_ticket"] += 1
else:
st.error("敗北... 3階層戻る"); data["dungeon"]["floor"] = max(1, data["dungeon"]["floor"] - 3)
save_data(data); st.rerun()

with t2:
st.subheader("🏪 ショップ")
can_buy, key = check_shop_limit(data, "ticket", "daily", 1)
if st.button(f"🎫 ガチャチケ (150pt) {'[売切]' if not can_buy else ''}", disabled=not can_buy or data["points"] < 150):
data["points"] -= 150; data["items"]["gacha_ticket"] += 1
data["shop_counts"][key] = data["shop_counts"].get(key, 0) + 1
save_data(data); st.rerun()

with t3:
st.subheader("🎰 ガチャ")
if st.button(f"召喚する (残{data['items']['gacha_ticket']}枚)", disabled=data["items"]["gacha_ticket"] == 0):
data["items"]["gacha_ticket"] -= 1
rarity = random.choices(["N", "R", "SR", "SSR", "UR"], weights=[50, 30, 15, 4, 1])[0]
m = random.choice(MONSTER_DB.get(rarity, MONSTER_DB["N"]))
st.image(m["img"], width=200); st.write(f"🎉 {m['name']} が現れた！")
data["monster_levels"][m["name"]] = data["monster_levels"].get(m["name"], 0) + 1
save_data(data)

with t4:
st.subheader("📊 記録")
if data["point_history"]:
df = pd.DataFrame(list(data["point_history"].items()), columns=["Date", "Points"])
st.plotly_chart(px.bar(df, x="Date", y="Points", template="plotly_dark"))

with t5:
st.subheader("📖 図鑑")
for name, lv in data["monster_levels"].items():
st.write(f"👾 {name} (Lv.{lv})")