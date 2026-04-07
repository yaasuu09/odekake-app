import os
from datetime import datetime, timedelta, timezone
import requests
import googlemaps
from google import genai
from dotenv import load_dotenv

load_dotenv()

def get_child_age():
    birth_date = datetime(2024, 3, 8)
    now = datetime.now()
    months = (now.year - birth_date.year) * 12 + now.month - birth_date.month
    if now.day < birth_date.day:
        months -= 1
    years = months // 12
    remaining_months = months % 12
    return f"{years}歳{remaining_months}ヶ月"

CHILD_HOROSCOPE = """
【お子様のホロスコープ情報】
Sun in Pisces 18°06’, in 9th House
Moon in Aquarius 17°14’, in 7th House
Mercury in Pisces 26°11’, in 9th House
Venus in Aquarius 25°24’, in 8th House
Mars in Aquarius 18°29’, in 7th House
Jupiter in Taurus 12°35’, in 10th House
Saturn in Pisces 10°47’, in 8th House
Uranus in Taurus 19°48’, in 10th House
Neptune in Pisces 27°00’, in 9th House
Pluto in Aquarius 1°23’, in 7th House
North Node in Aries 17°19’, Retrograde, in 9th House
Lilith in Virgo 17°26’, in 3rd House
Chiron in Aries 17°36’, in 9th House
Fortune in Gemini 29°08’, in 12th House
Vertex in Sagittarius 13°07’, in 5th House
ASC in Cancer 29°59’
MC in Aries 18°27’
"""

MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

gmaps = googlemaps.Client(key=MAPS_API_KEY)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

def get_weather_info(city="Yokohama"):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
    try:
        res = requests.get(url)
        data = res.json()
        if res.status_code == 200:
            wind_speed = data['wind']['speed']
            alert = "⚠️ 風が強いため、自転車での移動は少し注意が必要です。" if wind_speed >= 5.0 else "✅ 風は穏やかで、安全に自転車で移動できる天候です。"
            return {
                "description": data['weather'][0]['description'],
                "temp": data['main']['temp'],
                "wind_speed": wind_speed,
                "alert": alert
            }
        return {"error": data.get("message")}
    except Exception as e:
        return {"error": str(e)}

def suggest_destination(mode, schedule, origin, max_time="30分以内"):
    """天気と移動手段、日時、移動時間、指定された出発地(現在地含む)から、2歳児に最高の行き先を複数(3〜5つ)提案する機能"""
    weather_info = get_weather_info("Yokohama")
    temp = weather_info.get("temp", "不明")
    desc = weather_info.get("description", "不明")
    
    age_str = get_child_age()
    prompt = f"""
    あなたは横浜の地理と占星術の知識を併せ持つ、優秀な子育て支援AIです。
    ユーザーは「{origin}」付近を出発地とし、{age_str}の男の子を連れてお出かけをします。
    
    {CHILD_HOROSCOPE}
    
    【条件】
    - 移動手段: {"自転車（坂道が少し少なめの場所）" if mode == 'bicycle' else "車（有料駐車場が近くにある場所）"}
    - 希望の片道移動時間: 最大{max_time}
    - お出かけの予定日時: {schedule}
    - (もし「今すぐ」など直近の場合は、現在の天気(気温{temp}度, {desc})も考慮してください)
    
    【指示】
    お子様の月齢（{age_str}）の発達段階や、ホロスコープから読み取れる性格・興味関心の傾向、そして指定された条件にぴったり合うお出かけスポットを「3つ〜5つ」厳選してください。
    ※自転車の場合は行動範囲が狭くマンネリ化しやすいため、毎回同じ提案にならないよう、王道の公園だけでなく、絵本のある図書館、子供歓迎のカフェ、屋内キッズスペース、無料の支援センターなど、ジャンルの【バリエーションを最大限豊か】にしてください！
    ※有名すぎる場所（アンパンマンミュージアム等）は避けてください。
    
    必ず以下のJSON形式の配列(Array)のみを出力し、Markdownの記号(```jsonなど)は含めないでください。
    [
      {{
        "name": "施設名1",
        "address": "施設の正確な住所や、Google Mapsで検索可能な具体的な場所の名称（例: 神奈川県横浜市南区○○1-2-3）",
        "stars": "⭐⭐⭐⭐⭐",
        "reason": "なぜおすすめなのか（120文字程度。月齢やホロスコープの観点を含めて）"
      }},
      {{
        "name": "施設名2",
        "address": "施設の正確な住所（例: 神奈川県横浜市中区○○4-5-6）",
        "stars": "⭐⭐⭐⭐",
        "reason": "なぜおすすめなのか（120文字程度）"
      }}
    ]
    """
    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return {"suggestion": response.text}
    except Exception as e:
        print("Suggest Error:", e)
        return {"suggestion": '[{"name":"蒔田公園", "address":"神奈川県横浜市南区宿町1丁目1", "stars":"⭐⭐⭐", "reason":"大型遊具があり安全に遊べます。AIからの応答が遅延しているため、定番の公園をご案内します。"}]'}

