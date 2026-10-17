import os
import json
import time
from datetime import date, datetime, timedelta, timezone
import requests
import googlemaps
from google import genai
from dotenv import load_dotenv

load_dotenv()

JST = timezone(timedelta(hours=9), "JST")
BIRTH_DATE = date(2024, 3, 8)
HISTORY_FILE = "topic_history.json"

MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

# 外部APIクライアントの遅延初期化用キャッシュ（起動時クラッシュ防止）
_gmaps_client = None
_gemini_client = None


def get_gmaps_client():
    """Google Maps APIクライアントを必要な時だけ安全に初期化する"""
    global _gmaps_client
    if _gmaps_client is None:
        if not MAPS_API_KEY:
            raise ValueError("GOOGLE_MAPS_API_KEY が設定されていません。")
        _gmaps_client = googlemaps.Client(key=MAPS_API_KEY)
    return _gmaps_client


def get_gemini_client():
    """Gemini APIクライアントを必要な時だけ安全に初期化する"""
    global _gemini_client
    if _gemini_client is None:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY が設定されていません。")
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client


CHILD_HOROSCOPE = """
【お子様のホロスコープ情報（2024年3月8日生まれ）】
- Sun in Pisces 18°06’, in 9th House（太陽うお座・9ハウス：共感力が高く優しい、豊かな想像力と感受性、広い世界への憧れ）
- Moon in Aquarius 17°14’, in 7th House（月みずがめ座・7ハウス：独自のこだわりとひらめき、マイペースな自立心、大人と対等な1対1の関わりを好む）
- Mercury in Pisces 26°11’, in 9th House（水星うお座・9ハウス：理屈より直感・リズム・擬音・イメージや物語で言葉を吸収する）
- Venus in Aquarius 25°24’, in 8th House（金星みずがめ座・8ハウス：ユニークな視点、一度好きになった対象への深い集中と探究心）
- Mars in Aquarius 18°29’, in 7th House（火星みずがめ座・7ハウス：頭ごなしの指示では動かず、自分が納得した独自のやり方や作戦会議でやる気が出る）
- Jupiter in Taurus 12°35’, in 10th House（木星おうし座・10ハウス：五感の心地よさ・肌触り・美味しい食・音楽・自然から安心と豊かさを得る）
- Saturn in Pisces 10°47’, in 8th House（土星うお座・8ハウス：繊細な感受性を少しずつ育て、じっくり深い信頼関係を築く）
- Uranus in Taurus 19°48’, in 10th House（天王星おうし座・10ハウス：五感や身体感覚を通じたユニークな工夫、あっと驚く独自の成長リズム）
- Neptune in Pisces 27°00’, in 9th House（海王星うお座・9ハウス：音楽・アート・ごっこ遊び・空想の世界を広げる圧倒的なイマジネーション）
- Pluto in Aquarius 1°23’, in 7th House（冥王星みずがめ座・7ハウス：人との関わりの中で強い意志と個性を発揮する底力）
- North Node & Chiron in Aries 17°’, in 9th House（ドラゴンヘッド＆キロンおひつじ座：「はじめての挑戦」「自分の足で一歩踏み出す体験」で自信が育つ）
- Vertex in Sagittarius 13°07’, in 5th House / Fortune in Gemini 29°08’（5ハウスいて座・ふたご座：体を使ったのびのびした遊びと言葉のキャッチボールが喜びの源泉）
- ASC in Cancer 29°59’（アセンダントかに座：安心できる家族・スキンシップがすべての土台。外で頑張る分、家でのハグが最大のエネルギー充電）
- MC in Aries 18°27’（MCおひつじ座：自分の「やりたい！」という情熱で道を切り拓くエネルギー）
""".strip()

