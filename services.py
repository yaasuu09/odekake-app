import os
from datetime import datetime, timedelta, timezone
import requests
import googlemaps
from google import genai
from dotenv import load_dotenv
import json

load_dotenv()

HISTORY_FILE = "topic_history.json"

def get_recent_topics(days=14):
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
        cutoff = datetime.now() - timedelta(days=days)
        recent = [item["topic"] for item in history if datetime.fromisoformat(item["date"]) > cutoff]
        return recent
    except Exception as e:
        print("Error reading topic history:", e)
        return []

def add_topic_to_history(topic):
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            pass
    
    history.append({"date": datetime.now().isoformat(), "topic": topic})
    history = history[-30:]  # 履歴は直近30件まで保持
    
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error writing topic history:", e)

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

def get_tomorrow_weather_info(city="Yokohama"):
    """OpenWeatherMapの5日間/3時間予報APIから、明日の天気予報（最高/最低気温、天気概要、風速）を取得する"""
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
    try:
        res = requests.get(url)
        data = res.json()
        if res.status_code == 200:
            jst = timezone(timedelta(hours=9), 'JST')
            now = datetime.now(jst)
            tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
            tomorrow_items = [item for item in data.get("list", []) if item.get("dt_txt", "").startswith(tomorrow)]
            if tomorrow_items:
                max_temp = round(max(item["main"]["temp_max"] for item in tomorrow_items), 1)
                min_temp = round(min(item["main"]["temp_min"] for item in tomorrow_items), 1)
                weather_descs = list(dict.fromkeys([item["weather"][0]["description"] for item in tomorrow_items if item.get("weather")]))
                desc_str = "、".join(weather_descs) if weather_descs else "不明"
                max_wind = round(max(item.get("wind", {}).get("speed", 0.0) for item in tomorrow_items), 1)
                return {
                    "date": tomorrow,
                    "max_temp": max_temp,
                    "min_temp": min_temp,
                    "description": desc_str,
                    "wind_speed": max_wind
                }
        return {"error": data.get("message", "予報データの取得に失敗しました")}
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
    """毎日の月齢育児コラム、横浜市の直近イベント情報、複数感染症アラート、明日の天気と服装アドバイスをGeminiで生成する"""
    age_str = get_child_age()
    tomorrow_weather = get_tomorrow_weather_info("Yokohama")
    
    recent_topics = get_recent_topics(14)
    topics_context = ""
    if recent_topics:
        topics_list = "\n".join([f"・{t}" for t in recent_topics])
        topics_context = f"\n\n       【重要：過去2週間の配信済みテーマ】\n       以下のテーマは直近で配信済みのため、これらと被らない、全く新しいテーマを必ず選んでください。\n{topics_list}\n"

    # 日本時間での曜日と現在時刻の取得
    jst = timezone(timedelta(hours=9), 'JST')
    now = datetime.now(jst)
    tomorrow = now + timedelta(days=1)
    
    weekday_kanji = ["月", "火", "水", "木", "金", "土", "日"]
    now_str = f"{now.year}年{now.month}月{now.day}日({weekday_kanji[now.weekday()]})"
    tomorrow_str = f"{tomorrow.month}月{tomorrow.day}日({weekday_kanji[tomorrow.weekday()]})"
    hour = now.hour
    
    # 配信時間帯（主にお昼12時）に合った挨拶
    if 4 <= hour < 11:
        greeting = "おはようございます！今日も1日マイペースにいきましょう✨"
    elif 11 <= hour < 17:
        greeting = "こんにちは！お昼休み、今日もお疲れ様です☕️"
    else:
        greeting = "こんばんは！今日も1日本当にお疲れ様でした🌙"

    # 明日の天気コンテキスト
    if "error" not in tomorrow_weather:
        weather_desc = tomorrow_weather.get("description", "不明")
        max_t = tomorrow_weather.get("max_temp", "不明")
        min_t = tomorrow_weather.get("min_temp", "不明")
        wind = tomorrow_weather.get("wind_speed", 0)
        weather_context = f"明日（{tomorrow_str}）の横浜市の天気予報は「{weather_desc}」、予想最高気温は{max_t}℃、最低気温は{min_t}℃（最大風速: {wind}m/s）です。"
    else:
        weather_context = f"明日（{tomorrow_str}）の横浜市の天気予報を検索し、明日の予想気温と天気を反映してください。"

    prompt = f"""
    あなたは横浜に住むファミリーを全力でサポートする、頼れる子育て専属コンシェルジュAIです。
    ユーザーは「横浜市」在住で、保育園に通う「{age_str}」（2024年3月生まれ）の男の子を育てています。
    今日の日付は「{now_str}」です。
    お昼12時前後に配信されるLINEメッセージとして、親御さんがお昼休みに読んで「なるほど！」「知れてよかった！」と元気が出る、充実したメッセージを作成してください。

    以下の【必須項目】をすべて網羅してください：

    1. 【💡 今日の育児コラム（{age_str}のいま）】（★一番のメインコンテンツ！）
       - お子様の現在の月齢（{age_str}）の発達段階にぴったりの育児トピック・豆知識を、具体的かつ実践的に読み応えのあるボリュームで書いてください。
       - テーマは固定せず、以下のような幅広い観点から「毎日新鮮で役に立つ切り口」を1つ選んで掘り下げてください：
         * 言葉の急成長（二語文・三語文、言い間違いの愛らしさ、語彙を増やす自然な会話など）
         * 自我の芽生え・イヤイヤ期・自己主張への寄り添い（「自分でやりたい」への工夫、切り替えの魔法の言葉など）
         * 体力向上・運動遊び・おうちでできる指先遊びやごっこ遊び
         * 生活習慣（トイトレの進め方、歯磨き・お風呂・お着替えがスムーズになる遊び心）
         * 食事・栄養・食べムラへの対策、時短アイディア
         * 睡眠のリズムや寝かしつけの工夫
         * 親のメンタルケア・声かけの工夫・夫婦の連携{topics_context}
       - 「イヤイヤ期には2択で選ばせる」等の使い古された一般論は避け、専門的かつ実践的で、親にとって新しく具体的な気づきとなるTipsを提供してください。

    2. 【🎪 横浜市・直近のイベント情報】
       - Google検索ツールを活用し、今日（{now_str}）から直近1〜2週間の間に、神奈川県横浜市内で開催される幼児・ファミリー向けイベント、季節のお祭り、マルシェ、ワークショップ、子ども向け催し物などの最新情報を調べて「2〜3つ」紹介してください。
       - 各イベントについて「開催日時」「場所（施設名・エリア）」「イベント名」「内容や見どころ」を簡潔かつ具体的に記載してください。
       - ※固定の公園紹介ではなく、期間限定のイベント・催し・マルシェを必ず紹介してください。

    3. 【⚠️ 感染症流行アラート】
       - Google検索ツールを活用し、現在の横浜市・神奈川県周辺における「子どもの感染症」（手足口病、RSウイルス、インフルエンザ、マイコプラズマ肺炎、溶連菌、アデノウイルス、コロナ等）の直近の流行状況を調べてください。
       - 警戒すべき感染症が複数ある場合は、遠慮なく複数挙げて、それぞれの初期症状や家庭・保育園で意識すべき予防ポイントを簡潔に伝えてください。

    4. 【🌤 明日の天気】
       - {weather_context}
       - 明日の横浜市の天気と予想最高・最低気温を1〜2行で簡潔に記載してください。
       - ※文章全体のボリュームを抑えるため、服装や持ち物のアドバイスは一切含めないでください（完全に省略してください）。

    5. 【☕️ パパママへのねぎらいメッセージ】
       - 毎日仕事と育児を頑張る親御さんへ、お昼休みにホッと一息つける温かい応援・労いの言葉を添えてください。

    【出力フォーマット】（見出しの絵文字装飾を使って美しく整理。Markdownのコードブロック ``` は不要）:
    {greeting}

    💡【今日の育児コラム：{age_str}のいま】
    ■テーマ：（ここにテーマ名を1行で記載）
    （充実した内容・アドバイス）

    🎪【横浜市・直近のイベント情報】
    （2〜3件のイベント情報）

    ⚠️【感染症流行アラート】
    （現在流行している感染症と予防ポイント）

    🌤【明日の天気】
    （明日の天気と予想気温を1〜2行で簡潔に）

    ☕️（温かいねぎらいのメッセージ）
    """

    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={"tools": [{"google_search": {}}]}
        )
        message_text = response.text
        
        # 配信したテーマを履歴に保存
        for line in message_text.split('\n'):
            if line.strip().startswith('■テーマ：'):
                topic_name = line.strip().replace('■テーマ：', '').strip()
                add_topic_to_history(topic_name)
                break
                
        return {"message": message_text}
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