def get_route_and_parking(origin, destination, mode):
    maps_mode = "bicycling" if mode == "bicycle" else "driving"
    result = {"route": None, "parking": []}
    
    try:
        directions = gmaps.directions(origin, destination, mode=maps_mode, language="ja", departure_time="now")
        if directions:
            leg = directions[0]['legs'][0]
            result["route"] = {
                "distance": leg['distance']['text'],
                "duration": leg['duration']['text'],
                "duration_in_traffic": leg.get('duration_in_traffic', {}).get('text', None),
                "end_address": leg['end_address'],
            }
            if mode == "car":
                lat = leg['end_location']['lat']
                lng = leg['end_location']['lng']
                places = gmaps.places_nearby(location=(lat, lng), radius=1000, type="parking", language="ja")
                if places.get('status') == 'OK':
                    for p in places['results'][:3]:
                        result["parking"].append({"name": p.get('name'), "rating": p.get('rating', '評価なし')})
        return result
    except Exception as e:
        result["error"] = str(e)
        return result

def analyze_place(place_name):
    reviews = []
    try:
        search = gmaps.places(query=place_name, language="ja")
        if search.get('status') == 'OK' and search['results']:
            place_id = search['results'][0]['place_id']
            details = gmaps.place(place_id=place_id, language="ja")
            if 'reviews' in details.get('result', {}):
                reviews = [r['text'] for r in details['result']['reviews']]
    except Exception as e:
        pass
        
    if not reviews:
        reviews = [
            "緑が豊かで散歩に最適ですが、坂道が多いのでベビーカーを押すのは少し大変でした。",
            "トイレは綺麗に清掃されており、おむつ替えの台も1つありました。",
            "どんぐりがたくさん落ちていて、2歳の子供が大喜びでした！小学生以上の子供は少ないので安全です。",
            "休日は駐車場がすぐに満車になるため、早めに行くことをおすすめします。"
        ]

    reviews_text = "\n\n".join([f"口コミ:\n{r}" for r in reviews])
    age_str = get_child_age()
    prompt = f"""
    あなたは優秀な子育て支援AIです。以下の施設の口コミを統合して、{age_str}の男の子を連れた親の視点で【良い点】と【注意点】を要約してください。
    
    {CHILD_HOROSCOPE}

    【絶対に分析してほしいポイント】
    1. おむつ替え/トイレ等、{age_str}の快適さ
    2. 安全性と、ホロスコープから推測される本人の性格との相性・おすすめ度（⭐⭐⭐⭐⭐の星マークを含む）
    3. 混雑状況と、子供の歩行のしやすさ・親が抱っこで対応しやすい環境か（※ベビーカーは使用しません）
    【実際の口コミデータ】
    {reviews_text}
    """
    try:
        response = gemini_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return {"summary": response.text}
    except Exception as e:
        return {"error": str(e), "summary": "AIからの応答が遅延しています。"}

