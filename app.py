import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import random
import json

# --- 1. 設定とデータ定義 ---
SHEET_NAME = "life_quest_db"

# ★ここが進化したモンスター図鑑データ！
# 好きな画像のURL（ネット上の画像の住所）を入れると、それが表示されます！
MONSTER_DB = {
    "UR": [
        {"name": "🐲 伝説のドラゴン", "power": 9999, "desc": "世界を焼き尽くす炎を吐く、最強の古龍。", "img": "https://placehold.co/400x400/000000/FF0000?text=Dragon"},
        {"name": "🦄 虹色のユニコーン", "power": 8500, "desc": "見た者に永遠の幸運をもたらす幻獣。", "img": "https://placehold.co/400x400/eeeeee/FF00FF?text=Unicorn"},
        {"name": "👼 大天使", "power": 8800, "desc": "天界からの使者。神々しい光を放つ。", "img": "https://placehold.co/400x400/FFFFE0/DAA520?text=Angel"}
    ],
    "SSR": [
        {"name": "🦁 百獣の王", "power": 5000, "desc": "サバンナを支配する王者の風格。", "img": "https://placehold.co/400x400/DAA520/000000?text=Lion"},
        {"name": "🧛 ヴァンパイア", "power": 4800, "desc": "夜の貴族。トマトジュースが好きらしい。", "img": "https://placehold.co/400x400/000000/800080?text=Vampire"},
        {"name": "🤖 未来ロボ", "power": 5500, "desc": "22世紀から来たハイテクマシン。", "img": "https://placehold.co/400x400/C0C0C0/0000FF?text=Robot"}
    ],
    "SR": [
        {"name": "🐺 シルバーウルフ", "power": 3000, "desc": "銀色の毛並みを持つ孤高の狼。", "img": "https://placehold.co/400x400/A9A9A9/FFFFFF?text=Wolf"},
        {"name": "🦅 グリフォン", "power": 3200, "desc": "空の王者。鷲とライオンのハーフ。", "img": "https://placehold.co/400x400/8B4513/FFD700?text=Griffin"},
        {"name": "👻 ゴーストキング", "power": 2800, "desc": "驚かすのが大好きなオバケの王様。", "img": "https://placehold.co/400x400/483D8B/00FFFF?text=Ghost"}
    ],
    "R": [
        {"name": "🐗 ワイルドボア", "power": 1200, "desc": "突進しかできない猪突猛進野郎。", "img": "https://placehold.co/400x400/8B0000/FFFFFF?text=Boar"},
        {"name": "🕷️ 巨大グモ", "power": 1100, "desc": "カサカサ動く。実は益虫。", "img": "https://placehold.co/400x400/000000/00FF00?text=Spider"},
        {"name": "🦇 コウモリ", "power": 900, "desc": "洞窟に住んでいる。超音波でおしゃべりする。", "img": "https://placehold.co/400x400/2F4F4F/FFFF00?text=Bat"}
    ],
    "N": [
        {"name": "💧 スライム", "power": 10, "desc": "プルプルしている。最弱のモンスター。", "img": "https://placehold.co/400x400/00BFFF/FFFFFF?text=Slime"},
        {"name": "🍄 きのこ", "power": 5, "desc": "ただのキノコ。たまに毒があるかも。", "img": "https://placehold.co/400x400/FF4500/FFFFFF?text=Mushroom"},
        {"name": "🐛 けむし", "power": 3, "desc": "葉っぱを食べている。将来は蝶になる予定。", "img": "https://placehold.co/400x400/32CD32/000000?text=Caterpillar"}
    ]
}

# ガチャ確率
GACHA_RATES = {"UR": 1, "SSR": 4, "SR": 15, "R": 30, "N": 50}

# データベース接続
def get_database():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

# データ読み込み・保存
def load_data():
    try:
        sheet = get_database()
        data_str = sheet.acell('A1').value
        if data_str: return json.loads(data_str)
    except: pass
    return {"points": 0, "xp": 0, "level": 1, "last_login": "", "collection": [], "daily_gacha_done": False}

def save_data(data):
    try:
        sheet = get_database()
        sheet.update(range_name='A1', values=[[json.dumps(data, ensure_ascii=False)]])
    except Exception as e: st.error(f"セーブ失敗: {e}")

