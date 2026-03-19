import os
import googlemaps
from dotenv import load_dotenv

# .envファイルからAPIキーを読み込む
load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

def test_google_maps():
    print("--- Google Maps API テスト開始 ---\n")
    if not API_KEY or API_KEY == "ここにGoogleのAPIキーを貼り付けてください":
        print("エラー: Google MapsのAPIキーが正しく設定されていません。")
        return

    # Google Maps クライアントの初期化
    gmaps = googlemaps.Client(key=API_KEY)

    # 【テスト1】Geocoding API: 指定した地名の緯度経度を取得
    print("👉 [テスト1: 緯度・経度の取得]")
    origin = "横浜市南区清水ヶ丘"
    geocode_result = gmaps.geocode(origin)
    if geocode_result:
        location = geocode_result[0]['geometry']['location']
        lat, lng = location['lat'], location['lng']
        print(f"✅ '{origin}' の座標: 緯度 {lat}, 経度 {lng}\n")
    else:
        print("❌ 場所が見つかりませんでした。\n")
        return

    # 【テスト2】Places API: 指定した場所の周辺の駐車場を検索
    print("👉 [テスト2: 周辺の駐車場を検索]")
    places_result = gmaps.places_nearby(location=(lat, lng), radius=1000, type="parking", language="ja")
    if places_result.get('status') == 'OK':
        for i, place in enumerate(places_result['results'][:3], 1): # 上位3件を表示
            print(f"   🚗 駐車場候補{i}: {place.get('name')} (評価: {place.get('rating', 'なし')})")
        print("✅ 駐車場情報を取得しました。\n")
    else:
        print(f"❌ 駐車場の検索に失敗しました。(ステータス: {places_result.get('status')})\n")

    # 【テスト3】Directions API: クルマでのルートと所要時間の取得 (出発時間を`now`にして渋滞情報も加味)
    print("👉 [テスト3: クルマでのルート検索]")
    destination = "横浜市 こども植物園" # 近くの家族向けお出かけスポットを仮設定
    try:
        directions_result = gmaps.directions(
            origin,
            destination,
            mode="driving",
            language="ja",
            departure_time="now" # リアルタイム渋滞情報のため
        )
        
        if directions_result:
            route = directions_result[0]['legs'][0]
            print(f"   📍 目的地: {route['end_address']}")
            print(f"   ⏱️ 所要時間: {route['duration']['text']}")
            if 'duration_in_traffic' in route:
                print(f"   🚦 渋滞考慮の所要時間: {route['duration_in_traffic']['text']}")
            print(f"   📏 距離: {route['distance']['text']}")
            print("✅ ルート検索に成功しました。\n")
        else:
            print("❌ ルートが見つかりませんでした。\n")
    except Exception as e:
        print(f"❌ ルート検索でエラーが発生しました: {e}\n")

    print("--- テスト完了！ ---")

if __name__ == "__main__":
    test_google_maps()
