def r():
    import machine
    machine.reset()


def cat(fname):
    with open(fname, 'r') as f:
        print(f.read())


def cycle_all(pins, delay=500):
    for i in pins.values():
        i.off()

    import utime
    utime.sleep_ms(delay)

    for i in pins.values():
        i.on()


ROUTES = [
    ('/', lambda req, resp: (yield from app.sendfile(resp, '/static/index.html'))),
    ('/ws', lambda req, resp: (yield from app.websocket_handshake(req, resp))),
]


if __name__ == '__main__':
    #cycle_all(outputs, 200)
    import ulogging as logging
    import utime
    import lapcounter
    from machine import Pin
    logging.basicConfig(level=logging.INFO)
    lapcounter.LapCounter.inputs = inputs
    lapcounter.LapCounter.outputs = outputs
    app = lapcounter.LapCounter(__name__, ROUTES)
    app.run('0.0.0.0', 80, True)
