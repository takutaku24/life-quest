import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import random
import json

# --- 1. 設定とスプレッドシート接続 ---
SHEET_NAME = "life_quest_db"

# ガチャ設定
GACHA_RATES = {"UR(1%)":1, "SSR(4%)":4, "SR(15%)":15, "R(30%)":30, "N(50%)":50}
MONSTERS = {
    "UR(1%)": ["🐲 伝説のドラゴン", "🦄 虹色のユニコーン", "👼 大天使"],
    "SSR(4%)": ["🦁 百獣の王", "🧛 ヴァンパイアロード", "🤖 未来ロボ"],
    "SR(15%)": ["🐺 シルバーウルフ", "🦅 グリフォン", "👻 ゴーストキング"],
    "R(30%)": ["🐗 ワイルドボア", "🕷️ ジャイアントスパイダー", "🦇 コウモリ"],
    "N(50%)": ["💧 スライム", "🍄 きのこ", "🐛 けむし"]
}

# データベース接続
def get_database():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

# データ読み込み
def load_data():
    try:
        sheet = get_database()
        data_str = sheet.acell('A1').value # ここを修正
        if data_str:
            return json.loads(data_str)
    except Exception:
        pass
    return {
        "points": 0, "xp": 0, "level": 1, 
        "last_login": "", "collection": [], "daily_gacha_done": False
    }

# データ保存
def save_data(data):
    try:
        sheet = get_database()
        # update_cell は古いので update_acell に変更
        sheet.update_acell('A1', json.dumps(data, ensure_ascii=False))
    except Exception as e:
        st.error(f"セーブ失敗: {e}")

# --- 2. ゲームロジック ---
def pull_gacha():
    rarities = list(GACHA_RATES.keys())
    weights = list(GACHA_RATES.values())
    selected_rarity = random.choices(rarities, weights=weights, k=1)[0]
    monster = random.choice(MONSTERS[selected_rarity])
    return selected_rarity, monster

def check_login_bonus(data):
    today = str(datetime.date.today())
    if data["last_login"] != today:
        data["last_login"] = today
        data["daily_gacha_done"] = False
        bonus_pt = 100
        data["points"] += bonus_pt
        save_data(data)
        return True, bonus_pt
    return False, 0

# --- 3. アプリ画面 ---
st.set_page_config(page_title="Life Quest Cloud", page_icon="☁️")

if 'data' not in st.session_state:
    st.session_state.data = load_data()
data = st.session_state.data

st.markdown("""<style>.stButton>button {width: 100%; border-radius: 10px; font-weight: bold;}</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.title("☁️ 冒険の記録")
    st.write(f"Lv: **{data['level']}**")
    st.write(f"💎 Pt: **{data['points']}**")
    st.progress(min(data['xp'] % 100 / 100, 1.0))
    st.write("---")
    st.write("📦 コレクション")
    for m in set(data['collection']):
        st.write(m)

st.title("☁️ Life Quest: Cloud Edition")

is_new_day, bonus = check_login_bonus(data)
if is_new_day:
    st.balloons()
    st.success(f"ログインボーナス！ +{bonus}pt")

tab1, tab2 = st.tabs(["⚔️ クエスト", "🔮 ガチャ"])

with tab1:
    col1, col2 = st.columns(2)
    tasks = {"掃除 (5分)": 30, "勉強 (15分)": 50, "コード書き": 80, "筋トレ": 40}
    for i, (task, reward) in enumerate(tasks.items()):
        with col1 if i%2==0 else col2:
            if st.button(f"{task} (+{reward})"):
                data["points"] += reward
                data["xp"] += 10
                if data["xp"] // 100 > data["level"]:
                    data["level"] += 1
                    st.toast(f"レベルアップ！ Lv.{data['level']}")
                save_data(data)
                st.rerun()

with tab2:
    if st.button("ガチャを引く (200pt)", disabled=data["points"] < 200):
        data["points"] -= 200
        rarity, monster = pull_gacha()
        data["collection"].append(monster)
        save_data(data)
        st.balloons()
        st.write(f"## {rarity}\n# {monster}")

if st.button("🔄 手動セーブ"):
    save_data(data)
    st.success("クラウドに保存しました！")