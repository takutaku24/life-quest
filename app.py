import streamlit as st
import json
import os
import random
import datetime
import time # 演出用の時間を操る魔法

# --- 1. 設定とデータ管理 ---
DATA_FILE = "quest_data.json"

# ガチャの確率設定 (合計100%)
GACHA_RATES = {
    "UR (1%)": 1,
    "SSR (4%)": 4,
    "SR (15%)": 15,
    "R (30%)": 30,
    "N (50%)": 50
}
# ガチャの中身（モンスター図鑑）
MONSTERS = {
    "UR (1%)": ["🐲 伝説のドラゴン", "🦄 虹色のユニコーン", "👼 大天使", "🪐 宇宙猫", "👑 魔王"],
    "SSR (4%)": ["🦁 百獣の王", "🧛 ヴァンパイアロード", "🤖 未来ロボ", "🐉 水龍", "🧚 精霊王"],
    "SR (15%)": ["🐺 シルバーウルフ", "🦅 グリフォン", "👻 ゴーストキング", "🦈 メガロドン", "🦍 キングコング"],
    "R (30%)": ["🐗 ワイルドボア", "🕷️ ジャイアントスパイダー", "🦇 コウモリ", "🐍 大蛇", "🐸 巨大ガエル"],
    "N (50%)": ["💧 スライム", "🍄 きのこ", "🐛 けむし", "🪨 石ころ", "🦴 ほね"]
}

# 初期のセーブデータ構造
DEFAULT_DATA = {
    "points": 500,         # 動作確認用に初期ポイント多め
    "xp": 0,
    "level": 1,
    "last_login": "",
    "collection": [],
    "daily_gacha_done": False
}

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return DEFAULT_DATA.copy()
    return DEFAULT_DATA.copy()

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 2. ゲームロジック ---

# ガチャ演出＆抽選システム
def pull_gacha_with_animation():
    # 演出用の場所を確保
    placeholder = st.empty()
    
    # ドキドキ演出タイム
    placeholder.markdown("### 🌀 召喚の儀式を開始...")
    time.sleep(0.7)
    placeholder.markdown("### ⚡ エネルギー充填中...")
    time.sleep(0.7)
    placeholder.markdown("### ✨ ゲートが開く...！")
    time.sleep(0.7)
    placeholder.empty() # 演出を消す

    # 抽選
    rarities = list(GACHA_RATES.keys())
    weights = list(GACHA_RATES.values())
    selected_rarity = random.choices(rarities, weights=weights, k=1)[0]
    monster = random.choice(MONSTERS[selected_rarity])
    
    return selected_rarity, monster

# ログインボーナス判定
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

# --- 3. アプリ画面構築 ---
st.set_page_config(page_title="Life Quest V4", page_icon="🏰")

# データ読み込み
if 'data' not in st.session_state:
    st.session_state.data = load_data()
data = st.session_state.data

# CSSデザイン
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; }
    .result-rarity { font-size: 30px; font-weight: bold; color: #FFD700; text-align: center;}
    .result-monster { font-size: 50px; font-weight: bold; text-align: center; }
</style>
""", unsafe_allow_html=True)

# === サイドバー ===
with st.sidebar:
    st.title("🛡️ ステータス")
    avatar, job = "🧑‍🌾", "見習い"
    if data['level'] >= 3: avatar, job = "⚔️", "戦士"
    if data['level'] >= 5: avatar, job = "🧙‍♂️", "魔導士"
    if data['level'] >= 10: avatar, job = "👑", "英雄"
    
    st.header(f"{avatar} Lv.{data['level']} {job}")
    st.write(f"💎 ポイント: **{data['points']} pt**")
    next_level_xp = data['level'] * 100
    st.progress(min(data['xp'] / next_level_xp, 1.0))
    
    st.divider()
    st.subheader("📖 モンスター図鑑")
    unique_monsters = set(data["collection"])
    total_monsters = sum(len(v) for v in MONSTERS.values())
    st.write(f"収集率: {len(unique_monsters)} / {total_monsters} 種")
    with st.expander("コレクションを見る"):
        for m in unique_monsters: st.write(m)

# === メイン画面 ===
st.title("🏰 Life Quest V4")

is_new_day, bonus = check_login_bonus(data)
if is_new_day:
    st.balloons()
    st.toast(f"🎉 ログインボーナス！ {bonus}pt 獲得！")

tab1, tab2, tab3 = st.tabs(["📜 クエスト", "🔮 ガチャ", "⚙️ 設定"])

# --- タブ1: クエスト ---
with tab1:
    st.subheader("⚔️ 本日のクエスト")
    period = st.radio("", ["☀️ 午前 (AM)", "🌙 午後 (PM)"], horizontal=True)
    tasks = {"🛏️ 起床即水飲み": 10, "🧹 掃除 (5分)": 30, "💻 デイトラ起動": 50} if "午前" in period else {"📚 勉強 (15分)": 50, "💪 筋トレ": 40, "🛁 入浴": 20}
    
    col1, col2 = st.columns(2)
    for i, (task, reward) in enumerate(tasks.items()):
        with col1 if i % 2 == 0 else col2:
            if st.button(f"{task}\n(+{reward}pt)"):
                data["points"] += reward
                data["xp"] += 10
                if data["xp"] >= data["level"] * 100:
                    data["xp"] = 0
                    data["level"] += 1
                    st.balloons()
                    st.toast(f"レベルアップ！ Lv.{data['level']}！")
                save_data(data)
                st.rerun()

# --- タブ2: ガチャ（演出強化版） ---
with tab2:
    st.subheader("🔮 召喚の館")
    
    # ガチャ実行ボタン（コールバック関数で処理）
    def run_gacha(is_free):
        if not is_free:
            data["points"] -= 200
        else:
            data["daily_gacha_done"] = True
            
        # 演出付きで抽選
        rarity, monster = pull_gacha_with_animation()
        data["collection"].append(monster)
        save_data(data)
        
        # 結果表示
        if "UR" in rarity:
            st.balloons()
            st.markdown(f"<div class='result-rarity'>🌈 {rarity} ！！</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='result-monster'>{monster}</div>", unsafe_allow_html=True)
        elif "SSR" in rarity:
            st.snow()
            st.markdown(f"<div class='result-rarity'>✨ {rarity} ！</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='result-monster'>{monster}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"### {rarity} ゲット！")
            st.write(f"# {monster}")

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.info("🆓 デイリー無料")
        st.button("無料で引く！", disabled=data["daily_gacha_done"], on_click=run_gacha, args=(True,))
    with col_g2:
        st.warning("💎 ポイント召喚 (200pt)")
        st.button("200pt で引く", disabled=data["points"] < 200, on_click=run_gacha, args=(False,))

# --- タブ3: 設定 ---
with tab3:
    st.write("データ管理")
    if st.button("全データをリセットする"):
        save_data(DEFAULT_DATA)
        st.session_state.data = DEFAULT_DATA
        st.rerun()
        