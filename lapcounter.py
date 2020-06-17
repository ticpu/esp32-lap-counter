import ujson as json
import picoweb
import ulogging
import utime
import uwebsocket as websocket
import uasyncio


class WebSocketLap:
    def __init__(self):
        self.listener = socket.socket()
        self.client_socket = None
        self.client = None
        self.last_recv = utime.time()

    def start(self):
        self.listener.bind(('0.0.0.0', 8080))
        self.listener.listen(1)
        self.listener.setblocking(False)
        self.listener.setsockopt(socket.SOL_SOCKET, 20, self.accept_client)

    def close_client(self):
        if self.client:
            self.client.close()
        if self.client_socket:
            self.client_socket.close()
        self.client_socket = None
        self.client = None

    def recv_client(self, s):
        try:
            line = self.client.readline()
            if line == b'' or line is None:
                self.close_client()
            else:
                self.client.write(line.upper())
                self.last_recv = utime.time()
        except:
            self.close_client()

    def accept_client(self, s):
        cl, cl_info = s.accept()
        if self.client_socket and (utime.time() - self.last_recv) < 10:
            cl.close()
        else:
            self.close_client()
            self.client_socket = cl
            websocket_helper.server_handshake(cl)
            self.client = websocket.websocket(cl, True)
            cl.setblocking(False)
            cl.setsockopt(socket.SOL_SOCKET, 20, self.recv_client)


class WSWrapper:
    def __init__(self, reader, writer):
        self.r = reader
        self.w = writer
        self.ws_reader = websocket.websocket(reader)

    async def aread(self, size):
        yield uasyncio.core._io_queue.queue_read(self.r)
        return self.ws_reader.read(size)

    async def areadline(self):
        yield uasyncio.core._io_queue.queue_read(self.r)
        return self.ws_reader.readline()

    async def awrite(self, data):
        size = len(data)
        if size < 126:
            header = b"\x81" + bytes([size])
        else:
            header = b"\x81\x7e" + bytes([size>>8]) + bytes([size&0xFF])

        await self.w.awrite(header)
        await self.w.awrite(data)


class SegmentDigit:
    """
       1
    2|¯¯¯|3
     | 4 |
    5|¯¯¯|6
     | 7 |
      ¯¯¯
    """
    calibration_file = "pins_map.json"
    segments = {
        None: {},
        "1": {3,6},
        "2": {1,3,4,5,7},
        "3": {1,3,4,6,7},
        "4": {2,3,4,6},
        "5": {1,2,4,6,7},
        "6": {1,2,4,5,6,7},
        "7": {1,3,6},
        "8": {1,2,3,4,5,6,7},
        "9": {1,2,3,4,6,7},
        "0": {1,2,3,5,6,7},
        "-": {4},
    }

    def __init__(self, position, pins):
        self.log = ulogging.getLogger("segment%s" % position)
        self.position = str(int(position))
        self.pins = pins
        try:
            self.load_pin_map()
        except:
            pins_map = {"0": {}, "1": {}, "invert": True}
            for k, v in enumerate(self.pins):
                if 0 <= k <= 6:
                    pins_map["0"][k+1] = v
                elif 7 <= k <= 13:
                    pins_map["1"][k-6] = v
            with open(self.calibration_file, "w") as f:
                json.dump(pins_map, f)
        self.load_pin_map()
        self.set("-")

    def load_pin_map(self):
        pins_map = json.load(open(self.calibration_file))
        self.invert = bool(pins_map["invert"])
        self.pins_map = {int(k): int(v) for k, v in pins_map[self.position].items()}

    def set(self, digit):
        self.log.info("Setting digit to %s | pin_map %s", repr(digit), self.pins_map)
        segment_pins = self.segments[digit]
        on_pins = {self.pins_map[x] for x in segment_pins}
        for pin in self.pins_map.values():
            value = pin in on_pins
            if self.invert:
                value = not value
            self.pins[pin].value(value)


class InvalidArgumentException(Exception):
    pass


