# -*- coding: utf-8 -*-
from flask import Flask, request, abort, url_for, send_from_directory
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextSendMessage, TextMessage, TemplateSendMessage, ButtonsTemplate, \
    MessageAction, ImageSendMessage, ImageMessage, AudioSendMessage
import openai
import os
import firebase_admin
from firebase_admin import credentials, db
import logging
from gtts import gTTS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime
import pytz
from linebot.models import CarouselTemplate, CarouselColumn

# 初始化 Flask 應用
app = Flask(__name__)

# 初始化排程器
scheduler = BackgroundScheduler()
scheduler.start()

# 保存當前問題的字典
current_questions = {}

# 全局字典來存儲用戶的文字輸入
current_texts = {}

# 獲取環境變量
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LINE_BOT_TOKEN = os.getenv("LINE_BOT_TOKEN")
LINE_BOT_SECRET = os.getenv("LINE_BOT_SECRET")
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS")
FIREBASE_URL = os.getenv("FIREBASE_URL")

# Debugging: Print environment variables to ensure they are loaded correctly
#print(f"OPENAI_API_KEY: {OPENAI_API_KEY}")
#print(f"LINE_BOT_TOKEN: {LINE_BOT_TOKEN}")
#print(f"LINE_BOT_SECRET: {LINE_BOT_SECRET}")
#print(f"FIREBASE_CREDENTIALS: {FIREBASE_CREDENTIALS}")
#print(f"FIREBASE_URL: {FIREBASE_URL}")

# 確保腳本在環境變量未設置時停止運行
if not all([OPENAI_API_KEY, LINE_BOT_TOKEN, LINE_BOT_SECRET, FIREBASE_CREDENTIALS, FIREBASE_URL]):
    print("One or more environment variables are not set.")
    exit(1)

# 初始化 LineBot API 和 WebhookHandler
line_bot_api = LineBotApi(LINE_BOT_TOKEN)
handler = WebhookHandler(LINE_BOT_SECRET)
openai.api_key = OPENAI_API_KEY

# 初始化 Firebase Admin SDK
cred = credentials.Certificate('C:/Users/USER/Documents/pythonProject2/submission-query-bot/sad-frog-99537-firebase-adminsdk-vk5i3-9b3a03c9e5.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': "https://sad-frog-99537-default-rtdb.firebaseio.com/"
})
# 設置日誌
logging.basicConfig(level=logging.INFO)

