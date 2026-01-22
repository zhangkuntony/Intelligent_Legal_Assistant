# backend/test_time_sync.py
import requests
from datetime import datetime
import pytz


def check_time_sync():
    """检查时间同步"""
    print("=== 时间同步检查 ===")

    # 本地时间
    local_now = datetime.now(pytz.timezone('Asia/Shanghai'))
    print(f"本地时间: {local_now}")
    print(f"本地时间戳: {local_now.timestamp()}")

    # 通过 HTTP 请求 MinIO 服务器时间
    try:
        response = requests.get('http://localhost:9000/minio/health/live')
        server_date = response.headers.get('Date')
        if server_date:
            print(f"服务器时间 (HTTP Header): {server_date}")

        # 解析服务器时间
        if server_date:
            from email.utils import parsedate_to_datetime
            server_time = parsedate_to_datetime(server_date)
            print(f"服务器时间 (解析后): {server_time}")
            print(f"服务器时间戳: {server_time.timestamp()}")

            # 计算时间差
            time_diff = abs(local_now.timestamp() - server_time.timestamp())
            print(f"\n时间差: {time_diff:.2f} 秒")

            if time_diff < 60:
                print("✓ 时间同步正常")
            elif time_diff < 900:  # 15分钟
                print("⚠ 时间差异较大，但可接受")
            else:
                print("✗ 时间差异过大，需要同步！")

    except Exception as e:
        print(f"无法获取服务器时间: {e}")


if __name__ == "__main__":
    check_time_sync()