class LapCounter(picoweb.WebApp):
    inputs = {}
    outputs = {}

    def __init__(self, *args, **kwargs):
        self.ws = None
        self.laps = None
        self.segments = (
                SegmentDigit(0, self.outputs),
                SegmentDigit(1, self.outputs),
        )
        uasyncio.create_task(self.check_pins())
        super().__init__(*args, **kwargs)

    async def check_pins(self):
        inputs_state = {k: v.value() for k, v in self.inputs.items()}

        while True:
            for k, v in self.inputs.items():
                new_value = v.value()
                if new_value == inputs_state[k]:
                    continue
                else:
                    for x in range(40):
                        utime.sleep_ms(1)
                        if v.value() != new_value:
                            break
                    else:
                        uasyncio.create_task(self.pin_changed(k, inputs_state[k], new_value))
                        inputs_state[k] = new_value
            await uasyncio.sleep_ms(100)


    async def pin_changed(self, pin, old_value, new_value):
        laps = self.cmd_laps_get(None)
        if new_value == 0:
            return

        if pin == 33:
            if laps is None:
                laps = 0
            laps = int(laps) - 1
        if pin == 34:
            if laps is None:
                laps = 0
            laps = int(laps) + 1
        if pin == 35:
            laps = None
        self.cmd_laps_set({'laps':laps})

    def reply(self, data, reply_type, extra_data=None):
        if extra_data is None:
            yield from self.ws.awrite(json.dumps({
                'r': reply_type,
                'd': data,
            }))
        else:
            yield from self.ws.awrite(json.dumps({
                'r': reply_type,
                'd': data,
                'e': extra_data,
            }))

    def cmd_calibration_get(self, data):
        try:
            key = data["key"]
        except KeyError:
            raise InvalidArgumentException("Need a key.")
        try:
            data = json.load(open(SegmentDigit.calibration_file))[key]
        except KeyError:
            raise InvalidArgumentException("Key must be invert, 0 or 1.")
        return {'key': key, "data": data}

    def cmd_calibration_set(self, data):
        try:
            data = {
                "invert": bool(data["invert"]),
                "0": data["0"],
                "1": data["1"],
            }
        except KeyError:
            raise InvalidArgumentException("Need invert, 0 and 1.")

        for position in ("0", "1"):
            for k, v in data[position].items():
                v = int(v)
                data[position][k] = v
                k = int(k)
                if not 1 <= k <= 7:
                    raise ValueError("Segment must be from 1 to 7, not %s." % k)
                if v not in self.outputs:
                    raise ValueError("Pin must be in %s." % ", ".join(self.outputs.keys()))

        with open(SegmentDigit.calibration_file, "w") as f:
            json.dump(data, f)

        self.segments = (
                SegmentDigit(0, self.outputs),
                SegmentDigit(1, self.outputs),
        )

        return True

    def cmd_get_pins(self, data):
        return list(self.outputs.keys())

    def cmd_laps_get(self, data):
        return self.laps

    def cmd_laps_set(self, data):
        try:
            laps = data["laps"]
            if laps is not None:
                laps = int(data["laps"])
        except KeyError:
            raise InvalidArgumentException("Laps missing.")
        except ValueError:
            raise InvalidArgumentException("Laps must be digits.")

        if laps is None:
            self.segments[0].set("-")
            self.segments[1].set("-")
        elif -9 <= laps <= 99:
            laps = str(laps)
            if len(laps) == 1:
                self.segments[0].set(None)
                self.segments[1].set(laps[0])
                laps = " " + laps
            elif len(laps) == 2:
                self.segments[0].set(laps[0])
                self.segments[1].set(laps[1])
            else:
                ValueError("Invalid number: %s" % laps)
        else:
            raise InvalidArgumentException("Laps must be between -9 and 99.")

        self.laps = laps
        return laps

    def cmd_all_pins_set(self, data):
        try:
            state = data["state"]
        except KeyError:
            raise InvalidArgumentException("Need state.")
        if state == "off" or state == "0" or state == 0:
            state = False
        else:
            state = True
        for pin in self.outputs.value():
            pin.value(state)

    def cmd_pins_set(self, data):
        try:
            pins_on = data["on"]
            pins_off = data["off"]
        except KeyError:
            raise InvalidArgumentException("Need on and off.")
        on_pins = set()
        off_pins = set()
        untouched_pins = set(self.outputs.keys())
        for pin, v in self.outputs.items():
            if pin in pins_on:
                v.on()
                on_pins.add(pin)
            elif pin in pins_off:
                v.off()
                off_pins.add(pin)
        return {'on': list(on_pins), 'off': list(off_pins), 'untouched': list(untouched_pins - on_pins - off_pins)}

    def cmd_ping(self, data):
        return "pong"

    def websocket_loop(self, ws):
        self.ws = ws
        while True:
            command_name = None
            command = None
            extra = None
            data = yield from ws.aread(1024)

            try:
                data = json.loads(data)
                command_name = "cmd_%s" % data['c']
                extra_data = data.get("e", None)
                data = data.get("d", None)
                command = getattr(self, command_name)
            except KeyError:
                yield from self.reply("no command", "error")
            except AttributeError:
                yield from self.reply("invalid command: %s" % command_name, "error")
            except Exception as e:
                yield from self.reply(str(e), "exception")
                raise
            else:
                try:
                    data = command(data)
                    yield from self.reply(data, command_name, extra_data)
                except InvalidArgumentException as e:
                    yield from self.reply(str(e), "arguments")
                except Exception as e:
                    yield from self.reply(str(e), "exception")
                    raise

        return True

    def websocket_handshake(self, req, writer):
        try:
            import ubinascii as binascii
            import uhashlib as hashlib
            import uwebsocket as websocket
        except:
            import binascii
            import hashlib
            import websocket

        if b"Upgrade" in req.headers and b"Sec-WebSocket-Key" in req.headers:
            d = hashlib.sha1(req.headers[b"Sec-WebSocket-Key"])
            d.update(b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11")
            respkey = d.digest()
            respkey = binascii.b2a_base64(respkey)[:-1]
            yield from writer.awrite(b"""\
HTTP/1.1 101 Switching Protocols\r
Upgrade: websocket\r
Connection: Upgrade\r
Sec-WebSocket-Accept: """ + respkey + b"\r\n\r\n"
            )
            ws = WSWrapper(req.reader.s, writer)
            yield from self.websocket_loop(ws)
        else:
            yield from picoweb.start_response(writer, status="400")
            yield from writer.awrite("400 Missing Upgrade or Sec-WebSocket-Key for websocket connection.\r\n\r\n")
            yield from writer.awrite("Your headers: %s\r\n" % req.headers)
            return True