# 學習資源字典（可以更新）
learning_resources = {
    '大一': [
        {'subject': '普通物理學', 'link': 'https://www.khanacademy.org/science/physics'},
        {'subject': '工程力學', 'link': 'https://www.coursera.org/learn/engineering-mechanics'},
        {'subject': '計算機概論', 'link': 'https://www.khanacademy.org/computing/computer-programming'},
        {'subject': '微積分', 'link': 'https://www.khanacademy.org/math/calculus-1'},
        {'subject': '工程圖學與模擬', 'link': 'https://www.coursera.org/learn/technical-drawing'},
        {'subject': '材料力學', 'link': 'https://www.coursera.org/learn/mechanics-of-materials'},
        {'subject': '工程動力學', 'link': 'https://www.coursera.org/learn/engineering-dynamics'},
        {'subject': '程式設計', 'link': 'https://www.coursera.org/specializations/python'},
        {'subject': '線性代數', 'link': 'https://www.khanacademy.org/math/linear-algebra'},
        {'subject': '工程科學暨創新概論', 'link': 'https://www.coursera.org/learn/introduction-engineering'}
    ],
    '大二': [
        {'subject': '資料結構', 'link': 'https://www.coursera.org/specializations/data-structures-algorithms'},
        {'subject': '電路學', 'link': 'https://www.khanacademy.org/science/electrical-engineering'},
        {'subject': '材料科學', 'link': 'https://www.coursera.org/learn/materials-science'},
        {'subject': '工程數學', 'link': 'https://www.khanacademy.org/math/differential-equations'},
        {'subject': '熱力學', 'link': 'https://www.khanacademy.org/science/physics/thermodynamics'},
        {'subject': '電子學', 'link': 'https://www.allaboutcircuits.com/'},
        {'subject': '材料機械性質學', 'link': 'https://www.coursera.org/learn/mechanics-of-materials'},
        {'subject': '邏輯設計', 'link': 'https://www.coursera.org/learn/digital-systems'}
    ],
    '大三': [
        {'subject': '自動控制', 'link': 'https://www.coursera.org/learn/modern-robotics-motion-planning'},
        {'subject': '計算機組織與組合語言', 'link': 'https://ocw.aca.ntu.edu.tw/ntu-ocw/index.php/ocw/cou/101S210'},
        {'subject': '流體力學', 'link': 'https://ocw.aca.ntu.edu.tw/ntu-ocw/index.php/ocw/cou/110S201'},
        {'subject': '微處理機與介面設計(含實習)', 'link': 'https://www.coursera.org/specializations/microcontrollers'},
        {'subject': '計算機演算法', 'link': 'https://www.coursera.org/specializations/algorithms'},
        {'subject': '通訊系統', 'link': 'https://www.coursera.org/learn/digital-communication-systems'},
        {'subject': '機器人設計與製作', 'link': 'https://www.coursera.org/specializations/robotics'},
        {'subject': '電子電路', 'link': 'https://www.coursera.org/specializations/robotics'},
        {'subject': '應用電磁學', 'link': 'https://ocw.aca.ntu.edu.tw/ntu-ocw/index.php/ocw/cou/100S112'},
        {'subject': '跨領域半導體產業概論', 'link': 'https://www.coursera.org/learn/semiconductor-industry'},
        {'subject': '半導體製程概論', 'link': 'https://www.coursera.org/learn/semiconductor-devices'},
        {'subject': '數值方法', 'link': 'https://www.coursera.org/learn/numerical-methods'},
        {'subject': '熱傳學', 'link': 'https://www.coursera.org/learn/heat-transfer'},
        {'subject': '近代物理', 'link': 'https://ocw.aca.ntu.edu.tw/ntu-ocw/index.php/ocw/cou/105S111'},
        {'subject': '機器人原理', 'link': 'https://www.coursera.org/specializations/robotics'},
        {'subject': '作業系統', 'link': 'https://www.coursera.org/learn/operating-systems'},
        {'subject': '控制理論', 'link': 'https://www.coursera.org/learn/computational-thinking-problem-solving'},
        {'subject': '計算思維及問題解決', 'link': 'https://www.coursera.org/learn/computational-thinking-problem-solving'},
        {'subject': '量子計算導論', 'link': 'https://www.coursera.org/learn/quantum-computing'},
        {'subject': '半導體通路商產業分析', 'link': 'https://www.coursera.org/learn/semiconductor-industry'}
    ],
    '大四': [
        {'subject': '資料庫系統', 'link': 'https://ocw.nthu.edu.tw/ocw/index.php?page=course&cid=257'},
        {'subject': '機器學習工程應用', 'link': 'https://www.coursera.org/learn/machine-learning'}
    ]
}

# 將消息保存到實時數據庫的函數
def save_message_to_realtime_db(group_id, user_id, message_type, message_content, is_bot=False):
    timestamp = datetime.utcnow().strftime('%Y:%m:%d %H:%M:%S')
    if group_id == 'private':
        ref = db.reference(f'Private/{user_id if not is_bot else "bot_id"}/{timestamp}')
    else:
        ref = db.reference(f'Group/{group_id}/{user_id if not is_bot else "bot_id"}/{timestamp}')
    ref.set({
        'message_content': message_content,
        'message_type': message_type
    })
    app.logger.info(f"Saved message to Firebase: {message_content}")

