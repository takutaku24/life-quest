import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import random
import time
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 設定と定数 ---
PAGE_TITLE = "Life Quest: Pixel Legends"
PAGE_ICON = "⚔️"

JOBS = {
    "Novice": {"name": "冒険者", "desc": "バランス型", "multi": 1.0, "icon": "🛡️"},
    "Warrior": {"name": "戦士", "desc": "筋トレ特化 (1.5倍)", "multi": 1.0, "bonus_type": "筋トレ", "icon": "⚔️"},
    "Mage": {"name": "魔導士", "desc": "勉強特化 (1.5倍)", "multi": 1.0, "bonus_type": "勉強", "icon": "🪄"},
    "Thief": {"name": "盗賊", "desc": "掃除特化 (1.5倍)", "multi": 1.0, "bonus_type": "掃除", "icon": "💰"},
    "Jester": {"name": "遊び人", "desc": "稀にPt10倍・ガチャ運UP", "multi": 0.7, "gamble": True, "icon": "🃏"}
}

MISSIONS = {
    "daily": {"target": 3, "reward_gold": 300, "desc": "タスクを3つ完了する"},
    "weekly": {"target": 15, "reward_ticket": 1, "desc": "週間で15タスク完了する"}
}

DEFAULT_USER = {
    "name": "Player", "job": "Novice", "floor": 1, 
    "gold": 0, "tickets": 0, "xp": 0, "pet_name": "ポチ"
}

# --- 2. データベース関数 ---

def connect_to_gsheet():
    """Google Sheetsへの接続と初期化"""
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        sheet_name = st.secrets.get("sheet_name", "LifeQuest_DB")
        try:
            sh = client.open(sheet_name)
        except gspread.SpreadsheetNotFound:
            sh = client.create(sheet_name)
            st.toast("✨ 新しい冒険の書(データベース)を作成しました！")

        # シートの自動生成ロジック
        try:
            sh.worksheet("user")
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet("user", rows=10, cols=10)
            ws.append_row(["name", "job", "floor", "gold", "tickets", "xp", "pet_name"])
            ws.append_row(list(DEFAULT_USER.values()))
            
        try:
            sh.worksheet("log")
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet("log", rows=1000, cols=5)
            ws.append_row(["date", "task", "type", "points", "bonus_flag"])

        return sh
    except Exception as e:
        st.error(f"データベース接続エラー: {e}")
        return None

def load_data(sh):
    """データの読み込み（エラー回避機能付き）"""
    try:
        # LOGシート読み込み
        try:
            ws_log = sh.worksheet("log")
            logs = ws_log.get_all_records()
            df_log = pd.DataFrame(logs)
        except:
            df_log = pd.DataFrame() # 失敗したら空のデータ
        
        # USERシート読み込み
        ws_user = sh.worksheet("user")
        user_records = ws_user.get_all_records()
        
        # データが空っぽ、または壊れている場合の修復ロジック
        if not user_records:
            user_data = DEFAULT_USER.copy()
            # 空なら初期値を書き込んでおく
            ws_user.clear()
            ws_user.append_row(["name", "job", "floor", "gold", "tickets", "xp", "pet_name"])
            ws_user.append_row(list(DEFAULT_USER.values()))
        else:
            # 辞書データの欠損チェック
            fetched_data = user_records[0]
            user_data = DEFAULT_USER.copy()
            # 取得したデータで上書き（足りない項目はデフォルト値のまま）
            for key, value in fetched_data.items():
                if key in user_data:
                    user_data[key] = value

        return user_data, df_log

    except Exception as e:
        # それでもダメならデフォルト値を返してアプリを落とさない
        return DEFAULT_USER.copy(), pd.DataFrame()

def save_task_to_db(sh, task_data, new_user_data):
    try:
        ws_log = sh.worksheet("log")
        if task_data["task"]: 
            row = [
                str(task_data["date"]), task_data["task"],
                task_data["type"], task_data["points"], task_data["bonus_flag"]
            ]
            ws_log.append_row(row)
        
        ws_user = sh.worksheet("user")
        header = ["name", "job", "floor", "gold", "tickets", "xp", "pet_name"]
        # 安全に値を取り出す
        update_values = [new_user_data.get(k, DEFAULT_USER[k]) for k in header]
        
        cell_range = f"A2:{chr(65+len(header)-1)}2"
        ws_user.update(range_name=cell_range, values=[update_values])
        
    except Exception as e:
        st.error(f"データ保存エラー: {e}")

# --- 3. ゲームロジック ---

def calculate_points(base_pt, task_type, user_job):
    job_info = JOBS.get(user_job, JOBS["Novice"])
    multiplier = job_info["multi"]
    is_jackpot = False
    
    if "bonus_type" in job_info and job_info["bonus_type"] == task_type:
        multiplier = 1.5
    
    if user_job == "Jester" and job_info.get("gamble"):
        if random.random() < 0.10:
            multiplier = 10.0
            is_jackpot = True
            
    final_pt = int(base_pt * multiplier)
    return final_pt, is_jackpot

def get_avatar_url(seed, type="adventurer"):
    base = "https://api.dicebear.com/9.x/pixel-art/svg"
    return f"{base}?seed={seed}"

