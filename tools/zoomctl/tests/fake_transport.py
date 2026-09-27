import mido


class FakeTransport:
    """Replays queued mido messages; records everything sent."""

    def __init__(self, responses=None):
        self.sent = []
        self.responses = list(responses or [])

    def send(self, message):
        self.sent.append(message)

    def receive(self, timeout=None):
        if not self.responses:
            raise AssertionError("unexpected receive: response queue empty")
        return self.responses.pop(0)


def sysex(data):
    return mido.Message("sysex", data=list(data))