# 生成 GPT 回應的函數
def generate_gpt_response(input_string):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "你現在扮演的是個說繁體中文的台灣大學生，目的在於與同儕討論與回答同儕的問題。"},
            {"role": "user", "content": input_string}
        ]
    )
    return response['choices'][0]['message']['content']

# 生成 GPT4o 回應的函數
def generate_gpt4o_response(image_url, question, return_question_and_answer=False):
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system",
             "content": "你現在扮演的是個說繁體中文的台灣大學生，目的在於與同儕討論與回答同儕的問題。"
             },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url,
                        },
                    },
                ],
            }
        ],
        max_tokens=300,
    )

    response_content = response.choices[0]['message']['content']
    app.logger.info(f"GPT-4o response content: {response_content}")

    if return_question_and_answer:
        # 檢查回應內容是否包含預期的問題和答案部分，並去除空白行
        lines = [line.strip() for line in response_content.split('\n') if line.strip()]
        app.logger.info(f"Response lines after removing empty lines: {lines}")

        if len(lines) >= 2:
            question_part = lines[0]  # 假設第一行是問題
            correct_answer = lines[1]  # 假設第二行是正確答案
        else:
            app.logger.error("Unexpected response format: less than 2 lines")
            question_part = response_content.strip()
            correct_answer = "無法找到正確答案"

        app.logger.info(f"Extracted question: {question_part}")
        app.logger.info(f"Extracted correct answer: {correct_answer}")

        return question_part, correct_answer
    else:
        return response_content

# 評估用戶答案的函數（在@考考我的功能中使用）
def evaluate_answer(user_answer, correct_answer):
    prompt = f"以下是正確答案和使用者的答案，請判斷使用者的答案是否正確並回覆「正確」或「不正確」，只要意義相近就代表正確，意義不相近就代表錯誤，並附上理由或正確答案：\n\n正確答案：{correct_answer}\n\n使用者答案：{user_answer}"
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "你是一個智能助理，能夠判斷答案是否正確。"},
            {"role": "user", "content": prompt}
        ]
    )
    return response['choices'][0]['message']['content'].strip()

# 生成創意點子的函數
def generate_brainstorm_ideas(topic):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "你現在扮演的是個說繁體中文的台灣大學生，目的在於與同儕討論與回答同儕的問題。"},
            {"role": "user", "content": f"请为以下主题生成一些创意点子和想法: {topic}"}
        ],
        max_tokens=150,
        temperature=0.7
    )
    ideas = response['choices'][0]['message']['content'].strip()
    return ideas

# 生成反思性問題的函數
def generate_reflection_questions(issue):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "你現在扮演的是個說繁體中文的台灣大學生，目的在於與同儕討論與回答同儕的問題。"},
            {"role": "user", "content": f"请为以下问题生成一些反思性问题和角度: {issue}"}
        ],
        max_tokens=150,
        temperature=0.7
    )
    reflection_questions = response['choices'][0]['message']['content'].strip()
    return reflection_questions

# 處理提醒功能的函數
def send_reminder(user_id, message):
    line_bot_api.push_message(user_id, TextSendMessage(text=f"提醒：{message}的截止日期到了！"))

@app.route('/')
def home():
    return "Hello, World! This is the home page."

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        app.logger.error("Invalid signature. Check your channel secret and access token.")
        abort(400)
    return 'OK'