# ガチャロジック
def pull_gacha():
    rarity = random.choices(list(GACHA_RATES.keys()), weights=list(GACHA_RATES.values()), k=1)[0]
    monster_obj = random.choice(MONSTER_DB[rarity])
    return rarity, monster_obj

def check_login_bonus(data):
    today = str(datetime.date.today())
    if data["last_login"] != today:
        data["last_login"] = today
        data["daily_gacha_done"] = False
        data["points"] += 100
        save_data(data)
        return True, 100
    return False, 0

# --- 3. アプリ画面構築 ---
st.set_page_config(page_title="Life Quest V5", page_icon="⚔️")

# CSSで見た目をゲームっぽく調整
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; border: 2px solid #333; }
    .status-box { padding: 15px; border-radius: 10px; background-color: #f0f2f6; border: 2px solid #ccc; margin-bottom: 20px; }
    .card { background-color: #fff; padding: 10px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); border: 1px solid #ddd; text-align: center; }
    .rarity-UR { color: #ff0000; font-weight: bold; font-size: 1.2em; }
    .rarity-SSR { color: #DAA520; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if 'data' not in st.session_state: st.session_state.data = load_data()
data = st.session_state.data

# サイドバー（ステータス画面）
with st.sidebar:
    st.title("🛡️ 勇者のステータス")
    st.markdown(f"""
    <div class="status-box">
        <h3>Lv. {data['level']}</h3>
        <p>💎 ポイント: <b>{data['points']}</b></p>
        <p>⚔️ 次のレベルまで: {data['level']*100 - data['xp']} XP</p>
    </div>
    """, unsafe_allow_html=True)
    st.progress(min(data['xp'] % 100 / 100, 1.0))

# メイン画面
st.title("⚔️ Life Quest: Chronicle")

is_new_day, bonus = check_login_bonus(data)
if is_new_day:
    st.balloons()
    st.success(f"🎁 ログインボーナス！ +{bonus}pt")

tab1, tab2, tab3 = st.tabs(["📜 クエスト", "🔮 ガチャ", "📖 図鑑"])

# --- クエスト ---
with tab1:
    st.subheader("本日の任務")
    col1, col2 = st.columns(2)
    tasks = {"🧹 掃除 (5分)": 30, "📚 勉強 (15分)": 50, "💻 コード書き": 80, "💪 筋トレ": 40}
    for i, (task, reward) in enumerate(tasks.items()):
        with col1 if i%2==0 else col2:
            if st.button(f"{task}\n(+{reward}pt)"):
                data["points"] += reward
                data["xp"] += 10
                if data["xp"] // 100 > data["level"]:
                    data["level"] += 1
                    st.toast(f"レベルアップ！ Lv.{data['level']}")
                save_data(data)
                st.rerun()

# --- ガチャ ---
with tab2:
    st.subheader("モンスター召喚")
    if st.button("💎 200pt で引く", disabled=data["points"] < 200):
        data["points"] -= 200
        rarity, monster = pull_gacha()
        # 名前だけ保存して容量節約
        data["collection"].append(monster["name"])
        save_data(data)
        
        st.balloons()
        st.markdown(f"## ⚡ {rarity} 召喚成功！")
        # 結果表示カード
        st.image(monster["img"], width=300)
        st.markdown(f"### {monster['name']}")
        st.info(monster["desc"])

# --- 図鑑（コレクション詳細） ---
with tab3:
    st.subheader("📦 収集済みモンスター")
    if not data["collection"]:
        st.warning("まだモンスターを持っていません。ガチャを引こう！")
    else:
        # 持っているモンスターのリストを整理
        my_collection = sorted(list(set(data["collection"])))
        
        # 3列で表示
        cols = st.columns(3)
        for i, monster_name in enumerate(my_collection):
            # データベースから詳細情報を探す
            found_monster = None
            found_rarity = "N"
            for r, m_list in MONSTER_DB.items():
                for m in m_list:
                    if m["name"] == monster_name:
                        found_monster = m
                        found_rarity = r
                        break
            
            if found_monster:
                with cols[i % 3]:
                    st.markdown(f"""
                    <div class="card">
                        <div class="rarity-{found_rarity}">{found_rarity}</div>
                        <b>{monster_name}</b>
                    </div>
                    """, unsafe_allow_html=True)
                    st.image(found_monster["img"], use_column_width=True)
                    with st.expander("詳細を見る"):
                        st.write(f"⚔️ 戦闘力: {found_monster['power']}")
                        st.caption(found_monster["desc"])