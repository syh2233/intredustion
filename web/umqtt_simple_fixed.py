# 修复版本的 umqtt.simple
import usocket as socket
import ustruct as struct
from uerrno import EINPROGRESS, ETIMEDOUT


class MQTTException(Exception):
    pass


class MQTTClient:
    def __init__(self, client_id, server, port=0, user=None, password=None, keepalive=0,
                 ssl=False, ssl_params={}):
        if port == 0:
            port = 8883 if ssl else 1883
        self.client_id = client_id
        self.sock = None
        self.server = server
        self.port = port
        self.ssl = ssl
        self.ssl_params = ssl_params
        self.pid = 0
        self.cb = None
        self.user = user
        self.pswd = password
        self.keepalive = keepalive
        self.lw_topic = None
        self.lw_msg = None
        self.lw_qos = 0
        self.lw_retain = False

    def _send_str(self, s):
        self.sock.write(struct.pack("!H", len(s)))
        self.sock.write(s)

    def _recv_len(self):
        n = 0
        sh = 0
        while 1:
            b = self.sock.read(1)[0]
            n |= (b & 0x7f) << sh
            if not b & 0x80:
                return n
            sh += 7

    def set_callback(self, f):
        self.cb = f

    def set_last_will(self, topic, msg, retain=False, qos=0):
        assert 0 <= qos <= 2
        assert topic
        self.lw_topic = topic
        self.lw_msg = msg
        self.lw_qos = qos
        self.lw_retain = retain

    def connect(self, clean_session=True):
        self.sock = socket.socket()
        addr = socket.getaddrinfo(self.server, self.port)[0][-1]
        self.sock.connect(addr)
        if self.ssl:
            import ussl
            self.sock = ussl.wrap_socket(self.sock, **self.ssl_params)

        # 构造连接消息
        var_header = bytearray()
        var_header.append(4)  # 协议名长度
        var_header.extend(b'MQTT')  # 协议名
        var_header.append(4)  # 协议级别

        # 连接标志
        flags = 0
        if clean_session:
            flags |= 0x02
        if self.user:
            flags |= 0x80
        if self.pswd:
            flags |= 0x40
        if self.lw_topic:
            flags |= 0x4 | (self.lw_qos & 1) << 3 | (self.lw_qos & 2) << 3
            flags |= self.lw_retain << 5
        var_header.append(flags)

        # 保持连接时间
        if self.keepalive:
            var_header.append(self.keepalive >> 8)
            var_header.append(self.keepalive & 0xff)
        else:
            var_header.append(0)
            var_header.append(0)

        # 计算载荷长度
        payload_len = 2 + len(self.client_id)
        if self.user:
            payload_len += 2 + len(self.user)
            payload_len += 2 + len(self.pswd)
        if self.lw_topic:
            payload_len += 2 + len(self.lw_topic)
            payload_len += 2 + len(self.lw_msg)

        # 构造完整消息
        msg = bytearray()
        msg.append(0x10)  # CONNECT消息类型
        rem_len = len(var_header) + payload_len

        # 编码剩余长度
        if rem_len > 0:
            while rem_len > 0:
                b = rem_len & 0x7f
                rem_len >>= 7
                if rem_len > 0:
                    b |= 0x80
                msg.append(b)

        msg.extend(var_header)

        # Client ID
        msg.append(len(self.client_id) >> 8)
        msg.append(len(self.client_id) & 0xff)
        msg.extend(self.client_id.encode())

        # 用户名和密码
        if self.user:
            msg.append(len(self.user) >> 8)
            msg.append(len(self.user) & 0xff)
            msg.extend(self.user.encode())
            msg.append(len(self.pswd) >> 8)
            msg.append(len(self.pswd) & 0xff)
            msg.extend(self.pswd.encode())

        # Will消息
        if self.lw_topic:
            msg.append(len(self.lw_topic) >> 8)
            msg.append(len(self.lw_topic) & 0xff)
            msg.extend(self.lw_topic.encode())
            msg.append(len(self.lw_msg) >> 8)
            msg.append(len(self.lw_msg) & 0xff)
            msg.extend(self.lw_msg.encode())

        # 发送连接消息
        self.sock.write(msg)

        # 等待CONNACK响应
        resp = self.sock.read(4)
        if len(resp) != 4 or resp[0] != 0x20 or resp[1] != 0x02:
            raise MQTTException("Invalid CONNACK response")

        if resp[3] != 0:
            raise MQTTException(resp[3])

        return resp[2] & 1

    def disconnect(self):
        self.sock.write(b"\xe0\0")
        self.sock.close()

    def ping(self):
        self.sock.write(b"\xc0\0")

    def publish(self, topic, msg, retain=False, qos=0):
        pkt = bytearray(b"\x30\0\0\0")
        pkt[0] |= qos << 1 | retain
        sz = 2 + len(topic) + len(msg)
        if qos > 0:
            sz += 2
        assert sz < 2097152
        i = 1
        while sz > 0x7f:
            pkt[i] = (sz & 0x7f) | 0x80
            sz >>= 7
            i += 1
        pkt[i] = sz
        struct.pack_into("!H", pkt, i + 1, len(topic))
        self.sock.write(pkt, i + 3)
        self.sock.write(topic)
        self.sock.write(msg)
        if qos == 1:
            while 1:
                op = self.wait_msg()
                if op == 0x40:
                    sz = self.sock.read(1)
                    assert sz == b"\x02"
                    self.pid = self.sock.read(2)
                    self.pid = (self.pid[0] << 8) | self.pid[1]
                    return
        elif qos == 2:
            assert 0

    def subscribe(self, topic, qos=0):
        assert self.cb is not None, "Subscribe callback is not set"
        pkt = bytearray(b"\x82\0\0\0")
        self.pid += 1
        struct.pack_into("!BH", pkt, 1, 2 + 2 + len(topic) + 1, self.pid)
        self.sock.write(pkt)
        self._send_str(topic)
        self.sock.write(qos.to_bytes(1, "little"))
        while 1:
            op = self.wait_msg()
            if op == 0x90:
                resp = self.sock.read(4)
                assert resp[0] == 0x90 and resp[2] == pkt[2] and resp[3] == pkt[3]
                if resp[1] == 0x80:
                    raise MQTTException(resp[1])
                return

    def wait_msg(self):
        res = self.sock.read(1)
        if res is None:
            return None
        if res == b"":
            raise OSError(-1)
        if res == b"\xd0":  # PINGRESP
            sz = self.sock.read(1)[0]
            assert sz == 0
            return None
        op = res[0]
        if op & 0xf0 != 0x30:
            return op
        sz = self._recv_len()
        topic_len = self.sock.read(2)
        topic_len = (topic_len[0] << 8) | topic_len[1]
        topic = self.sock.read(topic_len)
        sz -= topic_len + 2
        if op & 6:
            pid = self.sock.read(2)
            pid = (pid[0] << 8) | pid[1]
            sz -= 2
        msg = self.sock.read(sz)
        self.cb(topic, msg)
        if op & 6 == 2:
            pkt = bytearray(b"\x40\x02\0\0")
            struct.pack_into("!H", pkt, 2, pid)
            self.sock.write(pkt)
        elif op & 6 == 4:
            assert 0
        return op

    def check_msg(self):
        self.sock.setblocking(True)
        return self.wait_msg()