@app.route('/images/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(os.getcwd(), filename)

#最重要的部分：主要用於接受text形式的信息，以作下一步的操作
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    text = event.message.text
    group_id = event.source.group_id if event.source.type == 'group' else 'private'
    user_id = event.source.user_id
    save_message_to_realtime_db(group_id, user_id, 'text', text)
    app.logger.info(f"Received message: {event.message.text}")

    #新手友善功能
    if text.lower() == "@sadfrog":
        buttons_template_message = TemplateSendMessage(
            alt_text='歡迎來到Sad Frog',
            template=ButtonsTemplate(
                title='WELCOME TO SAD FROG',
                text='以下是功能的介紹，歡迎你來使用',
                actions=[
                    MessageAction(label='功能查詢', text='功能查詢')
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template_message)

    elif text.lower() == "功能查詢":
        help_message = ('跟著Sad Frog一步步探索以下功能：\n\n1. 輸入任意一段文字或一張圖片，點擊你需要的功能！\n\n '
                        '2. 文字輸入: 可以進行問答、抓重點、翻譯、轉語音、轉圖片的功能\n\n'
                        '3. 圖片輸入: 可以進行問答、抓重點、考考我的功能\n\n'
                        '4. 其他功能: 可以推薦學習資源、頭腦風暴、問題反思、設定截止日期')
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=help_message))

#處理文字輸入的邏輯
    elif "@文字提問" in text:
        question = text.split("@文字提問 ")[1]
        response = generate_gpt_response(question)
        save_message_to_realtime_db(group_id, user_id, 'response', response, is_bot=True)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

    elif "@文字重點" in text:
        transcription = "請用繁體中文總結以下內容：" + text.split("@文字重點 ")[1]
        response = generate_gpt_response(transcription)
        save_message_to_realtime_db(group_id, user_id, 'response', response, is_bot=True)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

    elif "@文字翻譯" in text:
        transcription = "如果輸入是英文，就把將以下內容翻譯成繁體中文；如果輸入是繁體中文，就把將以下內容翻譯成英文；：" + text.split("@文字翻譯 ")[1]
        response = generate_gpt_response(transcription)
        save_message_to_realtime_db(group_id, user_id, 'response', response, is_bot=True)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

    elif "@文字轉語音" in text:
        prompt = text.split("@文字轉語音 ")[1]
        tts = gTTS(text=prompt, lang='zh')
        audio_path = f"{event.message.id}.mp3"
        tts.save(audio_path)
        # Use _scheme='https' 確保URL是HTTPS
        audio_url = url_for('uploaded_file', filename=audio_path, _external=True, _scheme='https')
        audio_message = AudioSendMessage(
            original_content_url=audio_url,
            duration=60000  # 60 seconds duration, you can adjust it based on your audio file
        )
        save_message_to_realtime_db(group_id, user_id, 'audio', audio_url, is_bot=True)
        line_bot_api.reply_message(event.reply_token, audio_message)

    elif "@文字轉圖片" in text:
        prompt = text.split("@文字轉圖片 ")[1]
        response = openai.Image.create(
            prompt=prompt,
            model="dall-e-3",
            size="1024x1024",
            response_format="url"
        )
        image_url = response['data'][0]['url']
        image_message = ImageSendMessage(
            original_content_url=image_url,
            preview_image_url=image_url
        )
        save_message_to_realtime_db(group_id, user_id, 'image', image_url, is_bot=True)
        line_bot_api.reply_message(event.reply_token, image_message)

#處理圖片輸入的邏輯
    elif "@理解圖片" in text:
        image_url = text.split("@理解圖片 ")[1]
        question = '請問這張圖片中有什麼？'  # 替換為用戶的問題
        response = generate_gpt4o_response(image_url, question)
        save_message_to_realtime_db(group_id, user_id, 'response', response, is_bot=True)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

        # 處理完圖片後刪除文件
        file_path = image_url.split('/')[-1]
        #os.remove(os.path.join(os.getcwd(), file_path))    #這行可以加或不加，主要目的是在執行完@理解圖片之後，決定要不要刪除本地圖片

    elif "@回答圖片" in text:
        image_url = text.split("@回答圖片 ")[1]
        question = '請解釋並回答圖片中的問題。'  # 替換為用戶的問題
        response = generate_gpt4o_response(image_url, question)
        save_message_to_realtime_db(group_id, user_id, 'response', response, is_bot=True)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

        # 處理完圖片後刪除文件
        file_path = image_url.split('/')[-1]
        #os.remove(os.path.join(os.getcwd(), file_path))    #這行可以加或不加，主要目的是在執行完@回答圖片之後，決定要不要刪除本地圖片

    elif "@筆記圖片" in text:
        image_url = text.split("@筆記圖片 ")[1]
        question = '請用繁體中文整理圖片中的重點，並條列出圖片中的重點。'  # 替換為用戶的問題
        response = generate_gpt4o_response(image_url, question)
        save_message_to_realtime_db(group_id, user_id, 'response', response, is_bot=True)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

        # 處理完圖片後刪除文件
        file_path = image_url.split('/')[-1]
        #os.remove(os.path.join(os.getcwd(), file_path))    #這行可以加或不加，主要目的是在執行完@筆記圖片之後，決定要不要刪除本地圖片

    elif "@考考我" in text:
        image_url = text.split("@考考我 ")[1]
        question, correct_answer = generate_gpt4o_response(image_url,
                                                           '請用圖片的語言為主，根據圖片內容的重點，生成一個簡單提問。換行后產出答案。',
                                                           return_question_and_answer=True)
        # 檢查返回的問題和答案是否正確
        app.logger.info(f"Generated question: {question}")
        app.logger.info(f"Generated correct answer: {correct_answer}")

        # 保存問題和正確答案到全局字典
        if user_id not in current_questions:
            current_questions[user_id] = []
        current_questions[user_id].append({
            'question': question,
            'correct_answer': correct_answer
        })

        save_message_to_realtime_db(group_id, user_id, 'response', question, is_bot=True)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=question+"\n(輸入 @回答[你的答案])"))

    elif text.startswith("@回答 "):
        user_answer = text.split("@回答 ")[1].strip()
        app.logger.info(f"User answer: {user_answer}")

        # 從全局字典中檢索問題和正確答案
        if user_id in current_questions and current_questions[user_id]:
            current_question = current_questions[user_id].pop(0)
            correct_answer = current_question['correct_answer'].strip()
        else:
            correct_answer = "無法找到正確答案"
            response = "沒有找到需要回答的問題。請先使用 @考考我 提問。"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))
            return

        app.logger.info(f"Correct answer: {correct_answer}")

        # 使用 OpenAI 評估用戶的答案(這裏的評估方式還可以用分數)
        evaluation_result = evaluate_answer(user_answer, correct_answer)
        app.logger.info(f"Evaluation result: {evaluation_result}")

        # 直接輸出評估結果
        response = evaluation_result

        save_message_to_realtime_db(group_id, user_id, 'response', response, is_bot=True)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

    elif "@不處理" in text:
        image_url = text.split("@不處理 ")[1]
        # 處理完圖片後刪除文件
        file_path = image_url.split('/')[-1]
        os.remove(os.path.join(os.getcwd(), file_path))

