# Copyright 2026 Sony Global Manufacturing & Operations Corporation

import statistics
import struct
import sys
import threading
import time
from typing import List, Optional
from ZeroMQClient import ZeroMQClient

# ==== 設定 ====
SUB_ADDRESS:  str = "tcp://localhost:55555"
PUSH_ADDRESS: str = "tcp://localhost:55556"

# ==== グローバル ====
running: bool = True
client: Optional[ZeroMQClient] = None

# Host 集計用
host_lock: threading.Lock = threading.Lock()
host_last_receive_time: float = 0
host_last_serial_number: int | None = None
host_last_data_type: int | None = None
host_total_max_value: int | None = None
host_total_min_value: int | None = None
host_median_list: List[float] = []

# ====================================================
#  各トピックの処理関数（カスタム部分）
# ====================================================
def handle_host_topic(payload: bytes) -> None:
    """
    Host トピック:
      データ形式（バイトオーダーはすべてリトルエンディアン）
      (1) 共通部
        [0:3]   バイト: シリアル番号（10ミリ秒ごとに +1 ずつ増加, 符号なし16ビット整数）
        [4:5]   バイト: データ種別
                          0000h = H/W データのみ
                          0001h = H/W データ及びナノギャップ生成回路電流測定値（サンプリング 10kHz） - Bias 0.1V 時の 1uA 当たりの電流測定値 42781900.799999997
                          0002h = H/W データ及び電流計測回路電流測定値（サンプリング 10kHz）        - Bias 0.1V 時の 1pA 当たりの電流測定値 5825183.6129280003
                          0003h = H/W データ及び電流計測回路電流測定値（サンプリング 50kHz）        - 同上
                          0004h = H/W データ及び電流計測回路電流測定値（サンプリング 100kHz）       - 同上
                          他    = （予約）※ 8バイト目以降のフォーマットが以下の記述とは異なる。
        [6:7]   バイト: （予約）
      (2) 固有部（データ種別 0000h-00004h は以下のフォーマット）
        [8]     バイト: Bias 印可電圧（単位は 0.1V, 符号なし8ビット整数）
        [9]     バイト: （予約）
        [10]    バイト: 電気泳動印可電圧（+側, 単位は 0.1V, 符号付き8ビット整数）
        [11]    バイト: 電気泳動印可電圧（-側, 単位は 0.1V, 符号付き8ビット整数）
        [12:15] バイト: 電流測定値（代表値, Raw データ, 符号付き32ビット整数） ※ 1 LSB に相当する電流値(A)はデータ種別及び Bias 印可電圧により異なる
        [16:19] バイト: ステッピングモーター位置（単位は 0.1um, 符号付き32ビット整数）
        [20:23] バイト: ピエゾアクチュエータ位置（単位は 1nm, 符号付き32ビット整数）
        [24:]   バイト: 電流測定値（個別値, Raw データ, 1サンプリング 符号付き32ビット整数） ※ 1 LSB に相当する電流値(A)はデータ種別及び Bias 印可電圧により異なる
                        直近の 10 msec 間に測定した電流値を時刻順に列挙
                         データ種別 0000h: サンプル数 0 = 0 バイト長
                         データ種別 0001h: サンプル数 100 = 400 バイト長
                         データ種別 0002h: サンプル数 100 = 400 バイト長
                         データ種別 0003h: サンプル数 500 = 2000 バイト長
                         データ種別 0004h: サンプル数 1000 = 4000 バイト長
    """
    global host_last_receive_time, host_last_serial_number, host_last_data_type, host_total_max_value, host_total_min_value, host_median_list
    if len(payload) >= 24:
        serial_number = struct.unpack("<I", payload[0:4])[0]
        data_type = struct.unpack("<H", payload[4:6])[0]

        # データ種別 0001h-0004h 以外はスキップ
        if data_type < 0x0001 or data_type > 0x0004:
            return

        # 24バイト目から4バイト×count個を符号付き32ビット整数として切り出して一括で展開
        count = (len(payload) - 24) // 4
        start_index = 24
        end_index = start_index + (count * 4)
        data_tuple = struct.unpack(f"<{count}i", payload[start_index:end_index])

        # 最大値、最小値、中央値を算出
        max_value = max(data_tuple)
        min_value = min(data_tuple)
        median_val = statistics.median(data_tuple)

        with host_lock:
            # 直近の受信とシリアル番号にギャップがある場合、またはデータ種別に変化がある場合はまず出力
            if (host_last_serial_number != None) and ((serial_number != host_last_serial_number + 1) or (data_type != host_last_data_type)):
                print_summary()

            host_last_receive_time = time.monotonic()
            host_last_serial_number = serial_number
            host_last_data_type = data_type
            host_total_max_value = max_value if host_total_max_value == None else max(host_total_max_value, max_value)
            host_total_min_value = min_value if host_total_min_value == None else min(host_total_min_value, min_value)
            host_median_list.append(median_val)

            # 100 個 = 1秒分蓄積されていたら出力
            if (len(host_median_list) == 100):
                print_summary()