def get_pet_comment(df_log, user_name):
    if df_log.empty:
        return "冒険の始まりだね！"
    try:
        # 日付列チェック
        if 'date' not in df_log.columns: return "今日も頑張ろう！"
        
        df_log['date'] = pd.to_datetime(df_log['date'])
        today = datetime.date.today()
        today_tasks = df_log[df_log['date'].dt.date == today]
        
        if len(today_tasks) == 0: return "まずは1つ、簡単なことから始めよう？"
        elif len(today_tasks) >= 3: return f"すごい！調子いいね、{user_name}！"
        else: return "その調子！"
    except:
        return "今日もいい日になりますように！"

def check_missions(df_log, user_data):
    completed = []
    if df_log.empty or 'date' not in df_log.columns:
        return completed, user_data

    try:
        df_log['date'] = pd.to_datetime(df_log['date'])
        today = datetime.date.today()
        
        # Daily
        today_tasks = df_log[df_log['date'].dt.date == today]
        if len(today_tasks) >= MISSIONS["daily"]["target"]:
            completed.append("daily")

        # Weekly
        start_week = today - datetime.timedelta(days=today.weekday())
        week_tasks = df_log[df_log['date'].dt.date >= start_week]
        if len(week_tasks) >= MISSIONS["weekly"]["target"]:
            completed.append("weekly")
    except:
        pass
    return completed, user_data

# --- 4. メインアプリ ---

def main():
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide")
    st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=DotGothic16&display=swap');
    * { font-family: 'DotGothic16', sans-serif; }
    .stButton>button { border-radius: 0px; border: 2px solid #333; }
    </style>""", unsafe_allow_html=True)

    if "sh" not in st.session_state:
        st.session_state.sh = connect_to_gsheet()
    
    if st.session_state.sh:
        user_data, df_log = load_data(st.session_state.sh)
    else:
        st.stop()

    # サイドバー
    with st.sidebar:
        st.title("🛡️ ステータス")
        # 安全に値を取得(.getを使う)
        name = user_data.get("name", "Player")
        st.image(get_avatar_url(name), width=100)
        
        job = user_data.get("job", "Novice")
        job_info = JOBS.get(job, JOBS["Novice"])
        
        st.write(f"**名前:** {name}")
        st.write(f"**職業:** {job_info['icon']} {job_info['name']}")
        st.write(f"**Lv:** {user_data.get('floor', 1)} (XP: {user_data.get('xp', 0)})")
        st.write(f"**Gold:** {user_data.get('gold', 0)} G")
        
        st.markdown("---")
        pet_name = user_data.get("pet_name", "ポチ")
        st.subheader(f"🐾 相棒: {pet_name}")
        st.image(get_avatar_url(pet_name, type="monster"), width=80)
        st.info(f"「{get_pet_comment(df_log, name)}」")

    # メインエリア
    st.title(f"{PAGE_ICON} {PAGE_TITLE}")
    tab1, tab2, tab3 = st.tabs(["⚔️ クエスト", "📜 ミッション", "📊 記録"])

    with tab1:
        col1, col2 = st.columns([2, 1])
        with col1:
            task_name = st.text_input("クエスト名", placeholder="例: 皿洗い")
            c1, c2 = st.columns(2)
            with c1: task_type = st.selectbox("属性", ["一般", "筋トレ", "勉強", "掃除"])
            with c2: difficulty = st.select_slider("難易度", options=[10, 30, 50, 100], value=30)
            
            if st.button("クエスト完了！", type="primary", use_container_width=True):
                if task_name:
                    earned_pt, jackpot = calculate_points(difficulty, task_type, job)
                    
                    # データの型変換を安全に
                    current_xp = int(user_data.get("xp", 0))
                    current_gold = int(user_data.get("gold", 0))
                    
                    user_data["xp"] = current_xp + earned_pt
                    user_data["gold"] = current_gold + earned_pt
                    
                    log_entry = {
                        "date": str(datetime.datetime.now()), "task": task_name,
                        "type": task_type, "points": earned_pt,
                        "bonus_flag": "JACKPOT" if jackpot else ""
                    }
                    save_task_to_db(st.session_state.sh, log_entry, user_data)
                    
                    if jackpot: st.balloons(); st.success(f"🎰 ポイント10倍！ +{earned_pt}!")
                    else: st.toast(f"✅ 完了！ +{earned_pt} XP")
                    time.sleep(1); st.rerun()

    with tab2:
        completed, _ = check_missions(df_log, user_data)
        st.write(f"**📅 デイリー: {MISSIONS['daily']['desc']}**")
        if "daily" in completed: st.success("達成済み！")
        else: st.info("挑戦中...")

    with tab3:
        if not df_log.empty and 'date' in df_log.columns:
            df_log['date'] = pd.to_datetime(df_log['date'])
            daily_sum = df_log.groupby(df_log['date'].dt.date)['points'].sum().reset_index()
            fig = px.bar(daily_sum, x='date', y='points', title="日別獲得XP")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_log.sort_values('date', ascending=False), use_container_width=True)
        else:
            st.info("データがありません")

if __name__ == "__main__":
    main()