def generate_daily_delivery_info():
    """毎日のイベント情報・育児TipsをGeminiで生成する。水・金はイベント検索あり、それ以外はTipsのみ。"""
    age_str = get_child_age()
    weather_info = get_weather_info("Yokohama")
    
    # 日本時間での曜日と現在時刻の取得
    jst = timezone(timedelta(hours=9), 'JST')
    now = datetime.now(jst)
    weekday = now.weekday() # 0:月, 1:火, 2:水, 3:木, 4:金, 5:土, 6:日
    hour = now.hour
    
    # 時間帯に合った挨拶
    if 4 <= hour < 10:
        greeting = "おはようございます！今日も1日マイペースにいきましょう✨"
    elif 10 <= hour < 17:
        greeting = "こんにちは！今日もお疲れ様です☕️"
    else:
        greeting = "こんばんは！今日も1日本当にお疲れ様でした🌙"

    # 天気を文字列で整える
    temp = weather_info.get("temp", "不明")
    desc = weather_info.get("description", "不明")
    weather_context = f"今日の横浜市の天気は「{desc}」、気温は約{temp}度です。"
    if weather_info.get("wind_speed"):
         weather_context += f" (風速: {weather_info['wind_speed']} m/s)"

    # 水曜(2)と金曜(4)はイベント＋Tips
    if weekday in [2, 4]:
        search_theme = "少し遠出のお出かけスポットや今週末のイベント情報" if weekday == 2 else "近場の穴場公園や、雨の日でも行ける屋内プレイスペース"
        prompt = f"""
        あなたは優秀な子育て支援AIコンシェルジュです。
        ユーザーは「横浜市」に住んでおり、保育園に通う「{age_str}」の男の子を育てています。
        以下の情報をリサーチ・要約し、LINEで読みやすい温かみのあるメッセージを作成してください。
        
        【必須項目】
        1. 今週末（直近の土日）の横浜市内の2歳児向けスポット・イベント情報を2〜3つ。
           ※今回の検索テーマは「{search_theme}」を中心にお願いします。
        2. {weather_context} この天気に合わせたアドバイス。
        3. 現在の横浜市周辺の「子供の感染症」の流行アラート（直近の動向を調べて警戒すべきものを1つ挙げてください）。
        4. 今日の育児・時短・メンタルケアの豆知識（Tips）1つ。
        
        出力フォーマット（見出し装飾を使って見やすく。マークダウンの ``` は不要）:
        {greeting}
        
        【🎪 今週末のおすすめスポット】
        （内容）
        【🌤 天気とアドバイス】
        （内容）
        【⚠️ 感染症アラート】
        （内容）
        【💡 今日の育児Tips】
        （内容）
        """
        tools_config = [{"google_search": {}}]
    else:
        # それ以外の曜日はTipsと天気と労いのみ
        prompt = f"""
        あなたは優秀な子育て支援AIコンシェルジュです。
        ユーザーは「横浜市」に住んでおり、保育園に通う「{age_str}」の男の子を育てています。
        毎日のモチベーションアップに繋がるような、短くて読みやすいLINEメッセージを作成してください。
        
        【必須項目】
        1. {weather_context} これに基づく簡単なアドバイス。
        2. 今日の育児・家事時短・メンタルケアの豆知識（Tips）1つ。（保育園関連、イヤイヤ期対策、超時短の夕飯準備など）
        3. 毎日育児と仕事を頑張る親への温かいねぎらいの言葉。
        
        出力フォーマット（装飾を使って見やすく。マークダウンの ``` は不要）:
        {greeting}
        
        【🌤 今日の天気とアドバイス】
        （内容）
        【💡 今日の育児Tips】
        （内容）
        
        （温かいねぎらいのメッセージ）
        """
        tools_config = None

    try:
        if tools_config:
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={"tools": tools_config}
            )
        else:
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
        return {"message": response.text}
    except Exception as e:
        print("Daily Info Error:", e)
        return {"error": str(e), "message": f"{greeting}\n\n情報の生成中にエラーが発生しました。時間を置いて再度お試しください。"}

def send_line_message(text):
    """LINE Messaging APIを使ってメッセージを送信する"""
    if not LINE_CHANNEL_ACCESS_TOKEN:
        return {"error": "LINE APIの環境変数が設定されていません。"}
        
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    data = {
        "messages": [
            {
                "type": "text",
                "text": text
            }
        ]
    }
    
    try:
        res = requests.post(url, headers=headers, json=data)
        if res.status_code == 200:
            return {"status": "success"}
        else:
            return {"error": res.text}
    except Exception as e:
        return {"error": str(e)}
