from flask import Flask
app = Flask(__name__)

from flask import request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import os
import requests

# 設定 OpenAI 和 LINE API 金鑰
openai.api_key = os.getenv('OPENAI_API_KEY')
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler1 = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# Spoonacular API 金鑰
SPOONACULAR_API_KEY = os.getenv('SPOONACULAR_API_KEY')
BASE_URL = "https://api.spoonacular.com/recipes/complexSearch"

# 記錄 OpenAI 回應的訊息計數器
openai_message_count = 0

# 定義根據食物名稱查找食譜的函數
def get_recipe_by_name(food_name):
    params = {
        'query': food_name,
        'apiKey': SPOONACULAR_API_KEY
    }
    response = requests.get(BASE_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['results']:
            recipe = data['results'][0]  # 取第一個食譜
            return f"這是關於 {food_name} 的食譜：\n\n" \
                   f"名稱: {recipe['title']}\n" \
                   f"食譜網址: {recipe['sourceUrl']}\n" \
                   f"預估準備時間: {recipe['readyInMinutes']} 分鐘"
        else:
            return f"抱歉，沒有找到 {food_name} 的食譜。"
    else:
        return "無法取得食譜資料，請稍後再試。"

@app.route('/callback', methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler1.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler1.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global openai_message_count  # 使用全局計數器
    text1 = event.message.text.lower()  # 使用小寫來方便處理
    response_text = ""

    # 根據不同的食物名稱回應
    if "披薩" in text1:
        response_text = "披薩是一道起源於意大利的美食，通常由麵團、番茄醬、起司和各種配料組成。"
    elif "壽司" in text1:
        response_text = "壽司是日本的傳統料理，通常由醋飯和海鮮或蔬菜等食材製成。"
    elif "漢堡" in text1:
        response_text = "漢堡是一種以麵包和肉餅為主的美國快餐食品，常搭配生菜、番茄、醬料等。"
    elif "冰淇淋" in text1:
        response_text = "冰淇淋是一種冷凍甜點，通常由奶油、糖和水果或巧克力等口味製成。"
    else:
        # 若無匹配的食物名稱，讓機器人嘗試查找食譜
        response_text = get_recipe_by_name(text1)
        # 如果查找食譜失敗，則讓 OpenAI 回應
        if "這是關於" not in response_text:
            try:
                response = openai.ChatCompletion.create(
                    messages=[
                        {"role": "user", "content": text1}
                    ],
                    model="gpt-3.5-turbo-0125",
                    temperature=0.5,
                )
                response_text = response['choices'][0]['message']['content'].strip()
                
                # 每當 OpenAI 回應時，計數器加 1
                openai_message_count += 1
                print(f"OpenAI 已回應 {openai_message_count} 次")
            except:
                response_text = '發生錯誤！'

    # 回應使用者
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response_text))

    # 若想要顯示目前的計數，可以回應計數器
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"目前 OpenAI 回應的總數是: {openai_message_count}"))

if __name__ == '__main__':
    app.run()
