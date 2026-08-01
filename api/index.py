import json
import os
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
import requests
from dotenv import load_dotenv

# .env ファイルを読み込む
load_dotenv()

app = FastAPI()

https://vercel.com/19870413kazu-projects/gasoline-settlement-v95/settings/environment-variablesGOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
DEFAULT_PRICE_PER_KM = float(os.environ.get("DEFAULT_PRICE_PER_KM", 15))

address_cache = {}


def get_address(geo_str: str) -> str:
    if not geo_str or not geo_str.startswith("geo:"):
        return "住所不明"
    coords = geo_str.replace("geo:", "").split(",")
    if len(coords) < 2:
        return "住所不明"

    lat, lng = coords[0].strip(), coords[1].strip()
    cache_key = f"{lat},{lng}"
    if cache_key in address_cache:
        return address_cache[cache_key]

    if not GOOGLE_MAPS_API_KEY:
        print(f"⚠️ APIキーなし")
        return f"{lat}, {lng}"

    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&language=ja&key={GOOGLE_MAPS_API_KEY}"
        print(f"🔄 APIを呼び出す: {lat}, {lng}")
        resp = requests.get(url, timeout=4)
        data = resp.json()
        print(f"✅ ステータス: {data.get('status')}")
        if data.get("status") == "OK" and data.get("results"):
            addr = data["results"][0]["formatted_address"].replace("日本、", "")
            address_cache[cache_key] = addr
            print(f"✅ アドレス取得: {addr[:50]}...")
            return addr
        else:
            print(f"❌ API エラー: {data.get('error_message', 'No error message')}")
    except Exception as e:
        print(f"❌ 例外: {e}")
    return f"{lat}, {lng}"


@app.post("/api/parse-timeline")
async def parse_timeline(file: UploadFile = File(...)):
    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))

        parsed_activities = []
        geo_to_fetch = set()

        for item in data:
            if "activity" in item:
                act = item["activity"]
                top = act.get("topCandidate", {})
                act_type = top.get("type", "不明")

                if act_type == "in passenger vehicle":
                    act_type_ja = "自動車"
                elif act_type == "walking":
                    act_type_ja = "徒歩"
                elif act_type == "in train":
                    act_type_ja = "電車"
                else:
                    act_type_ja = act_type

                start_geo = act.get("start", "")
                end_geo = act.get("end", "")
                distance_m = round(float(act.get("distanceMeters", 0)))

                if start_geo:
                    geo_to_fetch.add(start_geo)
                if end_geo:
                    geo_to_fetch.add(end_geo)

                start_time = item.get("startTime", "")
                date_part = (
                    start_time[:10].replace("-", "/")
                    if len(start_time) >= 10
                    else ""
                )
                time_part = (
                    start_time[11:16] if len(start_time) >= 16 else ""
                )

                parsed_activities.append(
                    {
                        "date": date_part,
                        "time": time_part,
                        "type": act_type_ja,
                        "isVehicle": (act_type_ja == "自動車"),
                        "distanceMeters": distance_m,
                        "distanceKm": round(distance_m / 1000.0, 2),
                        "startGeo": start_geo,
                        "endGeo": end_geo,
                    }
                )

        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(get_address, list(geo_to_fetch))

        for act in parsed_activities:
            act["startAddress"] = get_address(act["startGeo"])
            act["endAddress"] = get_address(act["endGeo"])

        return JSONResponse(
            {
                "success": True,
                "activities": parsed_activities,
                "pricePerKm": DEFAULT_PRICE_PER_KM,
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"解析エラー: {str(e)}"
        )
