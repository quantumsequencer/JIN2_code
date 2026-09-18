# Copyright 2026 Sony Global Manufacturing & Operations Corporation

import asyncio
import zmq
import threading
import queue
import re
from typing import Callable, Dict, List, Optional, Tuple, Union

# コントロール種別定数
TYPE_NOP                 = 0x00
TYPE_SNAP_CURRENT_GRAPH  = 0x01
TYPE_SNAP_HARDWARE_GRAPH = 0x02
TYPE_PRINT               = 0x80
TYPE_DEBUG               = 0xFE
TYPE_HOST                = 0xFF

class ZeroMQClient:
    """
    ZeroMQ 汎用クライアント。

    - SUB: 指定アドレスから受信。
        受信スレッドはイベントドリブンで Queue に積むことのみ行い、
        ディスパッチスレッドが Queue から取り出して、トピックごとに登録されたハンドラ関数を呼び出す。
        受信は multipart / 単一フレーム の両方に対応。
    - PUSH: 指定アドレスへ送信。
        複数スレッドからの送信は内部ロックで保護する。

    使用方法:
        client = ZeroMQClient(sub_addr, push_addr)
        client.register_host_topic_handler(on_host)
        client.register_debug_topic_handler(on_debug)
        client.register_log_topic_handler(on_log)
        client.start()
        ...
        client.stop()
    """

    def __init__(self, sub_address: str, push_address: str) -> None:
        self._sub_address: str = sub_address
        self._push_address: str = push_address

        self._ctx: zmq.Context = zmq.Context.instance()
        self._sub_socket: Optional[zmq.Socket] = None
        self._push_socket: Optional[zmq.Socket] = None

        self._push_lock: threading.Lock = threading.Lock()

        self._handlers: Dict[bytes, Callable[[bytes], None]] = {}
        self._recv_queue: "queue.Queue[Optional[Tuple[bytes, bytes]]]" = queue.Queue()
        self._running: bool = False

        self._sub_thread: Optional[threading.Thread] = None
        self._dispatch_thread: Optional[threading.Thread] = None

        self._debug_port_loop: Optional[asyncio.AbstractEventLoop] = None
        self._debug_port_lock: asyncio.Lock = asyncio.Lock()
        self._debug_port_transaction: asyncio.Event = asyncio.Event();
        self._debug_port_response_lock: threading.Lock = threading.Lock()
        self._debug_port_response: Optional[List[str]] = None

        self._log_port_loop: Optional[asyncio.AbstractEventLoop] = None
        self._log_port_transaction: asyncio.Event = asyncio.Event();
        self._log_port_predicate_lock: threading.Lock = threading.Lock()
        self._log_port_predicate: Optional[Callable[[str], Tuple[bool, any]]] = None
        self._log_port_predicate_context: any = None

        self._command_mcbj_worker_start_lock: asyncio.Lock = asyncio.Lock()

    # ---- ハンドラ登録 ----
    def register_host_topic_handler(self, handler: Callable[[bytes], None]) -> None:
        """
        Host トピックの処理関数を登録する。
        handler: function(payload_bytes: bytes)
        """
        self._register_bytes_topic_handler("Host",  handler)

    def register_debug_topic_handler(self, handler: Callable[[str], None]) -> None:
        """
        Debug トピックの処理関数を登録する。
        handler: function(payload_str: str)
        """
        self._register_str_topic_handler("Debug",  handler)

    def register_log_topic_handler(self, handler: Callable[[str], None]) -> None:
        """
        Log トピックの処理関数を登録する。
        handler: function(payload_str: str)
        """
        self._register_str_topic_handler("Log",  handler)

    def _register_str_topic_handler(self, topic: Union[str, bytes], handler: Callable[[str], None]) -> None:
        def _handle_bytes(payload: bytes) -> None:
            text = payload.decode("utf-8", errors="replace")
            handler(text)
        self._register_bytes_topic_handler(topic,  _handle_bytes)

    def _register_bytes_topic_handler(self, topic: Union[str, bytes], handler: Callable[[bytes], None]) -> None:
        if isinstance(topic, str):
            topic = topic.encode("utf-8")
        self._handlers[topic] = handler

    # ---- 起動／停止 ----
    def start(self) -> None:
        # PUSH ソケット
        self._push_socket = self._ctx.socket(zmq.PUSH)
        self._push_socket.connect(self._push_address)

        # SUB ソケット
        self._sub_socket = self._ctx.socket(zmq.SUB)
        self._sub_socket.connect(self._sub_address)

        ## 外部登録ハンドラの topic 群に内蔵ハンドラの topic を追加（重複時は追加しない）
        topic_set = set(self._handlers.keys())
        topic_set.add(b"Debug")
        topic_set.add(b"Log")
        for topic in topic_set:
            self._sub_socket.setsockopt(zmq.SUBSCRIBE, topic)

        self._running = True

        self._sub_thread = threading.Thread(target=self._sub_loop, daemon=True)
        self._dispatch_thread = threading.Thread(target=self._dispatch_loop, daemon=True)
        self._sub_thread.start()
        self._dispatch_thread.start()

    def stop(self) -> None:
        self._running = False

        # ディスパッチを起こすため終端マーカーを入れる
        self._recv_queue.put(None)

        if self._sub_thread:
            self._sub_thread.join(timeout=2.0)
        if self._dispatch_thread:
            self._dispatch_thread.join(timeout=2.0)

        if self._sub_socket:
            self._sub_socket.close(0)
        if self._push_socket:
            self._push_socket.close(0)

    # ---- SUB 受信ループ（単一 SUB 前提のシンプル実装） ----
    def _sub_loop(self) -> None:
        poller = zmq.Poller()
        poller.register(self._sub_socket, zmq.POLLIN)

        # 長いトピックから優先して一致判定するため、長さ降順でソート
        sorted_topics = sorted(self._handlers.keys(), key=len, reverse=True)

        while self._running:
            try:
                if poller.poll(timeout=500):
                    while True:
                        try:
                            msg = self._sub_socket.recv_multipart(flags=zmq.NOBLOCK)
                        except zmq.Again:
                            break

                        topic: Optional[bytes] = None
                        payload: bytes = b""

                        if len(msg) >= 2:
                            # multipart 送信: [topic, payload, ...]
                            topic = msg[0]
                            payload = msg[1]
                        elif len(msg) == 1:
                            # 単一フレーム送信: 先頭がトピック名
                            raw = msg[0]
                            for t in sorted_topics:
                                if raw.startswith(t):
                                    topic = t
                                    payload = raw[len(t):]
                                    break
                            if topic is None:
                                continue
                        else:
                            continue

                        self._recv_queue.put((topic, payload))
            except zmq.ContextTerminated:
                break
            except Exception as e:
                print(f"[SUB ERROR] {e}")

    # ---- ディスパッチループ ----
    def _dispatch_loop(self) -> None:
        """
        Queue から取り出してトピック対応のハンドラを呼ぶ。
        受信スレッドとは別スレッドで動作する。
        """
        while self._running:
            item = self._recv_queue.get()
            if item is None:
                break
            topic, payload = item

            # 内蔵ハンドラを優先的に処理
            if topic == b"Debug":
                self._builtin_handle_debug(payload)
            if topic == b"Log":
                self._builtin_handle_log(payload)

            # 外部登録ハンドラを次に処理
            handler = self._handlers.get(topic)
            if handler:
                try:
                    handler(payload)
                except Exception as e:
                    print(f"[HANDLER ERROR] topic={topic!r} {e}")

    # ---- 内蔵ハンドラ ----
    def _builtin_handle_debug(self, payload: bytes) -> None:
        text = payload.decode("utf-8", errors="replace")
        with self._debug_port_response_lock:
            if self._debug_port_response is not None:
                if text.startswith(">"):
                    if self._debug_port_loop is not None:
                        self._debug_port_loop.call_soon_threadsafe(self._debug_port_transaction.set);
                else:
                    self._debug_port_response.append(text)

    def _builtin_handle_log(self, payload: bytes) -> None:
        text = payload.decode("utf-8", errors="replace")
        with self._log_port_predicate_lock:
            if self._log_port_predicate is not None:
                (result, context) = self._log_port_predicate(text)
                if result:
                    self._log_port_predicate_context = context
                    if self._log_port_loop is not None:
                        self._log_port_loop.call_soon_threadsafe(self._log_port_transaction.set);

    # ---- PUSH 送信関数群 ----
    def send_nop(self) -> None:
        with self._push_lock:
            self._push_socket.send(bytes([TYPE_NOP]))

    def send_snap_current_graph(self) -> None:
        with self._push_lock:
            self._push_socket.send(bytes([TYPE_SNAP_CURRENT_GRAPH]))

    def send_snap_hardware_graph(self) -> None:
        with self._push_lock:
            self._push_socket.send(bytes([TYPE_SNAP_HARDWARE_GRAPH]))

    def send_print(self, text: str, echo: bool = False) -> None:
        with self._push_lock:
            data = bytes([TYPE_PRINT]) + text.encode("utf-8")
            self._push_socket.send(data)
        if echo:
            print(f"[PRINT] {text}")

    def send_host(self, payload: bytes) -> None:
        with self._push_lock:
            data = bytes([TYPE_HOST]) + payload
            self._push_socket.send(data)

    async def send_debug_async(self, text: str) -> List[str]:
        async with self._debug_port_lock:
            with self._debug_port_response_lock:
                self._debug_port_loop = asyncio.get_running_loop()
                self._debug_port_response = []
            self._debug_port_transaction.clear()

            with self._push_lock:
                data = bytes([TYPE_DEBUG]) + text.encode("utf-8")
                self._push_socket.send(data)

            await self._debug_port_transaction.wait()
            with self._debug_port_response_lock:
                response = self._debug_port_response.copy()
                self._debug_port_response = None
                self._debug_port_loop = None
            return response

    # -------------------------------------------------------------------------------------------------------
    # Command ラッパー関数用サブルーチン … 将来 Debug Port から Host Port に経路を移動したとき、この関数で吸収する。
    # -------------------------------------------------------------------------------------------------------

    # Debug Port Response に所定の文字列で始まる行がある場合、成功とするコマンド用共通化関数
    async def _command_verify_success_async(self, command : str, response_header_on_success: str) -> bool:
        response = await self.send_debug_async(command)
        return any(line.startswith(response_header_on_success) for line in response)

    # Debug Port Response に所定の文字列で始まる行がある場合、失敗とするコマンド用共通化関数
    async def _command_verify_error_async(self, command : str, response_header_on_error: str) -> bool:
        response = await self.send_debug_async(command)
        return not any(line.startswith(response_header_on_error) for line in response)

    # mcbj fc/targetting/mt/pt/ac/cal start, asz eg/hg start 用共通化関数
    async def _command_mcbj_worker_start_async(self, start_command : str, response_header_on_error: str, pattern_log_message_on_completed: str, pattern_log_message_on_canceled) -> bool:
        # _log_port_* 共有するため、同時呼び出しを排除する（F/W 側も同時に呼び出した所でエラーとなる）。
        async with self._command_mcbj_worker_start_lock:

            # pattern_log_message_on_completed と pattern_log_message_on_stopped は正規表現のパターンとして渡される。高速化のため、compile() する。
            re_log_message_on_completed = re.compile(pattern_log_message_on_completed)
            re_log_message_on_stopped = re.compile(pattern_log_message_on_canceled)

            # Log Port Message 判定関数: 第1戻値 on_completed もしくは on_stopped にマッチしている場合 True、第2戻値 on_completed にマッチしている場合 True
            def check_log_message(text: str) -> Tuple[bool, any]:
                if re_log_message_on_completed.search(text):
                    return True, True
                if re_log_message_on_stopped.search(text):
                    return True, False
                return False, False

            # Log Port Message の監視設定
            with self._log_port_predicate_lock:
                self._log_port_loop = asyncio.get_running_loop()
                self._log_port_predicate = check_log_message
                self._log_port_predicate_context = False
            self._log_port_transaction.clear()

            # 開始コマンドを送信
            response = await self.send_debug_async(start_command)

            # コマンドの成否を判定。Debug Port Response に所定の文字列で始まる行がある場合、失敗とする。
            if any(line.startswith(response_header_on_error) for line in response):
                # Log Port Message の監視設定を解除
                with self._log_port_predicate_lock:
                    self._log_port_predicate = None
                    self._log_port_loop = None
                return False

            # 処理の完了を待機。Log Port Message を監視し、判定関数の第1戻値が True を返したら待機が解除される。
            await self._log_port_transaction.wait()

            # Log Port Message の監視設定を解除
            with self._log_port_predicate_lock:
                context = self._log_port_predicate_context
                self._log_port_predicate = None
                self._log_port_loop = None

            # 判定関数の第2戻値を return する。
            return context

    # mcbj set * 用共通化関数
    async def _command_mcbj_set_async(self, *args) -> bool:
        command = "mcbj set " + " ".join(str(x) for x in args)
        return await self._command_verify_success_async(command, "Setting change : 0")

    # asz set * 用共通化関数
    async def _command_asz_set_async(self, *args) -> bool:
        command = "asz set " + " ".join(str(x) for x in args)
        return await self._command_verify_success_async(command, "Setting change : 0")

    # -------------------------
    # Command ラッパー関数: 一般
    # -------------------------

    async def command_set_bias_async(self, bias: int) -> bool:
        return await self._command_verify_success_async("dd_ep bias " + str(bias), "BIAS set complete.")

    async def command_set_ep_async(self, ep: int) -> bool:
        return await self._command_verify_success_async("dd_ep ep " + str(ep), "EP set complete.")

    async def command_move_to_zero_point_async(self) -> bool:
        return await self._command_verify_success_async("mw_ac go0", "Actuator Control for set 0point complete.")

    async def command_start_sampling_low_10k_async(self) -> bool:
        return await self._command_verify_success_async("sv_info_sender start 0", "Start complete. result:0")

    async def command_start_sampling_high_10k_async(self) -> bool:
        return await self._command_verify_success_async("sv_info_sender start 10", "Start complete. result:0")

    async def command_start_sampling_high_50k_async(self) -> bool:
        return await self._command_verify_success_async("sv_info_sender start 2", "Start complete. result:0")

    async def command_start_sampling_high_100k_async(self) -> bool:
        return await self._command_verify_success_async("sv_info_sender start 1", "Start complete. result:0")

    async def command_stop_sampling_async(self) -> bool:
        return await self._command_verify_success_async("sv_info_sender stop", "Stop complete. result:0")

    async def command_mcbj_stop_async(self) -> bool:
        return await self._command_verify_error_async("mcbj stop", "Stop error : ")

    async def command_mcbj_first_cut_async(self) -> bool:
        return await self._command_mcbj_worker_start_async("mcbj fc start", "Start error : ", "First Cut finish!$", "First Cut canceld!$")  # F/W と合わせるため、Typo は直さない。

    async def command_mcbj_targeting_async(self) -> bool:
        return await self._command_mcbj_worker_start_async("mcbj targeting start", "Targeting Start error : ", "Targeting finished\\.$", "Targeting canceled\\.$")

    async def command_mcbj_motor_training_async(self) -> bool:
        return await self._command_mcbj_worker_start_async("mcbj mt start", "MotorTraining Start error : ", "Actuator Training\\(Motor\\) end!$", "Actuator Training\\(Motor\\) canceld!$")  # F/W と合わせるため、Typo は直さない。

    async def command_mcbj_piezo_training_async(self) -> bool:
        return await self._command_mcbj_worker_start_async("mcbj pt start", "PiezoTraining Start error : ", "Actuator Training\\(Piezo\\) end!$", "Actuator Training\\(Piezo\\) canceld!$")  # F/W と合わせるため、Typo は直さない。

    async def command_mcbj_auto_cut_async(self) -> bool:
        return await self._command_mcbj_worker_start_async("mcbj ac start", "AutoCut Start error : ", "End\\.$", "End\\. Canceled\\.$")

    async def command_mcbj_calibration_async(self) -> bool:
        return await self._command_mcbj_worker_start_async("mcbj cal start", "Calibration Start error : ", "Calibration end!$", "Calibration canceld!$")  # F/W と合わせるため、Typo は直さない。

    async def command_asz_expand_gap_async(self) -> bool:
        return await self._command_mcbj_worker_start_async("asz eg start", "Start error : ", "ExpandGap finished\\.$", "ExpandGap canceled\\.$")

    async def command_asz_hold_gap_async(self) -> bool:
        return await self._command_mcbj_worker_start_async("asz hg start", "Start error : ", "HoldGap finished\\.$", "HoldGap canceled\\.$")

    # ----------------------------------------------
    # Command ラッパー関数: MCBJ/ASZ 内部パラメータ設定
    # ----------------------------------------------

    # First Cut
    #   mcbj set fc up_limit 10000          -> command_mcbj_set_fc_up_limit_async(10000)
    #   mcbj set fc last_down_distance 380  -> command_mcbj_set_fc_last_down_distance_async(380)
    #   mcbj set fc threshold 0x0037C53A    -> command_mcbj_set_fc_threshold_async(0x0037C53A)
    #   mcbj set fc speed_table 0 100 3800  -> command_mcbj_set_fc_speed_table_async(0, 100, 3800)
    #   mcbj set fc speed_table 1 400 3800  -> command_mcbj_set_fc_speed_table_async(1, 400, 3800)
    #   mcbj set fc speed_table 2 1000 3800 -> command_mcbj_set_fc_speed_table_async(2, 1000, 3800)

    async def command_mcbj_set_fc_up_limit_async(self, up_limit_displacement: int) -> bool:
        return await self._command_mcbj_set_async("fc", "up_limit", up_limit_displacement)

    async def command_mcbj_set_fc_last_down_distance_async(self, distance: int) -> bool:
        return await self._command_mcbj_set_async("fc", "last_down_distance", distance)

    async def command_mcbj_set_fc_threshold_async(self, threshold_current: int) -> bool:
        return await self._command_mcbj_set_async("fc", "threshold", f"0x{threshold_current:08X}")

    async def command_mcbj_set_fc_speed_table_async(self, trial_index: int, up_speed: int, down_speed: int) -> bool:
        return await self._command_mcbj_set_async("fc", "speed_table", trial_index, up_speed, down_speed)

    # Motor Training
    #   mcbj set mt ROUGH 0x0037C53A 0x116DA25C 20 -> command_mcbj_set_mt_async(0x0037C53A, 0x116DA25C, 20)

    async def command_mcbj_set_mt_async(self, lower_limit_current: int, upper_limit_current: int, motor_speed: int) -> bool:
        return await self._command_mcbj_set_async("mt", "ROUGH", f"0x{lower_limit_current:08X}", f"0x{upper_limit_current:08X}", motor_speed)

    # Piezo Training
    #   mcbj set pt SMOOTH 0x0037C53A 0x116DA25C 500 -> command_mcbj_set_pt_async(0x0037C53A, 0x116DA25C, 500)

    async def command_mcbj_set_pt_async(self, lower_limit_current: int, upper_limit_current: int, piezo_speed: int) -> bool:
        return await self._command_mcbj_set_async("pt", "SMOOTH", f"0x{lower_limit_current:08X}", f"0x{upper_limit_current:08X}", piezo_speed)

    # Targeting
    #   mcbj set targeting threshold 0x14664CD2          -> command_mcbj_set_targeting_threshold_async(0x14664CD2)
    #   mcbj set targeting up_table 0 0x15641390 13 250  -> command_mcbj_set_targeting_up_table_async(0, 0x15641390, 13, 250)
    #   mcbj set targeting up_table 1 0x15B7F511 25 500  -> command_mcbj_set_targeting_up_table_async(1, 0x15B7F511, 25, 500)
    #   mcbj set targeting up_table 2 0x15BE51FA 35 700  -> command_mcbj_set_targeting_up_table_async(2, 0x15BE51FA, 35, 700)
    #   mcbj set targeting up_table 3 0x7FFFFFFF 50 1000 -> command_mcbj_set_targeting_up_table_async(3, 0x7FFFFFFF, 50, 1000)
    #   mcbj set targeting down_table 0 0x0982B581 9 180 -> command_mcbj_set_targeting_down_table_async(0, 0x0982B581, 9, 180)
    #   mcbj set targeting down_table 1 0x7FFFFFFF 1 20  -> command_mcbj_set_targeting_down_table_async(1, 0x7FFFFFFF, 1, 20)
    #   mcbj set targeting up_limit 10000                -> command_mcbj_set_targeting_up_limit_async(10000)
    #   mcbj set targeting timeout 30000                 -> command_mcbj_set_targeting_timeout_async(30000)

    async def command_mcbj_set_targeting_threshold_async(self, threshold_current: int) -> bool:
        return await self._command_mcbj_set_async("targeting", "threshold", f"0x{threshold_current:08X}")

    async def command_mcbj_set_targeting_up_table_async(self, index: int, upper_limit_current: int, displacement: int, speed: int) -> bool:
        return await self._command_mcbj_set_async("targeting", "up_table", index, f"0x{upper_limit_current:08X}", displacement, speed)

    async def command_mcbj_set_targeting_down_table_async(self, index: int, upper_limit_current: int, displacement: int, speed: int) -> bool:
        return await self._command_mcbj_set_async("targeting", "down_table", index, f"0x{upper_limit_current:08X}", displacement, speed)

    async def command_mcbj_set_targeting_up_limit_async(self, up_limit_displacement: int) -> bool:
        return await self._command_mcbj_set_async("targeting", "up_limit", up_limit_displacement)

    async def command_mcbj_set_targeting_timeout_async(self, timeout_milliseconds: int) -> bool:
        return await self._command_mcbj_set_async("targeting", "timeout", timeout_milliseconds)

    # Auto Cut
    #   mcbj set ac threshold 0x0006227E          -> command_mcbj_set_ac_threshold_async(0x0006227E)
    #   mcbj set ac up_table 0 0x0856196D 50 1000 -> command_mcbj_set_ac_up_table_async(0, 0x0856196D, 50, 1000)
    #   mcbj set ac up_table 1 0x0F3B72A5 50 1000 -> command_mcbj_set_ac_up_table_async(1, 0x0F3B72A5, 50, 1000)
    #   mcbj set ac up_table 2 0x11EDC168 45 900  -> command_mcbj_set_ac_up_table_async(2, 0x11EDC168, 45, 900)
    #   mcbj set ac up_table 3 0x12C24A0B 35 700  -> command_mcbj_set_ac_up_table_async(3, 0x12C24A0B, 35, 700)
    #   mcbj set ac up_table 4 0x134B8705 10 200  -> command_mcbj_set_ac_up_table_async(4, 0x134B8705, 10, 200)
    #   mcbj set ac up_table 5 0x1476F645 25 500  -> command_mcbj_set_ac_up_table_async(5, 0x1476F645, 25, 500)
    #   mcbj set ac up_table 6 0x153CB4C5 45 900  -> command_mcbj_set_ac_up_table_async(6, 0x153CB4C5, 45, 900)
    #   mcbj set ac up_table 7 0x7FFFFFFF 50 1000 -> command_mcbj_set_ac_up_table_async(7, 0x7FFFFFFF, 50, 1000)
    #   mcbj set ac timeout 30000                 -> command_set_ac_timeout_async(30000)

    async def command_mcbj_set_ac_threshold_async(self, threshold_current: int) -> bool:
        return await self._command_mcbj_set_async("ac", "threshold", f"0x{threshold_current:08X}")

    async def command_mcbj_set_ac_up_table_async(self, index: int, upper_limit_current: int, displacement: int, speed: int) -> bool:
        return await self._command_mcbj_set_async("ac", "up_table", index, f"0x{upper_limit_current:08X}", displacement, speed)

    async def command_set_ac_timeout_async(self, timeout_milliseconds: int) -> bool:
        return await self._command_mcbj_set_async("ac", "timeout", timeout_milliseconds)

    # Calibration
    #   mcbj set cal limit 0x02369472 0x6EA8FE50 -> command_mcbj_set_cal_limit_async(0x02369472, 0x6EA8FE50)
    #   mcbj set cal speed 100                   -> command_mcbj_set_cal_speed_async(100)

    async def command_mcbj_set_cal_limit_async(self, lower_limit_current: int, upper_limit_current: int) -> bool:
        return await self._command_mcbj_set_async("cal", "limit", f"0x{lower_limit_current:08X}", f"0x{upper_limit_current:08X}")

    async def command_mcbj_set_cal_speed_async(self, speed: int) -> bool:
        return await self._command_mcbj_set_async("cal", "speed", speed)

    # Expand Gap
    #   asz set eg delta 800                       -> command_asz_set_eg_delta_async(800)
    #   asz set eg stable_current_range 0x00A9F955 -> command_asz_set_eg_stable_current_range_async(0x00A9F955)
    #   asz set eg stable_current_count 50         -> command_asz_set_eg_stable_current_count_async(50)

    async def command_asz_set_eg_delta_async(self, delta: int) -> bool:
        return await self._command_asz_set_async("eg", "delta", delta)

    async def command_asz_set_eg_stable_current_range_async(self, range_current: int) -> bool:
        return await self._command_asz_set_async("eg", "stable_current_range", f"0x{range_current:08X}")

    async def command_asz_set_eg_stable_current_count_async(self, count: int) -> bool:
        return await self._command_asz_set_async("eg", "stable_current_count", count)

    # Hold Gap
    #   asz set hg tunnel_current 0x004C0C02    -> command_asz_set_hg_tunnel_current_async(0x004C0C02)
    #   asz set hg fb_table 0 0x0010FF55 0 0    -> command_asz_set_hg_fb_table_async(0, 0x0010FF55, 0, 0)
    #   asz set hg fb_table 1 0x0038A871 2 1000 -> command_asz_set_hg_fb_table_async(1, 0x0038A871, 2, 1000)
    #   asz set hg fb_table 2 0x00A9F955 18 500 -> command_asz_set_hg_fb_table_async(2, 0x00A9F955, 18, 500)
    #   asz set hg fb_table 3 0x046D28E4 34 300 -> command_asz_set_hg_fb_table_async(3, 0x046D28E4, 34, 300)
    #   asz set hg fb_table 4 0xFFFFFFFF 88 300 -> command_asz_set_hg_fb_table_async(4, 0xFFFFFFFF, 88, 300)

    async def command_asz_set_hg_tunnel_current_async(self, tunnel_current: int) -> bool:
        return await self._command_asz_set_async("hg", "tunnel_current", f"0x{tunnel_current:08X}")

    async def command_asz_set_hg_fb_table_async(self, index: int, upper_limit_gap_current: int, displacement: int, speed: int) -> bool:
        return await self._command_asz_set_async("hg", "fb_table", index, f"0x{upper_limit_gap_current:08X}", displacement, speed)
