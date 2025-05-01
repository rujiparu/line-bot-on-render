from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError
import os
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import openai

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

# --- Google Sheets API設定 ---
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SPREADSHEET_ID = '18uzTFvHbNdM3D-036IgcEO81yNbZzjeMd0oEa1JGhgw'

# 認証ファイルのパス（Render環境では環境変数を使って設定する）
import base64

base64_creds = os.environ.get("GOOGLE_CREDS_BASE64")
creds_path = "/tmp/credentials.json"

with open(creds_path, "wb") as f:
    f.write(base64.b64decode(base64_creds))

creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)

gc = gspread.authorize(creds)
worksheet = gc.open_by_key(SPREADSHEET_ID).sheet1

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# ChatGPTから返答をもらう関数
def ask_chatgpt(user_input):
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # または "gpt-4"（課金状況による）
        messages=[
            {"role": "system", "content": "あなたは小学生の保護者に優しく答えるアシスタントです。"},
            {"role": "user", "content": user_input}
        ],
        max_tokens=500,
        temperature=0.7
    )
    
    return response.choices[0].message.content.strip()


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text.strip()

    try:
        # ここでChatGPTに質問を送って返答を受け取る
        reply = ask_chatgpt(user_text)
    except Exception as e:
        reply = f"エラーが発生しました：{e}"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

def get_schedule_for_tomorrow():
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y/%m/%d')
    data = worksheet.get_all_records()

    for row in data:
        if row['日付'] == tomorrow:
            return f"【{tomorrow}の予定】\n🧳持ち物: {row['持ち物']}\n📅行事: {row['行事']}\n📚時間割: {row['時間割']}"

    return f"{tomorrow} のデータが見つかりませんでした。"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))