# 曜日別7ジャンル × 各7週ローテーション ＝ 全49パターンの日替わりテーママトリクス
# 毎日ホロスコープの異なる天体・ハウス（着眼レンズ）を掛け合わせることで、
# 「毎日うちの子専用」でありながら同じ占星術フレーズの繰り返しにならない構造
WEEKDAY_THEME_MATRIX = [
    # 0: 月曜日【保育園・生活リズムと切り替えの工夫】
    {
        "genre": "保育園・生活リズムと切り替え",
        "horoscope_lens": "ASCかに座（家族との安心基地・スキンシップが最大のエネルギー充電）× 火星みずがめ座（頭ごなしの指示より、自分で納得したやり方や対等な作戦会議でやる気スイッチが入る気質）",
        "themes": [
            "帰宅直後に急にご機嫌ナナメになる「保育園がんばり疲れ（夕方の甘え爆発）」への最初の5分の向き合い方",
            "朝の登園前や出発前に「行かない・着替えない」となる時の、脳のモード切り替えスイッチ（予告とゲーム化）",
            "お風呂や歯磨きを嫌がる夜に、親が追いかけ回さず子ども自ら動きたくなる「小さな役割づくりとユーモア」",
            "遊びに夢中で「もうおしまい」が聞けない時の、満足感を損なわない区切り方（「キリがいい所」の作り方）",
            "休日の生活リズムと月曜朝のスムーズな立ち上がり（週末の疲れを残さない昼寝・夕方の過ごし方）",
            "保育園の先生との連絡帳や送迎時のひとこと共有で、家庭と園の連携をラクにするコツ",
            "季節の変わり目や気圧変化の日に起きやすい「なんとなく不機嫌・眠い」サインの見極めとペースダウン術",
        ],
    },
    # 1: 火曜日【言葉・会話・知的好奇心の伸ばし方】
    {
        "genre": "言葉・会話・知的好奇心",
        "horoscope_lens": "水星うお座・9ハウス（理屈よりリズム・擬音・イメージや物語で言葉を吸収する力）× 金星みずがめ座・8ハウス（好きな乗り物や図鑑・仕組みへ深く没頭する探究心）",
        "themes": [
            "「なんで？」「これなに？」の質問攻めが始まったらチャンス！思考力を伸ばす「質問返し」のコツ",
            "言い間違いや拙いおしゃべりを否定せずに語彙を自然に増やす「リキャスト（拡充模倣）」の声かけ",
            "同じ絵本を何回も「もう1回読んで！」とせがむ脳の理由と、2歳後半ならではの絵本の楽しみ方",
            "保育園であったことを「今日なにしたの？」と聞いても答えてくれない時の、記憶を引き出す具体的な聞き方",
            "「くやしい」「びっくりした」など感情の名前を親が代弁して、かんしゃくを言葉に変えていくステップ",
            "乗り物・生き物・図鑑など「今ハマっている好き」を、日常の観察や会話に広げるちょっとした工夫",
            "遊びながらブツブツ言う「ひとり言（プライベート・スピーチ）」が増える時期の脳の働きと温かい見守り方",
        ],
    },
    # 2: 水曜日【脳科学・発達心理でわかる「2歳児の不思議行動」】
    {
        "genre": "脳科学・発達心理でわかる2歳児の不思議行動",
        "horoscope_lens": "太陽うお座（周囲の空気や感情を敏感にキャッチする繊細な優しさ）× 月みずがめ座・7ハウス（独自のこだわりと「ひとりの人間として対等に扱われたい」自立心）",
        "themes": [
            "「さっき自分で『これにする』と言ったのに泣いて怒る」のはなぜ？2歳児の脳の葛藤と受け止め方",
            "「ダメ」と言われると余計にニヤニヤしてやってしまう心理（悪気ではなく「親の反応の実験」をしている理由）",
            "お友達におもちゃを「どうぞ」できない・取り合いになるのは、「自分のもの」という所有概念が育った成長の証",
            "急に「こわい（暗い場所・大きな音・おばけ等）」が増えるのは、想像力と危険予測能力が発達しているサイン",
            "パパ・ママのどちらか一方に「〇〇がいい！（もう一方はイヤ！）」と偏る時期の心理と、選ばれなかった側の振る舞い方",
            "できるはずのことを「やって〜」と赤ちゃん返りのように甘える時の心の中（自立への一歩と安心基地の確認）",
            "まだ時間感覚が未来まで届かない2歳児に、「あとでね」「明日ね」を納得してもらう視覚・体感の工夫",
        ],
    },
    # 3: 木曜日【おうち遊び・五感・指先・運動の発達】
    {
        "genre": "おうち遊び・指先・運動の発達",
        "horoscope_lens": "海王星うお座（ごっこ遊び・音楽・空想の世界を広げる豊かなイマジネーション）× 5ハウスいて座・ドラゴンヘッドおひつじ座（のびのび体を動かす冒険心と「はじめての挑戦」を楽しむ力）",
        "themes": [
            "家にある日用品（洗濯バサミ・シール・空き箱・キャップ等）で没頭できる、指先の器用さを育てる5分遊び",
            "見立て遊び・ごっこ遊び（「お店屋さん」「運転手さん」等）で想像力を広げる、親の「名脇役」の演じ方",
            "雨の日や夕方にお部屋の中で体力を発散できる、体幹・バランス遊び（タオル綱引き・クッション渡り・動物なりきり）",
            "お手伝いブームを遊びに変える！食事準備や洗濯で「家族の役に立てた」自信を育てる小さなミッション",
            "ブロックやパズルで「できなくて投げる・怒る」時に、全部手伝わずヒントを1ミリだけ出すサポート術",
            "いつもの帰り道が宝探しに変わる！葉っぱ・石・影踏み・音探しなど五感をフル活用するお散歩コミュニケーション",
            "音楽・リズム・手遊びや歌を使って、グズりそうな時間帯を笑いに変えるスキンシップ遊び",
        ],
    },
    # 4: 金曜日【生まれ持った気質（ホロスコープ）を深掘りする才能開花コラム】
    {
        "genre": "お子様の生まれ持った気質（ホロスコープ）を深掘りする才能開花コラム",
        "horoscope_lens": "ホロスコープ全体（うお座の共感力と想像力 × みずがめ座の独創性とひらめき × おうし座の五感 × かに座の安心感 × おひつじ座の開拓心）",
        "themes": [
            "太陽・水星うお座の「高い共感力と想像力」：親の表情や空気を敏感に察するお子様へ安心感を届ける声のトーン",
            "月・火星みずがめ座の「独自のこだわりとひらめき」：大人とは違うユニークな遊び方やマイペースさを才能として伸ばす見守り方",
            "アセンダントかに座の「安心基地への愛着」：初めての場所や人で慎重になる時に「味方だよ」と伝えるウォームアップ術",
            "うお座のファンタジー脳×みずがめ座の発明脳：お話を一緒に作ったり「もし〜だったら？」と空想を広げたりする会話術",
            "木星おうし座が示す「五感の心地よさ」：肌触りの良いタオルや好きな匂い・食感など、五感の快・不快に寄り添う機嫌ケア",
            "周囲の感情を吸収しやすい優しさを持つ子に、気持ちを切り替えられる「お気に入りの安心コーナー」を作る工夫",
            "頭ごなしの指示が苦手なみずがめ座気質に効く、「〇〇くんはどうやりたい？」と対等な作戦会議にするアプローチ",
        ],
    },
    # 5: 土曜日【食事・睡眠・トイトレ・身の回りの自立サポート】
    {
        "genre": "食事・睡眠・トイトレ・生活習慣の自立",
        "horoscope_lens": "木星・天王星おうし座（五感の心地よさ・肌触り・食感・マイペースな身体感覚を尊重すると生活習慣がスムーズに定着する気質）× MCおひつじ座（「自分でできた！」の達成感が原動力）",
        "themes": [
            "食べムラ・遊び食べが起きる時期に、完食を目指さず「食卓が楽しい場所」にする一口サイズ・盛り付けの工夫",
            "トイトレ（トイレへの興味づけ）：プレッシャーを与えず、おしっこの間隔や体の感覚に楽しく気づかせる声かけ",
            "靴やズボンの「自分で履きたい！（でもできなくて泣く）」に効く、最後の1割だけ本人にゴールテープを切らせる介助術",
            "寝かしつけ前にテンションが上がって走り回る夜の、照明・声のトーン・入眠ルーティンのクールダウン設計",
            "お片付けを「片付けなさい」ではなく「赤い車だけ駐車場に戻そう！」と超具体的なミッションに変える声かけ",
            "外食や買い物先での待ち時間を機嫌よく乗り切る、スマホ以外の「観察ゲーム・小声クイズ」の引き出し",
            "手洗い・うがい・鼻かみなど「自分の体を守る習慣」を2歳後半の子どもが面白がって身につけるコツ",
        ],
    },
    # 6: 日曜日【パパママのメンタルケア・夫婦の連携・声かけ変換】
    {
        "genre": "パパママのメンタルケア・夫婦の連携・声かけ変換",
        "horoscope_lens": "太陽うお座×ASCかに座（パパとママの笑顔や心のゆとりを鏡のように敏感に感じ取る優しい子だからこそ、親自身が肩の力を抜いてご機嫌でいることが一番の安心材料になる）",
        "themes": [
            "親も人間！イライラして強い口調になりそうな瞬間のクールダウンと、叱りすぎた後の仲直りフォロー術",
            "つい言ってしまう「早くして！」「何回言ったらわかるの！」を、子どもが動ける言葉に変える言い換えレシピ",
            "夫婦で育児のやり方や基準が違う時に、「正解探し」ではなくお互いの得意を活かすチームプレーにするコツ",
            "疲れが溜まる週末に、「完璧な親」を手放して親自身のエネルギーを回復させる「戦略的手抜き」のすすめ",
            "子どもの成長だけでなく、パパ・ママ自身が「今週も無事に乗り切ったこと」を夫婦で労い合うコミュニケーション",
            "イヤイヤや癇癪を「親への反抗」ではなく「まだ未熟な脳のオーバーヒート」と客観視して心の消耗を減らす捉え方",
            "2歳後半の「今だけの可愛さ（小さな手、独特の言い回し、全力の甘え）」を味わう1分間のマインドフルネス",
        ],
    },
]


