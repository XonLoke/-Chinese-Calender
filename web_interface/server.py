"""万年历引擎 — Web 测试接口服务器

用法:
    cd D:\c_wannianli
    python web_interface/server.py

然后打开 http://localhost:8765
"""

import json
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class CalendarHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器。"""

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            self._serve_static("web_interface/index.html", "text/html; charset=utf-8")
        elif path == "/api/calendar":
            self._handle_calendar_api(parse_qs(parsed.query))
        elif path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            self.send_error(404, "Not Found")

    def _serve_static(self, filepath: str, content_type: str):
        """提供静态文件。"""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(root, filepath)
        if not os.path.exists(full_path):
            self.send_error(404, f"File not found: {filepath}")
            return
        with open(full_path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _handle_calendar_api(self, params: dict):
        """处理日历查询 API。"""
        import sys, traceback
        try:
            year = int(params.get("year", [2026])[0])
            month = int(params.get("month", [5])[0])
            day = int(params.get("day", [21])[0])
            hours = float(params.get("hours", [12.0])[0])
            locale = params.get("locale", ["zh"])[0]

            print(f"  API请求: {year}-{month:02d}-{day:02d} {hours}h [{locale}]")

            from chinese_calendar.api import Calendar

            cal = Calendar.from_solar(year, month, day, hours=hours, locale=locale)
            print(f"  八字: {cal.bazi_str}")
            result = cal.to_dict()
            print(f"  to_dict: OK")

            # 补充节气数据
            try:
                result["solar_terms"] = cal.solar_terms
            except Exception as e:
                print(f"  solar_terms error: {e}")
                result["solar_terms"] = []
            result["bazi_str"] = cal.bazi_str
            result["lunar_str"] = cal.lunar_str if cal.lunar else ""
            result["shengxiao_zh"] = cal.shengxiao.zh
            result["shengxiao_en"] = cal.shengxiao.en
            result["weekday"] = cal.weekday.zh
            result["weekday_en"] = cal.weekday.en

            # 术数文化层
            try:
                from chinese_calendar.api.lunar_culture import get_lunar_culture
                culture = get_lunar_culture(year, month, day)
                if culture:
                    result["culture"] = culture
                    print(f"  culture: {culture.get('xiu', '')}")
            except Exception as e:
                print(f"  culture error: {e}")

            print(f"  发送响应...")
            self._send_json(result)
            print(f"  响应完成")

        except ImportError as e:
            print(f"  ImportError: {e}")
            traceback.print_exc()
            self._send_json({"error": str(e)}, status=500)
        except Exception as e:
            print(f"  Exception: {e}")
            traceback.print_exc()
            self._send_json({"error": str(e)}, status=500)

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

    def log_message(self, format, *args):
        if len(args) >= 3:
            print(f"[{self.address_string()}] {args[0]} {args[1]} {args[2]}")
        elif args:
            print(f"[{self.address_string()}] {' '.join(str(a) for a in args)}")
        else:
            print(f"[{self.address_string()}] {format}")


def main():
    port = 8765
    server = HTTPServer(("0.0.0.0", port), CalendarHandler)
    print(f"万年历引擎 — 测试服务器")
    print(f"  http://localhost:{port}")
    print(f"  Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止.")
        server.server_close()


if __name__ == "__main__":
    main()
