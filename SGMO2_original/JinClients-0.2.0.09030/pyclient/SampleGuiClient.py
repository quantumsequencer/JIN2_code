# Copyright 2026 Sony Global Manufacturing & Operations Corporation

import asyncio
import statistics
import struct
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import List, Optional
from ZeroMQClient import ZeroMQClient

# ==== 設定 ====
SUB_ADDRESS:  str = "tcp://localhost:55555"
PUSH_ADDRESS: str = "tcp://localhost:55556"

# 列幅（文字数換算）
COL2_WIDTH_CHARS: int = 40
INDENT_PREFIX: str = "    "   # アルファベット2文字程度のインデント

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

# UI への反映用 (UI スレッドから読み書き)
app: Optional["SampleGuiApp"] = None

# ====================================================
#  GUI アプリ本体
# ====================================================
class SampleGuiApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root: tk.Tk = root
        self.root.title("Sample GUI Client")

        # ---- StringVar (Entry のテキスト用) ----
        self.var_host:  tk.StringVar = tk.StringVar()
        self.var_debug: tk.StringVar = tk.StringVar()
        self.var_log:   tk.StringVar = tk.StringVar()
        self.var_print_input: tk.StringVar = tk.StringVar()
        self.var_debug_input: tk.StringVar = tk.StringVar()

        # バックグラウンドスレッドとそのイベントループの起動
        self.async_loop = asyncio.new_event_loop()
        def run_async_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()
        threading.Thread(target=run_async_loop, args=(self.async_loop,), daemon=True).start()

        # ---- ウィジェット配置 ----
        self._build_widgets()

        # 終了処理
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_widgets(self) -> None:
        # Label (1段目第1列)
        ttk.Label(self.root, text="Receive Frame").grid(row=0, column=0, sticky="w", padx=4, pady=2)

        # Label (2段目第1列, インデント)
        ttk.Label(self.root, text=INDENT_PREFIX + "Host: Frame Summary").grid(row=1, column=0, sticky="w", padx=4, pady=2)

        # Label (3段目第1列, インデント)
        ttk.Label(self.root, text=INDENT_PREFIX + "Debug: Text").grid(row=2, column=0, sticky="w", padx=4, pady=2)

        # Label (4段目第1列, インデント)
        ttk.Label(self.root, text=INDENT_PREFIX + "Log: Text").grid(row=3, column=0, sticky="w", padx=4, pady=2)

        # Label (5段目第1列)
        ttk.Label(self.root, text="Transmit Control Message").grid(row=4, column=0, sticky="w", padx=4, pady=2)

        # Label (6段目第1列, インデント)
        ttk.Label(self.root, text=INDENT_PREFIX + "NOP").grid(row=5, column=0, sticky="w", padx=4, pady=2)

        # Label (7段目第1列, インデント)
        ttk.Label(self.root, text=INDENT_PREFIX + "SNAP Current Graph").grid(row=6, column=0, sticky="w", padx=4, pady=2)

        # Label (8段目第1列, インデント)
        ttk.Label(self.root, text=INDENT_PREFIX + "SNAP Hardware Graph").grid(row=7, column=0, sticky="w", padx=4, pady=2)

        # Label (9段目第1列, インデント)
        ttk.Label(self.root, text=INDENT_PREFIX + "PRINT Message").grid(row=8, column=0, sticky="w", padx=4, pady=2)

        # Label (10段目第1列, インデント)
        ttk.Label(self.root, text=INDENT_PREFIX + "DEBUG Command").grid(row=9, column=0, sticky="w", padx=4, pady=2)

        # Entry (2段目第2列, 読み取り専用)
        entry_host = ttk.Entry(self.root, textvariable=self.var_host, width=COL2_WIDTH_CHARS, state="readonly")
        entry_host.grid(row=1, column=1, sticky="ew", padx=4, pady=2)

        # Entry (3段目第2列, 読み取り専用)
        entry_debug = ttk.Entry(self.root, textvariable=self.var_debug, width=COL2_WIDTH_CHARS, state="readonly")
        entry_debug.grid(row=2, column=1, sticky="ew", padx=4, pady=2)

        # Entry (4段目第2列, 読み取り専用)
        entry_log = ttk.Entry(self.root, textvariable=self.var_log, width=COL2_WIDTH_CHARS, state="readonly")
        entry_log.grid(row=3, column=1, sticky="ew", padx=4, pady=2)

        # Entry (9段目第2列, 入力可能)
        entry_print_in = ttk.Entry(self.root, textvariable=self.var_print_input, width=COL2_WIDTH_CHARS)
        entry_print_in.grid(row=8, column=1, sticky="ew", padx=4, pady=2)
        entry_print_in.bind("<Return>", self._on_print_entered)

        # Entry (10段目第2列, 入力可能)
        self.entry_debug_in = ttk.Entry(self.root, textvariable=self.var_debug_input, width=COL2_WIDTH_CHARS)
        self.entry_debug_in.grid(row=9, column=1, sticky="ew", padx=4, pady=2)
        self.entry_debug_in.bind("<Return>", self._on_debug_entered)

        # Button (6段目第2列, アルファベット10文字程度の固定幅・右寄せ)
        btn_nop = ttk.Button(self.root, text="Transmit", width=10, command=self._on_nop_clicked)
        btn_nop.grid(row=5, column=1, sticky="e", padx=4, pady=2)

        # Button (7段目第2列, アルファベット10文字程度の固定幅・右寄せ)
        btn_snap_current_graph = ttk.Button(self.root, text="Transmit", width=10, command=self._on_snap_current_graph_clicked)
        btn_snap_current_graph.grid(row=6, column=1, sticky="e", padx=4, pady=2)

        # Button (8段目第2列, アルファベット10文字程度の固定幅・右寄せ)
        btn_snap_hardware_graph = ttk.Button(self.root, text="Transmit", width=10, command=self._on_snap_hardware_graph_clicked)
        btn_snap_hardware_graph.grid(row=7, column=1, sticky="e", padx=4, pady=2)

        # ---- 列幅の調整 ----
        # 第1列: 含まれるラベルが見切れないようにする (grid は内容に合わせる)
        self.root.columnconfigure(0, weight=0)
        # 第2列: COL2_WIDTH_CHARS で固定 (Entry の width で確保)
        self.root.columnconfigure(1, weight=1)

    # ---- イベントハンドラ ----
    def _on_print_entered(self, event: tk.Event) -> None:
        text = self.var_print_input.get()
        if text and client is not None:
            client.send_print(text)

    def _on_debug_entered(self, event: tk.Event) -> None:
        text = self.var_debug_input.get()
        if text and client is not None:
            asyncio.run_coroutine_threadsafe(self._send_debug_async(text), self.async_loop)

    async def _send_debug_async(self, text: str) -> None:
        self.root.after(0, lambda: self.entry_debug_in.config(state=tk.DISABLED))
        await client.send_debug_async(text)
        self.root.after(0, lambda: self.entry_debug_in.config(state=tk.NORMAL))

    def _on_nop_clicked(self) -> None:
        if client is not None:
            client.send_nop()

    def _on_snap_current_graph_clicked(self) -> None:
        if client is not None:
            client.send_snap_current_graph()

    def _on_snap_hardware_graph_clicked(self) -> None:
        if client is not None:
            client.send_snap_hardware_graph()

    def _on_close(self) -> None:
        global running
        running = False
        try:
            if client is not None:
                client.stop()
        except Exception:
            pass
        self.root.destroy()

    # ---- UI 更新メソッド (UI スレッドから呼ぶ) ----
    def set_host_text(self, text: str) -> None:
        self.var_host.set(text)

    def set_debug_text(self, text: str) -> None:
        self.var_debug.set(text)

    def set_log_text(self, text: str) -> None:
        self.var_log.set(text)

# ===================================================================
#  各トピックの処理関数 (ZeroMQClient のディスパッチスレッドから呼ばれる)
#   → UI 更新は root.after() 経由でメインスレッドへ
# ===================================================================
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
    if app is not None:
        app.root.after(0, app.set_debug_text, payload)

def handle_log_topic(payload: str) -> None:
    if app is not None:
        app.root.after(0, app.set_log_text, payload)

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
        if client is not None:
            client.send_print(summary)
        if app is not None:
            app.root.after(0, app.set_host_text, summary)
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
#  メイン
# ====================================================
def main() -> None:
    global running, client, app

    root = tk.Tk()
    app = SampleGuiApp(root)

    client = ZeroMQClient(SUB_ADDRESS, PUSH_ADDRESS)
    client.register_host_topic_handler(handle_host_topic)
    client.register_debug_topic_handler(handle_debug_topic)
    client.register_log_topic_handler(handle_log_topic)
    client.start()

    agg_thread = threading.Thread(target=host_aggregator_thread_func, daemon=True)
    agg_thread.start()

    try:
        root.mainloop()
    finally:
        running = False
        agg_thread.join(timeout=2.0)
        try:
            client.stop()
        except Exception:
            pass


if __name__ == "__main__":
    main()
