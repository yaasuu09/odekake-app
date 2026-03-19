import os
import googlemaps
from google import genai
from dotenv import load_dotenv

# APIキーの読み込み
load_dotenv()
MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def test_integration():
    print("--- 【Step 2】Places API + Gemini API連携テスト ---\n")

    gmaps = googlemaps.Client(key=MAPS_API_KEY)
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)

    # ==========================================
    # 1. Places APIで施設の口コミ取得
    # ==========================================
    print("👉 [ステップ1: Places APIから実際の施設の口コミを取得]")
    # 横浜市の「こども植物園」でテスト
    target_place = "横浜市 こども植物園"
    reviews = []
    
    try:
        # まずテキスト検索でPlace ID（施設の固有ID）を取得
        search_result = gmaps.places(query=target_place, language="ja")
        if search_result.get('status') == 'OK' and search_result['results']:
            place_id = search_result['results'][0]['place_id']
            place_name = search_result['results'][0]['name']
            
            # Place Detailsを取得して最新の口コミ(reviews)を取り出す
            details = gmaps.place(place_id=place_id, language="ja")
            if 'reviews' in details.get('result', {}):
                for review in details['result']['reviews']:
                    reviews.append(review['text'])
                print(f"✅ Google Mapsから '{place_name}' の口コミを {len(reviews)}件 取得しました！")
            else:
                print(f"❌ '{place_name}' の口コミデータがありませんでした。")
        else:
            print("❌ 施設の検索に失敗しました。")
    except Exception as e:
        print(f"⚠️ Places API情報の取得でエラー発生（APIキー反映待ちの可能性が高いです）: {e}")

    # もし口コミが取得できなかった場合（APIキー反映待ち等）は、ダミーデータでテストを続行
    if not reviews:
        print("\n⚠️ 実際の口コミが取得できなかったため、ダミーの口コミデータを使用して連携テストを続行します。")
        reviews = [
            "緑が豊かで散歩に最適ですが、坂道が多いのでベビーカーを押すのは少し大変でした。",
            "トイレは綺麗に清掃されており、おむつ替えの台も1つありました。",
            "どんぐりがたくさん落ちていて、2歳の子供が大喜びでした！小学生以上の子供は少ないので安全です。",
            "休日は駐車場がすぐに満車になるため、午前中の早めに行くことをおすすめします。"
        ]

    # ==========================================
    # 2. Gemini API で分析
    # ==========================================
    print("\n👉 [ステップ2: 取得した口コミリストを全てGeminiに渡して要約]")
    
    # 取得した口コミリストを1つの文字列に結合する（バケツリレー）
    reviews_text = ""
    for i, r in enumerate(reviews, 1):
        reviews_text += f"口コミ{i}:\n{r}\n\n"

    # AIへの指示書
    prompt = f"""
    あなたは優秀な子育て支援AIです。
    以下の公園（施設）の実際の口コミを統合して、2歳の子供を連れた親の視点で【良い点】と【注意点】を分かりやすく要約・箇条書きしてください。
    
    【絶対に分析してほしいポイント】
    1. おむつ替え/授乳スペースの有無と使いやすさ
    2. 2歳児が安全に楽しめるか
    3. 混雑状況とベビーカーでの移動しやすさ
    
    【実際の口コミデータ】
    {reviews_text}
    """

    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        print("✅ AIからの連携分析結果（要約）:\n")
        print("="*40)
        print(response.text)
        print("="*40)
        print("\n🎉 API同士のバケツリレー（連携）が正常に完了しました！")
    except Exception as e:
        print(f"❌ Gemini APIエラーが発生しました: {e}")

if __name__ == "__main__":
    test_integration()
