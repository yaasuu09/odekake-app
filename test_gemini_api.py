import os
from google import genai
from dotenv import load_dotenv

# .envファイルからAPIキーを読み込む
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

def test_gemini():
    print("--- Gemini API テスト開始 ---\n")
    if not API_KEY or API_KEY == "ここにGeminiのAPIキーを貼り付けてください":
        print("エラー: GeminiのAPIキーが正しく設定されていません。")
        return

    # Gemini クライアントの初期化
    client = genai.Client(api_key=API_KEY)

    # Places APIから取得したと仮定する「ダミーの口コミデータ」
    sample_reviews = """
    ・遊具がたくさんあって子供が楽しそうでした！ただ、休日は小学生が多くて走り回っているので少し危ないかも。
    ・おむつ替えシートがあるトイレは入口の1箇所だけで、少し遠かったです。
    ・ベビーカーで移動しやすい舗装されたフラットな道が多かったです。
    ・駐車場が狭く、休日はすぐ満車になります。
    """

    # Geminiに依頼するプロンプト（指示書）
    prompt = f"""
    あなたは優秀な子育て支援AIです。
    以下の公園の口コミを、2歳の子供を連れた親の視点で分析・要約してください。
    
    【絶対に分析してほしいポイント】
    1. おむつ替え/授乳スペースの有無と使いやすさ
    2. 2歳児が安全に楽しめるか（小学生以上向けで危なくないか）
    3. 混雑状況とベビーカーでの移動しやすさ
    
    【口コミデータ】
    {sample_reviews}
    """

    print("👉 [テスト: 2歳児パパママ視点での口コミ分析]")
    try:
        # gemini-2.5-flash などの高速・高性能モデルを利用
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        print("✅ AIからの要約回答:\n")
        print("="*40)
        print(response.text)
        print("="*40)
        print("\n✅ 分析が正常に完了しました！")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

    print("\n--- テスト完了！ ---\n")

if __name__ == "__main__":
    test_gemini()
