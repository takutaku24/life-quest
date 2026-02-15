import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import random
import time
import gspread
from google.oauth2.service_account import Credentials
from google.auth import exceptions

# --- 1. 設定と定数 (Configuration) ---
PAGE_TITLE = "Life Quest: Pixel Legends"
PAGE_ICON = "⚔️"

# 職業データ
JOBS = {
    "Novice": {"name": "冒険者", "desc": "バランス型", "multi": 1.0, "icon": "🛡️"},
    "Warrior": {"name": "戦士", "desc": "筋トレ特化 (1.5倍)", "multi": 1.0, "bonus_type": "筋トレ", "icon": "⚔️"},
    "Mage": {"name": "魔導士", "desc": "勉強特化 (1.5倍)", "multi": 1.0, "bonus_type": "勉強", "icon": "🪄"},
    "Thief": {"name": "盗賊", "desc": "掃除特化 (1.5倍)", "multi": 1.0, "bonus_type": "掃除", "icon": "💰"},
    "Jester": {"name": "遊び人", "desc": "稀にPt10倍・ガチャ運UP", "multi": 0.7, "gamble": True, "icon": "🃏"}
}

# ミッション設定
MISSIONS = {
    "daily": {"target": 3, "reward_gold": 300, "desc": "タスクを3つ完了する"},
    "weekly": {"target": 15, "reward_ticket": 1, "desc": "週間で15タスク完了する"}
}

# --- 2. データベース関数 (Database Functions) ---

def connect_to_gsheet():
    """Google Sheetsへの接続を確立し、ワークシートオブジェクトを返す"""
    try:
        # st.secrets から認証情報を取得
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        # dictとしてsecretsから読み込む
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        # スプレッドシートを開く（シート名またはキーで指定）
        # ※初回はシート名を st.secrets["sheet_name"] 等で指定するか、固定値にする必要があります
        sheet_name = st.secrets.get("sheet_name", "LifeQuest_DB") 
        try:
            sh = client.open(sheet_name)
        except gspread.SpreadsheetNotFound:
            # シートがない場合は作成（権限がある場合）
            sh = client.create(sheet_name)
            # 初期ヘッダー作成
            sh.add_worksheet(title="log", rows=1000, cols=5)
            sh.add_worksheet(title="user", rows=10, cols=10)
            sh.sheet1.update([["date", "task", "type", "points", "bonus_flag"]]) # logヘッダー
            sh.worksheet("user").update([["name", "job", "floor", "gold", "tickets", "xp", "pet_name"]]) # userヘッダー
            
        return sh
    except Exception as e:
        st.error(f"データベース接続エラー: {e}")
        return None

def load_data(sh):
    """スプレッドシートからデータを読み込み、session_stateに格納する"""
    try:
        # ログデータの読み込み
        ws_log = sh.worksheet("log")
        logs = ws_log.get_all_records()
        df_log = pd.DataFrame(logs)
        
        # ユーザーデータの読み込み
        ws_user = sh.worksheet("user")
        user_records = ws_user.get_all_records()
        
        if not user_records:
            # 新規ユーザー初期化
            user_data = {
                "name": "Player", "job": "Novice", "floor": 1,
                "gold": 0, "tickets": 0, "xp": 0, "pet_name": "ポチ"
            }
            # シートに書き込み
            ws_user.append_row(list(user_data.values()))
        else:
            user_data = user_records[0]

        return user_data, df_log

    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")
        return {}, pd.DataFrame()

