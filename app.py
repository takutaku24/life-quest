import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

st.title("🔧 スプレッドシート接続テスト")

# あなたのスプレッドシートのID
SHEET_ID = "17YKG8M4kOQN1gZl1zM-LCghU5mv0-twDoxkfy88IXl0"

if st.button("接続して書き込む！"):
    try:
        # 1. 認証の準備
        st.write("1. 鍵の確認中...")
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        # 2. シートを開く
        st.write("2. スプレッドシートを検索中...")
        sheet = client.open_by_key(SHEET_ID).sheet1
        
        # 3. 書き込み
        st.write("3. 書き込みテスト中...")
        # A1セルにテスト文字を書き込む
        sheet.update_acell('A1', '接続テスト大成功！！！')
        
        st.balloons()
        st.success("✨ 完璧です！スプレッドシートのA1に文字が書き込まれました！")
        
    except Exception as e:
        st.error("❌ エラーが発生しました！以下の赤い文字をコピーして教えてください。")
        st.error(f"エラーの種類: {type(e).__name__}")
        st.code(str(e))