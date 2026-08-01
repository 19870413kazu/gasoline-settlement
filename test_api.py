import os
import requests
from dotenv import load_dotenv

# .env から APIキーを読み込み
load_dotenv()
api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")

print(f"APIキー: {api_key[:20]}..." if api_key else "APIキーが見つかりません")

# テスト座標（東京）
lat, lng = "35.642955", "139.711953"

url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&language=ja&key={api_key}"

try:
    resp = requests.get(url, timeout=4)
    data = resp.json()
    print(f"ステータス: {data.get('status')}")
    if data.get("results"):
        addr = data["results"][0]["formatted_address"]
        print(f"住所: {addr}")
    else:
        print(f"エラー: {data}")
except Exception as e:
    print(f"例外: {e}")
