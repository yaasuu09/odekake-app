import os
import requests
from dotenv import load_dotenv

# .envファイルからAPIキーを読み込む
load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")

def test_weather():
    print("--- OpenWeather API テスト開始 ---\n")
    if not API_KEY or API_KEY == "ここにOpenWeatherのAPIキーを貼り付けてください":
        print("エラー: OpenWeatherのAPIキーが正しく設定されていません。")
        return

    # 横浜市の天気を取得するAPI URL
    city = "Yokohama"
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric&lang=ja"

    print("👉 [テスト: 現在の横浜市の天気・風速の取得]")
    try:
        response = requests.get(url)
        data = response.json()
        
        if response.status_code == 200:
            weather_desc = data['weather'][0]['description']
            temp = data['main']['temp']
            wind_speed = data['wind']['speed'] # m/s
            print(f"   🌤️ 天気: {weather_desc}")
            print(f"   🌡️ 気温: {temp} ℃")
            print(f"   💨 風速: {wind_speed} m/s\n")
            
            # 2歳児向け自転車移動のアラートロジック（簡易版）
            if wind_speed >= 5.0:
                print("   ⚠️ アラート: 風が強いため、自転車での移動は少し注意が必要です。")
            else:
                print("   ✅ 風は穏やかで、自転車での移動も概ね問題ありません。")
                
        else:
            print(f"❌ エラーコード {response.status_code}: {data.get('message')}")
            
    except Exception as e:
        print(f"❌ 通信エラーが発生しました: {e}")

    print("\n--- テスト完了！ ---\n")

if __name__ == "__main__":
    test_weather()