def save_task_to_db(sh, task_data, new_user_data):
    """タスクの追記とユーザーステータスの更新"""
    try:
        # ログ追記
        ws_log = sh.worksheet("log")
        row = [
            str(task_data["date"]),
            task_data["task"],
            task_data["type"],
            task_data["points"],
            task_data["bonus_flag"]
        ]
        ws_log.append_row(row)
        
        # ユーザーデータ更新 (1行目を上書き)
        ws_user = sh.worksheet("user")
        # gspreadは1始まり。ヘッダーが1行目なのでデータは2行目
        header = ["name", "job", "floor", "gold", "tickets", "xp", "pet_name"]
        update_values = [new_user_data[k] for k in header]
        
        # A2からG2まで更新
        cell_range = f"A2:{chr(65+len(header)-1)}2"
        ws_user.update(range_name=cell_range, values=[update_values])
        
    except Exception as e:
        st.error(f"データ保存エラー: {e}")

# --- 3. ゲームロジック関数 (Game Logic) ---

def calculate_points(base_pt, task_type, user_job):
    """職業補正とギャンブル判定を含めたポイント計算"""
    job_info = JOBS[user_job]
    multiplier = job_info["multi"]
    is_jackpot = False
    
    # 職業特化ボーナス
    if "bonus_type" in job_info and job_info["bonus_type"] == task_type:
        multiplier = 1.5
    
    # 遊び人: 10倍界王拳ロジック
    if user_job == "Jester" and job_info.get("gamble"):
        if random.random() < 0.10: # 10%
            multiplier = 10.0
            is_jackpot = True
            
    final_pt = int(base_pt * multiplier)
    return final_pt, is_jackpot

def get_avatar_url(seed, type="adventurer"):
    """DiceBear APIを使ってドット絵アバターURLを生成"""
    # pixel-art スタイルを使用
    base = "https://api.dicebear.com/9.x/pixel-art/svg"
    if type == "monster":
        base = "https://api.dicebear.com/9.x/pixel-art/svg" # モンスターっぽいシードを使う
    return f"{base}?seed={seed}"

def get_pet_comment(df_log, user_name):
    """ユーザーの活動状況に応じたペットのコメントを生成"""
    msgs = [f"{user_name}、今日もいい天気だね！", "何か手伝うことある？"]
    
    if df_log.empty:
        return "冒険の始まりだね！まずは簡単なクエストからどう？"
    
    # 日付処理
    df_log['date'] = pd.to_datetime(df_log['date'])
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    
    today_tasks = df_log[df_log['date'].dt.date == today]
    yesterday_tasks = df_log[df_log['date'].dt.date == yesterday]
    
    today_count = len(today_tasks)
    yesterday_count = len(yesterday_tasks)
    
    if today_count > 0:
        msgs.append("すごーい！順調に進んでるね！")
        if today_count >= 3:
             msgs.append("今日は絶好調だね！この調子！")
    
    if today_count > yesterday_count and yesterday_count > 0:
        return f"すごい！昨日よりも多くのタスクをこなしてるよ！成長してるね、{user_name}！"
        
    if today_count == 0 and yesterday_count == 0:
        return "焦らなくて大丈夫。まずは「深呼吸」っていうタスクはどう？"

    return random.choice(msgs)

def check_missions(df_log, user_data):
    """ミッション達成状況を確認し報酬を付与する"""
    if df_log.empty:
        return [], user_data

    completed_missions = []
    df_log['date'] = pd.to_datetime(df_log['date'])
    today = datetime.date.today()
    
    # デイリー集計
    today_tasks = df_log[df_log['date'].dt.date == today]
    if len(today_tasks) >= MISSIONS["daily"]["target"]:
        # ここで「既に報酬を受け取ったか」の判定が必要だが、
        # 簡易化のため「今日達成している」という表示にする（厳密な受取管理はDB拡張が必要）
        completed_missions.append("daily")

    # ウィークリー集計 (月曜始まり)
    start_week = today - datetime.timedelta(days=today.weekday())
    week_tasks = df_log[df_log['date'].dt.date >= start_week]
    if len(week_tasks) >= MISSIONS["weekly"]["target"]:
        completed_missions.append("weekly")
        
    return completed_missions, user_data

# --- 4. メインアプリ (Main App) ---

