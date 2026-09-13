"""ZeroMQ transport. All sockets are created, used and closed on one thread."""
from collections import deque
import queue
import threading
import zmq
from zmq.utils.monitor import recv_monitor_message


class Gateway:
    def __init__(self, sub_address='tcp://127.0.0.1:55555', push_address='tcp://127.0.0.1:55556'):
        self.sub_address, self.push_address = sub_address, push_address
        self.events = queue.Queue(maxsize=4000)
        self.host = deque(maxlen=600)
        self.host_lock = threading.Lock()
        self.outgoing = queue.Queue(maxsize=8)
        self.halt = threading.Event()
        self.overflow = threading.Event()
        self.thread = None
        self.connected = False
        self.host_dropped = 0

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True, name='JIN-ZeroMQ')
        self.thread.start()

    def send(self, text):
        if not self.connected or self.halt.is_set():
            raise RuntimeError('Gatewayの送信接続がありません。')
        self.outgoing.put_nowait(b'\xfe' + text.encode('utf-8'))

    def close(self):
        self.connected = False
        self.halt.set()
        if self.thread:
            self.thread.join(timeout=2)

    def drain_host(self):
        with self.host_lock:
            result = list(self.host)
            self.host.clear()
        return result

    def _event(self, topic, value):
        try:
            self.events.put_nowait((topic, value))
        except queue.Full:
            self.overflow.set()
            self.halt.set()

    def _run(self):
        context = zmq.Context()
        sockets = []
        try:
            sub = context.socket(zmq.SUB)
            push = context.socket(zmq.PUSH)
            sockets.extend([sub, push])
            for sock in (sub, push):
                sock.setsockopt(zmq.LINGER, 0)
            sub.setsockopt(zmq.RCVHWM, 2000)
            push.setsockopt(zmq.IMMEDIATE, 1)
            push.setsockopt(zmq.SNDHWM, 1)
            for topic in (b'Host', b'Debug', b'Log'):
                sub.setsockopt(zmq.SUBSCRIBE, topic)
            monitors = [sock.get_monitor_socket(events=zmq.EVENT_CONNECTED | zmq.EVENT_DISCONNECTED)
                        for sock in (sub, push)]
            sockets.extend(monitors)
            sub.connect(self.sub_address)
            push.connect(self.push_address)
            poller = zmq.Poller()
            poller.register(sub, zmq.POLLIN)
            for monitor in monitors:
                poller.register(monitor, zmq.POLLIN)
            states = [False, False]
            while not self.halt.is_set():
                ready = dict(poller.poll(20))
                for index, monitor in enumerate(monitors):
                    if monitor in ready:
                        event = recv_monitor_message(monitor)['event']
                        states[index] = event == zmq.EVENT_CONNECTED
                        self.connected = all(states)
                        self._event('Connection', self.connected)
                        if event == zmq.EVENT_DISCONNECTED:
                            # Discard outbound commands; a reconnect must not replay old actions.
                            self._event('Error', 'Gatewayとの接続が切れました。装置状態を確認してください。')
                            self.halt.set()
                if self.halt.is_set():
                    break
                if sub in ready:
                    for _ in range(500):
                        try:
                            parts = sub.recv_multipart(zmq.NOBLOCK)
                        except zmq.Again:
                            break
                        if len(parts) != 2:
                            self._event('Error', 'Gateway受信フレーム数が不正です。')
                            continue
                        topic, payload = parts
                        if topic == b'Host':
                            with self.host_lock:
                                if len(self.host) == self.host.maxlen:
                                    self.host_dropped += 1
                                self.host.append(payload)
                        else:
                            self._event(topic.decode('ascii'), payload.decode('utf-8', errors='replace'))
                if self.connected:
                    try:
                        data = self.outgoing.get_nowait()
                    except queue.Empty:
                        continue
                    try:
                        push.send(data, zmq.NOBLOCK)
                    except zmq.Again:
                        self._event('Error', 'コマンドを送信できませんでした。自動再送はしません。')
                        self.halt.set()
        except Exception as error:
            self._event('Error', str(error))
        finally:
            self.connected = False
            for sock in reversed(sockets):
                sock.close(0)
            context.term()