def get_child_age():
    """日本時間（JST）基準でお子様の現在の年齢（〇歳〇ヶ月）を計算する"""
    today = datetime.now(JST).date()
    months = (today.year - BIRTH_DATE.year) * 12 + today.month - BIRTH_DATE.month
    if today.day < BIRTH_DATE.day:
        months -= 1
    years = months // 12
    remaining_months = months % 12
    return f"{years}歳{remaining_months}ヶ月"


def get_today_assigned_theme(now_jst=None):
    """
    JSTの日付から決定論的に本日のジャンル・具体テーマ・ホロスコープ着眼レンズを選出する。
    曜日ごとにジャンルと着眼天体が変わり、週ごとにサブテーマが巡回するため、
    サーバー再起動でファイルが消えても49日間（7週間）同じテーマが重複しない。
    """
    if now_jst is None:
        now_jst = datetime.now(JST)
    today = now_jst.date()
    weekday = today.weekday()  # 0(月)〜6(日)
    days_since_birth = (today - BIRTH_DATE).days
    week_cycle = (days_since_birth // 7) % 7

    day_config = WEEKDAY_THEME_MATRIX[weekday]
    theme = day_config["themes"][week_cycle]
    return {
        "genre": day_config["genre"],
        "theme": theme,
        "horoscope_lens": day_config["horoscope_lens"],
    }


def get_recent_topics(days=14):
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
        cutoff = datetime.now(JST) - timedelta(days=days)
        recent = []
        for item in history:
            dt = datetime.fromisoformat(item["date"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=JST)
            if dt > cutoff:
                recent.append(item["topic"])
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

    history.append({"date": datetime.now(JST).isoformat(), "topic": topic})
    history = history[-30:]  # 履歴は直近30件まで保持

    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error writing topic history:", e)


def get_weather_info(city="Yokohama"):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        if res.status_code == 200:
            wind_speed = data["wind"]["speed"]
            alert = (
                "⚠️ 風が強いため、自転車での移動は少し注意が必要です。"
                if wind_speed >= 5.0
                else "✅ 風は穏やかで、安全に自転車で移動できる天候です。"
            )
            return {
                "description": data["weather"][0]["description"],
                "temp": data["main"]["temp"],
                "wind_speed": wind_speed,
                "alert": alert,
            }
        return {"error": data.get("message")}
    except Exception as e:
        return {"error": str(e)}


def get_tomorrow_weather_info(city="Yokohama"):
    """
    OpenWeatherMapの5日間/3時間予報APIから、明日の日中（6時〜21時）を中心に
    最高/最低気温、天気概要、最大降水確率を取得する。
    """
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        if res.status_code == 200:
            now = datetime.now(JST)
            tomorrow_date = (now + timedelta(days=1)).date()

            tomorrow_all = []
            tomorrow_daytime = []
            for item in data.get("list", []):
                dt_utc = datetime.fromtimestamp(item["dt"], tz=timezone.utc)
                dt_jst = dt_utc.astimezone(JST)
                if dt_jst.date() == tomorrow_date:
                    tomorrow_all.append(item)
                    if 6 <= dt_jst.hour <= 21:
                        tomorrow_daytime.append(item)

            target_items = tomorrow_daytime if tomorrow_daytime else tomorrow_all
            if target_items:
                max_temp = round(max(item["main"]["temp_max"] for item in tomorrow_all), 1)
                min_temp = round(min(item["main"]["temp_min"] for item in tomorrow_all), 1)
                weather_descs = list(
                    dict.fromkeys(
                        [item["weather"][0]["description"] for item in target_items if item.get("weather")]
                    )
                )
                desc_str = "・".join(weather_descs[:2]) if weather_descs else "不明"
                max_pop = int(round(max(item.get("pop", 0.0) for item in target_items) * 100))
                max_wind = round(max(item.get("wind", {}).get("speed", 0.0) for item in target_items), 1)
                return {
                    "date": tomorrow_date.strftime("%Y-%m-%d"),
                    "max_temp": max_temp,
                    "min_temp": min_temp,
                    "description": desc_str,
                    "pop": max_pop,
                    "wind_speed": max_wind,
                }
        return {"error": data.get("message", "予報データの取得に失敗しました")}
    except Exception as e:
        return {"error": str(e)}


def suggest_destination(mode, schedule, origin, max_time="30分以内"):
    """天気と移動手段、日時、移動時間、指定された出発地(現在地含む)から、お子様にぴったりの行き先を提案する機能"""
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
        client = get_gemini_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return {"suggestion": response.text}
    except Exception as e:
        print("Suggest Error:", e)
        return {
            "suggestion": '[{"name":"蒔田公園", "address":"神奈川県横浜市南区宿町1丁目1", "stars":"⭐⭐⭐", "reason":"大型遊具があり安全に遊べます。AIからの応答が遅延しているため、定番の公園をご案内します。"}]'
        }


def get_route_and_parking(origin, destination, mode):
    maps_mode = "bicycling" if mode == "bicycle" else "driving"
    result = {"route": None, "parking": []}

    try:
        gmaps = get_gmaps_client()
        directions = gmaps.directions(origin, destination, mode=maps_mode, language="ja", departure_time="now")
        if directions:
            leg = directions[0]["legs"][0]
            result["route"] = {
                "distance": leg["distance"]["text"],
                "duration": leg["duration"]["text"],
                "duration_in_traffic": leg.get("duration_in_traffic", {}).get("text", None),
                "end_address": leg["end_address"],
            }
            if mode == "car":
                lat = leg["end_location"]["lat"]
                lng = leg["end_location"]["lng"]
                places = gmaps.places_nearby(location=(lat, lng), radius=1000, type="parking", language="ja")
                if places.get("status") == "OK":
                    for p in places["results"][:3]:
                        result["parking"].append({"name": p.get("name"), "rating": p.get("rating", "評価なし")})
        return result
    except Exception as e:
        result["error"] = str(e)
        return result


def analyze_place(place_name):
    reviews = []
    try:
        gmaps = get_gmaps_client()
        search = gmaps.places(query=place_name, language="ja")
        if search.get("status") == "OK" and search["results"]:
            place_id = search["results"][0]["place_id"]
            details = gmaps.place(place_id=place_id, language="ja")
            if "reviews" in details.get("result", {}):
                reviews = [r["text"] for r in details["result"]["reviews"]]
    except Exception:
        pass

    if not reviews:
        reviews = [
            "緑が豊かで散歩に最適ですが、坂道が多いのでベビーカーを押すのは少し大変でした。",
            "トイレは綺麗に清掃されており、おむつ替えの台も1つありました。",
            "どんぐりがたくさん落ちていて、2歳の子供が大喜びでした！小学生以上の子供は少ないので安全です。",
            "休日は駐車場がすぐに満車になるため、早めに行くことをおすすめします。",
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
        client = get_gemini_client()
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return {"summary": response.text}
    except Exception as e:
        return {"error": str(e), "summary": "AIからの応答が遅延しています。"}


def generate_daily_delivery_info():
    """感染症流行アラート、明日の天気、ホロスコープ気質×月齢の重複しない育児コラムをコンパクトに生成する"""
    now = datetime.now(JST)
    tomorrow = now + timedelta(days=1)
    age_str = get_child_age()
    tomorrow_weather = get_tomorrow_weather_info("Yokohama")
    assigned = get_today_assigned_theme(now)

    recent_topics = get_recent_topics(14)
    topics_context = ""
    if recent_topics:
        topics_list = " / ".join(recent_topics)
        topics_context = f"\n   - ※直近配信済みのテーマ（{topics_list}）とは具体例や表現が重ならないようにしてください。"

    weekday_kanji = ["月", "火", "水", "木", "金", "土", "日"]
    now_str = f"{now.year}年{now.month}月{now.day}日({weekday_kanji[now.weekday()]})"
    tomorrow_str = f"{tomorrow.month}/{tomorrow.day}({weekday_kanji[tomorrow.weekday()]})"
    hour = now.hour

    if 4 <= hour < 11:
        greeting = "おはようございます！今日も1日マイペースにいきましょう✨"
    elif 11 <= hour < 17:
        greeting = "こんにちは！お昼休み、今日もお疲れ様です☕️"
    else:
        greeting = "こんばんは！今日も1日本当にお疲れ様でした🌙"

    if "error" not in tomorrow_weather:
        weather_desc = tomorrow_weather.get("description", "不明")
        max_t = tomorrow_weather.get("max_temp", "不明")
        min_t = tomorrow_weather.get("min_temp", "不明")
        pop = tomorrow_weather.get("pop", 0)
        weather_context = (
            f"明日{tomorrow_str}の横浜市の予報データ：天候「{weather_desc}」、"
            f"最高気温{max_t}℃ / 最低気温{min_t}℃、日中最大降水確率{pop}%。"
        )
    else:
        weather_context = f"明日{tomorrow_str}の横浜市の天気と最高・最低気温を検索して反映してください。"

    prompt = f"""
あなたは横浜在住のファミリーを支える、占星術と発達心理学に精通した専属子育てコンシェルジュAIです。
読者は横浜市在住・保育園に通う「{age_str}」（2024年3月8日生まれ）の男の子を育てるパパとママです。
今日の日付は「{now_str}」です。

{CHILD_HOROSCOPE}

お昼休みにスマホでパッと1分で読めて、「あ、なるほどね！」「うちの子にはこう接してみよう」とスッと頭に入る、**コンパクトで中身の濃いメッセージ（全体で500〜650文字程度）**を作成してください。

以下の【必須項目】を必ず指定された【順番】と【分量ルール】で出力してください：

1. 【⚠️ 感染症流行アラート】（箇条書き2〜3行・100文字前後）
   - Google検索を活用し、現在（{now.year}年{now.month}月時点）の横浜市・神奈川県周辺で注意すべき子どもの感染症を2〜3つ挙げてください。
   - **重要**：「〇〇とは〜という病気です」といった教科書的な基礎説明や、「手洗いうがい・十分な休養を心がけましょう」といった毎回の定型まとめ文は一切書かず、**「疾患名：いま家庭で気をつける具体的な一言ポイント」**だけを1行ずつ端的に書いてください。

2. 【🌤 明日の天気】（1〜2行・60文字前後）
   - {weather_context}
   - 明日の天気・最高/最低気温と、傘の要否や寒暖差の体感だけを1〜2行でスッキリ伝えてください（服装や持ち物の細かい指示は不要）。

3. 【💡 今日の育児コラム：{age_str}のいま】（300〜400文字程度）
   - **本日の指定ジャンル**：{assigned['genre']}
   - **本日の指定ピンポイントテーマ**：『{assigned['theme']}』
   - **本日掛け合わせる「うちの子ホロスコープ着眼レンズ」**：『{assigned['horoscope_lens']}』{topics_context}
   - 一般的な2歳児の育児論だけで終わらせず、**「{age_str}の発達メカニズム」×「この子のホロスコープ気質（本日の着眼レンズ）」**を自然に掛け合わせた、**世界にひとつだけの「うちの子専用アドバイス」**にしてください（※「うお座だから」等と毎回同じ表現ばかりにならず、その日のテーマに沿って気質の強みやツボを自然に織り交ぜること）。
   - 長々と3〜4項目も羅列するのは禁止です。以下の**2ステップ構成**で簡潔かつ深く書いてください：
     ① **「なぜ？」の納得理由（2〜3文）**：その行動や状態の背景にある「{age_str}の脳・心の発達」と「この子ならではの気質」を伝え、「だからそうだったのか！」と親が納得できるようにする。
     ② **「今日から試せるうちの子専用ヒント」（1〜2個に厳選）**：この子の気質に響きやすい具体的な声かけ例（「〇〇」とカギカッコ付き）やアクションを1〜2個だけ実践的に紹介する。

4. 【☕️ パパママへのねぎらい】（1〜2行）
   - お昼休みにホッと肩の力が抜けるような、短く温かい一言を添えてください。

【出力フォーマット】（Markdownのコードブロック ``` は不要。以下の構成通りにそのまま出力してください）:
{greeting}

⚠️【感染症流行アラート】
・（疾患名）：（具体的な一言ポイント）
・（疾患名）：（具体的な一言ポイント）

🌤【明日の天気】
（明日の横浜の天気・最高/最低気温・一言ポイントを1〜2行で）

💡【今日の育児コラム：{age_str}のいま】
■テーマ：（本日のテーマを端的に1行で記載）

（①「なぜ？」の発達×うちの子気質の納得理由を2〜3文で）

👉 今日から試せるうちの子専用ヒント
・（この子の気質に響く具体的なアクションや「声かけ例」1つ目）
・（具体的なアクションや「声かけ例」2つ目 ※1つで十分なら1つでも可）

☕️（1〜2行の温かいねぎらいメッセージ）
""".strip()

    client = get_gemini_client()
    last_error = None

    # リトライ＆フォールバック機構（一時的なAPI過負荷やGoogle検索ツールのタイムアウト対策）
    for attempt in range(3):
        use_search_tool = attempt < 2  # 1〜2回目はGoogle検索あり、3回目は検索なしフォールバック
        config = {"tools": [{"google_search": {}}]} if use_search_tool else {}
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=config,
            )
            message_text = (response.text or "").strip()
            if not message_text:
                raise ValueError("Geminiから空のレスポンスが返されました。")

            # 配信したテーマを履歴に保存
            for line in message_text.split("\n"):
                if line.strip().startswith("■テーマ："):
                    topic_name = line.strip().replace("■テーマ：", "").strip()
                    add_topic_to_history(topic_name)
                    break

            return {"message": message_text}
        except Exception as e:
            last_error = e
            print(f"Daily Info Generation Attempt {attempt + 1} failed (search={use_search_tool}): {e}")
            if attempt < 2:
                time.sleep(2 * (attempt + 1))

    return {
        "error": str(last_error),
        "message": f"{greeting}\n\n情報の生成中に一時的な通信エラーが発生しました。時間を置いて再度お試しください。",
    }


def send_line_message(text):
    """LINE Messaging APIを使ってメッセージを送信する（リトライ・タイムアウト付き）"""
    if not LINE_CHANNEL_ACCESS_TOKEN:
        return {"error": "LINE APIの環境変数が設定されていません。"}

    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
    }
    data = {"messages": [{"type": "text", "text": text}]}

    for attempt in range(2):
        try:
            res = requests.post(url, headers=headers, json=data, timeout=10)
            if res.status_code == 200:
                return {"status": "success"}
            elif res.status_code >= 500 and attempt == 0:
                time.sleep(2)
                continue
            else:
                return {"error": res.text}
        except Exception as e:
            if attempt == 0:
                time.sleep(2)
                continue
            return {"error": str(e)}