def handle_debug_topic(payload: str) -> None:
    """ Debug トピック: 受信した文字列を即時 Print で Gateway に送信 """
    client.send_print(f"Debug: {payload}", echo=True)

def handle_log_topic(payload: str) -> None:
    """ Log トピック: 受信した文字列を即時 Print で Gateway に送信 """
    client.send_print(f"Log: {payload}", echo=True)

# =========================================================
#  統計値集計及び出力（コンソール及び Print で Gateway に送信）
# =========================================================
def print_summary() -> None:
    global host_last_receive_time, host_last_serial_number, host_last_data_type, host_total_max_value, host_total_min_value, host_median_list
    median_min_value = min(host_median_list)
    median_max_value = max(host_median_list)
    summary = (
        f"Last Serial Number = {host_last_serial_number}, "
        f"Data Type = {host_last_data_type:04x}h, "
        f"Count = {len(host_median_list)}, "
        f"Min = {host_total_min_value}, "
        f"Max = {host_total_max_value}, "
        f"Median = [{median_min_value}, {median_max_value}]"
    )
    host_last_receive_time = 0
    host_last_serial_number = None
    host_last_data_type = None
    host_total_min_value = None
    host_total_max_value = None
    host_median_list.clear()

    try:
       client.send_print(summary, echo=True)
    except Exception as e:
        print(f"[SUMMARY ERROR] {e}")

# ====================================================
#  最後の受信から1秒経過した記録を出力
# ====================================================
def host_aggregator_thread_func() -> None:
    global host_last_receive_time, host_median_list
    INTERVAL_SEC: float = 1.0
    while running:
        time.sleep(0.2)
        with host_lock:
            if (len(host_median_list) > 0) and (time.monotonic() - host_last_receive_time > INTERVAL_SEC):
                print_summary()

# ====================================================
#  Ctrl-D 検出
# ====================================================
def wait_ctrl_d() -> None:
    if sys.platform.startswith("win"):
        import msvcrt
        print("Ctrl-D で終了します。")
        while running:
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch == "\x04":  # Ctrl-D
                    return
            time.sleep(0.1)
    else:
        print("Ctrl-D で終了します。")
        while running:
            try:
                data = sys.stdin.read(1)
                if data == "" or data == "\x04":  # EOF or Ctrl-D
                    return
            except KeyboardInterrupt:
                return

# ====================================================
#  メイン
# ====================================================
def main() -> None:
    global running, client

    # 汎用クライアントを生成し、トピックごとの処理関数を登録
    client = ZeroMQClient(SUB_ADDRESS, PUSH_ADDRESS)
    client.register_host_topic_handler(handle_host_topic)
    client.register_debug_topic_handler(handle_debug_topic)
    client.register_log_topic_handler(handle_log_topic)
    client.start()

    # Host 1秒集計スレッド起動
    agg_thread = threading.Thread(target=host_aggregator_thread_func, daemon=True)
    agg_thread.start()

    try:
        wait_ctrl_d()
    except KeyboardInterrupt:
        pass

    # 終了処理
    print("\n終了処理中...")
    running = False
    agg_thread.join(timeout=2.0)
    client.stop()
    print("終了しました。")


if __name__ == "__main__":
    main()