#其他功能的操作邏輯
    elif text == "探索其他功能":
        buttons_template_message = TemplateSendMessage(
            alt_text='其他功能選項',
            template=ButtonsTemplate(
                title='其他功能',
                text='請選擇功能',
                actions=[
                    MessageAction(label='推薦資源', text='@[推薦資源] 功能說明'),
                    MessageAction(label='頭腦風暴', text='@[頭腦風暴] 功能說明'),
                    MessageAction(label='問題反思', text='@[問題反思] 功能說明'),
                    MessageAction(label='截止日期', text='@[截止日期] 功能說明')
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template_message)

    elif text == "@[推薦資源] 功能說明":
        response = "使用@推薦資源來獲取學習資源，格式如下：\n@推薦資源 學科名稱\n例如：@推薦資源 工程數學"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

    elif text == "@[頭腦風暴] 功能說明":
        response = "使用@頭腦風暴來生成創意點子，格式如下：\n@頭腦風暴 主題\n例如：@頭腦風暴 AI應用"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

    elif text == "@[問題反思] 功能說明":
        response = "使用@問題反思來生成反思性問題，格式如下：\n@問題反思 問題描述\n例如：@問題反思 如何改進團隊合作"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

    elif text == "@[截止日期] 功能說明":
        response = "使用@截止日期來設置提醒，格式如下：\n@截止日期 YYYY-MM-DD HH:MM 任務名稱\n例如：@截止日期 2024-12-31 23:59 完成期末報告"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

    elif text.lower() == "@推薦資源":
        reply_text = "請選擇你的學習階段並輸入以下關鍵字來獲取推薦資源：\n"
        for year, subjects in learning_resources.items():
            reply_text += f"\n{year}:\n" + "、".join([s['subject'] for s in subjects]) + "\n"
        reply_text += "\n輸入格式為：@推薦資源 [學科名稱]\n例如：@推薦資源 工程數學"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

    elif text.lower().startswith("@推薦資源"):
        subject = text[5:].strip()
        recommendations = []
        for year, subjects in learning_resources.items():
            for s in subjects:
                if subject == s['subject']:
                    recommendations.append(s)

        if recommendations:
            messages = []
            for rec in recommendations:
                messages.append(TextSendMessage(text=f"推薦資源 - {rec['subject']}: {rec['link']}"))
            line_bot_api.reply_message(event.reply_token, messages)
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="抱歉，沒有找到相關的學習資源。"))

    elif text.startswith("@頭腦風暴"):
        topic = text.split("@頭腦風暴 ")[1]
        response = generate_brainstorm_ideas(topic)
        save_message_to_realtime_db(group_id, user_id, 'response', response, is_bot=True)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

    elif text.startswith("@問題反思"):
        issue = text.split("@問題反思 ")[1]
        response = generate_reflection_questions(issue)
        save_message_to_realtime_db(group_id, user_id, 'response', response, is_bot=True)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))

    elif text.startswith("@截止日期"):
        parts = text.split()
        if len(parts) < 4:
            error_message = "格式錯誤：請使用@截止日期 YYYY-MM-DD HH:MM 任務名稱。"
            save_message_to_realtime_db(group_id, user_id, 'response', error_message, is_bot=True)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=error_message))
        else:
            try:
                _, date_str, time_str, *task = parts
                task_name = ' '.join(task)
                deadline_str = f"{date_str} {time_str}"
                deadline = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")
                # 轉換為本地時區（如果需要）
                deadline = pytz.timezone('Asia/Taipei').localize(deadline)
                trigger = DateTrigger(run_date=deadline)

                # 設置提醒
                scheduler.add_job(send_reminder, trigger, args=[user_id, task_name])

                response = f"提醒已設置，將在{deadline_str}提醒你{task_name}的截止日期到了。"
                save_message_to_realtime_db(group_id, user_id, 'response', response, is_bot=True)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response))
            except Exception as e:
                error_message = f"格式錯誤：請使用@截止日期 YYYY-MM-DD HH:MM 任務名稱。錯誤信息: {str(e)}"
                save_message_to_realtime_db(group_id, user_id, 'response', error_message, is_bot=True)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=error_message))

    #定義當使用者輸入非指定文字的時候，系統會統一輸出button template指引使用者的下一步
    else:
        current_texts[user_id] = text
        # 利用CarouselTemplate，定義每個button可以輸出什麽text
        carousel_template_message = TemplateSendMessage(
            alt_text='選擇文字處理選項',
            template=CarouselTemplate(
                columns=[
                    CarouselColumn(
                        title='你想要如何處理這段文字？',
                        text='第一頁',
                        actions=[
                            MessageAction(label='回答我', text='@文字提問 '+current_texts[user_id]),
                            MessageAction(label='抓重點', text='@文字重點 '+current_texts[user_id]),
                            MessageAction(label='翻譯', text='@文字翻譯 '+current_texts[user_id])
                        ]
                    ),
                    CarouselColumn(
                        title='你想要如何處理這段文字？',
                        text='第二頁',
                        actions=[
                            MessageAction(label='念出來', text='@文字轉語音 '+current_texts[user_id]),
                            MessageAction(label='轉圖片', text='@文字轉圖片 '+current_texts[user_id]),
                            MessageAction(label='探索其他功能', text='探索其他功能')
                        ]
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, carousel_template_message)


#定義使用者發送圖片之後的操作
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    message_content = line_bot_api.get_message_content(event.message.id)
    file_path = os.path.join(os.getcwd(), f'{event.message.id}.jpg')
    with open(file_path, 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)

    image_url = url_for('uploaded_file', filename=f'{event.message.id}.jpg', _external=True)
    group_id = event.source.group_id if event.source.type == 'group' else 'private'
    user_id = event.source.user_id
    save_message_to_realtime_db(group_id, user_id, 'image', image_url)

    #利用CarouselTemplate，定義每個button可以輸出什麽text，指引使用者下一步操作
    carousel_template_message = TemplateSendMessage(
        alt_text='選擇圖片處理選項',
        template=CarouselTemplate(
            columns=[
                CarouselColumn(
                    title='你想要如何處理這張圖片？',
                    text='第一頁',
                    actions=[
                        MessageAction(label='我想知道', text=f'@理解圖片 {image_url}'),
                        MessageAction(label='回答我', text=f'@回答圖片 {image_url}'),
                        MessageAction(label='抓重點', text=f'@筆記圖片 {image_url}')
                    ]
                ),
                CarouselColumn(
                    title='你想要如何處理這張圖片？',
                    text='第二頁',
                    actions=[
                        MessageAction(label='考考我', text=f'@考考我 {image_url}'),
                        MessageAction(label='不處理', text=f'@不處理 {image_url}'),
                        MessageAction(label='探索其他功能', text='探索其他功能')
                    ]
                )
            ]
        )
    )
    line_bot_api.reply_message(event.reply_token, carousel_template_message)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

#功能一：獲取學習資源
#功能二：設定提醒作業截止時間
#功能三：文字輸入或者拍照輸入，協助抓重點、問問題、評分
#功能四：文字輸入或者拍照輸入，翻譯、判斷grammar、讀出來
#功能五：創意靈感

'''
我想整理我的功能，現在如果我作爲使用者，當我輸入文字或者圖片，linebot會通過template=ButtonsTemplate(或者其他template)，來詢問我是想要實現哪一些功能？包括：
1）我想知道（對使用者的文字輸入或圖片輸入用@問題來作爲提問）
2）抓重點（對文字輸入使用@摘要，對圖片輸入使用@圖筆記，如果圖片裏面沒有文字内容，就用@理解圖片）
3）考考我（此時文字輸入或圖片輸入是使用者輸入的一段課文或者資訊，你要抓取其中重點并向使用者提問，使用者回答之後，你需要再回復答案，並給予評分）
4）我想翻譯（對使用者的文字輸入或圖片輸入用@翻譯成繁體中文）
5）讀出來（對使用者的圖片輸入用@文字轉語音）
6）不處理（即使用@不處理）

圖片功能：
1）我想知道--@理解圖片
2）回答我 --@圖答題
3）抓重點 --@圖筆記
4）考考我 --@考考我 
5）不處理 --@不處理 
6）探索其他功能（如果使用者點選這個，就出現新的ButtonsTemplate，告訴使用者，有推薦資源、頭腦風暴、問題反思、截止日期的功能，如果使用者點進去，系統就會告訴他有關功能的使用格式）
#圖片功能沒有翻譯，因爲可以用“我想知道”的功能取代

文字功能：
1）回答我 --@問題
2）抓重點 --@摘要
3）我想翻譯 --@翻譯
4）讀出來 --@文字轉語音
5）轉圖片 --@文字轉圖片
6）探索其他功能（如果使用者點選這個，就出現新的ButtonsTemplate，告訴使用者，有推薦資源、頭腦風暴、問題反思、截止日期的功能，如果使用者點進去，系統就會告訴他有關功能的使用格式）

'''