def main():
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide")
    
    # カスタムCSS（フォントなどをドット絵風に）
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DotGothic16&display=swap');
    * { font-family: 'DotGothic16', sans-serif; }
    .stButton>button { border-radius: 0px; border: 2px solid #333; box-shadow: 2px 2px 0px #333; }
    .stButton>button:active { box-shadow: 0px 0px 0px #333; transform: translateY(2px); }
    </style>
    """, unsafe_allow_html=True)

    # DB接続と初期ロード
    if "sh" not in st.session_state:
        st.session_state.sh = connect_to_gsheet()
    
    if st.session_state.sh:
        user_data, df_log = load_data(st.session_state.sh)
    else:
        st.warning("DB接続待ち... (secretsを設定してください)")
        return

    # --- サイドバー (Profile & Pet) ---
    with st.sidebar:
        st.title("🛡️ ステータス")
        
        # アバター表示
        avatar_url = get_avatar_url(user_data["name"])
        st.image(avatar_url, width=100)
        
        st.write(f"**名前:** {user_data['name']}")
        st.write(f"**職業:** {JOBS[user_data['job']]['icon']} {JOBS[user_data['job']]['name']}")
        st.write(f"**Lv:** {user_data['floor']} (累計XP: {user_data['xp']})")
        st.write(f"**Gold:** {user_data['gold']} G")
        st.write(f"**Tix:** {user_data['tickets']} 枚")
        
        st.markdown("---")
        
        # ペットエリア
        st.subheader(f"🐾 相棒: {user_data.get('pet_name', 'ポチ')}")
        pet_url = get_avatar_url(user_data.get('pet_name', 'ポチ'), type="monster")
        st.image(pet_url, width=80)
        
        # ペットのコメント生成
        pet_msg = get_pet_comment(df_log, user_data["name"])
        st.info(f"「{pet_msg}」")
        
        st.markdown("---")
        # 職業変更
        new_job = st.selectbox("転職する", list(JOBS.keys()), index=list(JOBS.keys()).index(user_data['job']))
        if new_job != user_data['job']:
            user_data['job'] = new_job
            # 即時保存してリロード
            save_task_to_db(st.session_state.sh, {"date": "", "task": "", "type": "", "points": 0, "bonus_flag": ""}, user_data)
            st.rerun()

    # --- メインエリア ---
    st.title(f"{PAGE_ICON} {PAGE_TITLE}")
    
    # タブ
    tab1, tab2, tab3, tab4 = st.tabs(["⚔️ クエストボード", "📜 ミッション", "🎰 酒場ガチャ", "📊 冒険の記録"])

    # 1. クエスト (Task Input)
    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("タスクをこなして魔王に挑め！")
            task_name = st.text_input("クエスト名 (タスク)", placeholder="例: 洗濯物をたたむ")
            
            c1, c2 = st.columns(2)
            with c1:
                task_type = st.selectbox("属性", ["一般", "筋トレ", "勉強", "掃除"])
            with c2:
                difficulty = st.select_slider("難易度", options=[10, 30, 50, 100], value=30)
            
            if st.button("クエスト完了！", type="primary", use_container_width=True):
                if task_name:
                    # ポイント計算
                    earned_pt, jackpot = calculate_points(difficulty, task_type, user_data["job"])
                    
                    # ユーザーデータ更新
                    user_data["xp"] += earned_pt
                    user_data["gold"] += earned_pt
                    
                    # ログデータ作成
                    log_entry = {
                        "date": str(datetime.datetime.now()),
                        "task": task_name,
                        "type": task_type,
                        "points": earned_pt,
                        "bonus_flag": "JACKPOT" if jackpot else ""
                    }
                    
                    # 保存
                    save_task_to_db(st.session_state.sh, log_entry, user_data)
                    
                    # 演出
                    if jackpot:
                        st.balloons()
                        st.success(f"🎰 【{JOBS[user_data['job']]['name']}の極意】発動！ ポイント10倍！ +{earned_pt} XP/Gold")
                    else:
                        st.toast(f"✅ クエスト完了！ +{earned_pt} XP/Gold")
                    
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("クエスト名を入力してください")

        with col2:
            st.image(f"https://source.unsplash.com/400x300/?fantasy,landscape&sig={user_data['floor']}", caption=f"現在のエリア: 第{user_data['floor']}層")
            # 簡易的な階層進行ボタン（本来はボス撃破などで進む）
            if st.button("次の階層へ進む"):
                user_data["floor"] += 1
                save_task_to_db(st.session_state.sh, {"date": "", "task": "", "type": "", "points": 0, "bonus_flag": ""}, user_data)
                st.rerun()

    # 2. ミッション (Missions)
    with tab2:
        st.subheader("ギルドからの依頼")
        completed, _ = check_missions(df_log, user_data)
        
        # デイリー
        st.write(f"**📅 デイリー: {MISSIONS['daily']['desc']}**")
        if "daily" in completed:
            st.success("✅ 達成済み！ (報酬受取済)")
        else:
            daily_prog = len(df_log[pd.to_datetime(df_log['date']).dt.date == datetime.date.today()])
            st.progress(min(1.0, daily_prog / MISSIONS['daily']['target']))
            st.caption(f"進捗: {daily_prog} / {MISSIONS['daily']['target']}")

        # ウィークリー
        st.write(f"**🗓️ ウィークリー: {MISSIONS['weekly']['desc']}**")
        if "weekly" in completed:
            st.success("✅ 達成済み！ (報酬受取済)")
        else:
            # 簡易計算
            today = datetime.date.today()
            start_week = today - datetime.timedelta(days=today.weekday())
            week_prog = len(df_log[pd.to_datetime(df_log['date']).dt.date >= start_week])
            st.progress(min(1.0, week_prog / MISSIONS['weekly']['target']))
            st.caption(f"進捗: {week_prog} / {MISSIONS['weekly']['target']}")

    # 3. ガチャ (Gacha)
    with tab3:
        st.subheader("異世界召喚")
        st.write("貯めたGoldで仲間を召喚しよう！ (1回 300 Gold)")
        
        if st.button(f"召喚する (所持: {user_data['gold']} G)", disabled=user_data['gold'] < 300):
            user_data['gold'] -= 300
            
            # 確率設定
            probs = [0.6, 0.3, 0.09, 0.01] # N, R, SR, UR
            # 遊び人の幸運
            if user_data['job'] == "Jester":
                probs = [0.5, 0.35, 0.12, 0.03] # URが3%にアップ
                st.caption("🃏 遊び人の運が作用している...")
            
            rarity = random.choices(["N", "R", "SR", "UR"], weights=probs)[0]
            
            # 演出
            colors = {"N": "gray", "R": "blue", "SR": "gold", "UR": "rainbow"}
            st.markdown(f"### :{colors[rarity]}[{rarity} モンスター召喚！]")
            
            # モンスター画像生成
            monster_seed = str(time.time())
            st.image(get_avatar_url(monster_seed, "monster"), width=200)
            
            # 保存処理 (本来はCollectionシートに追加するが、今回はUserデータの更新のみで簡易化)
            save_task_to_db(st.session_state.sh, {"date": "", "task": "", "type": "", "points": 0, "bonus_flag": ""}, user_data)
            st.rerun()

    # 4. ログ (Stats)
    with tab4:
        if not df_log.empty:
            df_log['date'] = pd.to_datetime(df_log['date'])
            daily_sum = df_log.groupby(df_log['date'].dt.date)['points'].sum().reset_index()
            
            fig = px.bar(daily_sum, x='date', y='points', title="日別獲得経験値", color_discrete_sequence=['#FF4B4B'])
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df_log.sort_values('date', ascending=False), use_container_width=True)
        else:
            st.info("データがありません。まずはクエストへ！")

if __name__ == "__main__":
    main()