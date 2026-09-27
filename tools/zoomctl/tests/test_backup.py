import json

from tools.zoomctl.backup import run_backup
from tools.zoomctl.codec import crc32_5, pack_7bit
from tools.zoomctl.tests.fake_transport import FakeTransport, sysex


def _identity_reply():
    return sysex([0x7E, 0x00, 0x06, 0x02, 0x52, 0x6E, 0x00, 0x0C, 0x00] + list(b"2.00"))


def _patch_reply(data: bytes):
    packet = [0x52, 0x00, 0x6E, 0x60, 0x04, 0, 0, 0, 0, 0]
    packet += [len(data) & 0x7F, (len(data) >> 7) & 0x7F]
    packet += list(pack_7bit(data)) + list(crc32_5(data))
    return sysex(packet)


def _file_block_reply(data: bytes):
    block = [0x52, 0x00, 0x6E, 0x60, 0x04, 0, 0, 0]
    block += [len(data) & 0x7F, (len(data) >> 7) & 0x7F]
    block += list(pack_7bit(data)) + list(crc32_5(data))
    return sysex(block)


def _file_end_reply():
    return sysex([0x52, 0x00, 0x6E, 0x60, 0x04, 0, 0, 0, 0, 0])


def _file_list_reply(name: str):
    return sysex([0x52, 0x00, 0x6E, 0x60, 0x04, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                 + list(name.encode()) + [0])


def _open_reply():
    return sysex([0x52, 0x00, 0x6E, 0x60, 0x20])


def _responses_for_full_backup():
    ack = [0x52, 0x00, 0x6E, 0x60, 0x05]
    return [
        _identity_reply(),                                   # identity
        sysex([0x52, 0x00, 0x6E, 0x52]),                     # pcmode on
        sysex([0x52, 0x00, 0x6E, 0x44, 2, 0, 0x20, 0, 0, 0, 10, 0]),  # 2 patches, bsize 10
        _patch_reply(b"patch-one"),                          # patch 1
        _patch_reply(b"patch-two"),                          # patch 2
        _file_list_reply("A.ZD2"),                           # fs list
        _file_list_reply("B.ZD2"),
        sysex([0x52, 0x00, 0x6E, 0x60, 0x05]),               # end of list
        _open_reply(), _open_reply(),                        # open A (sent twice)
        sysex(ack), sysex([0x52, 0x00, 0x6E, 0x60, 0x22]), _file_block_reply(b"effect-one"),
        sysex(ack), sysex([0x52, 0x00, 0x6E, 0x60, 0x22]), _file_end_reply(),
        sysex([0x52, 0x00, 0x6E, 0x60, 0x21]), sysex([0x52, 0x00, 0x6E, 0x60, 0x09]),
        _open_reply(), _open_reply(),                        # open B (sent twice)
        sysex(ack), sysex([0x52, 0x00, 0x6E, 0x60, 0x22]), _file_block_reply(b"effect-two"),
        sysex(ack), sysex([0x52, 0x00, 0x6E, 0x60, 0x22]), _file_end_reply(),
        sysex([0x52, 0x00, 0x6E, 0x60, 0x21]), sysex([0x52, 0x00, 0x6E, 0x60, 0x09]),
        sysex([0x52, 0x00, 0x6E, 0x53]),                     # pcmode off
    ]


def test_run_backup_writes_artifacts_and_manifest(tmp_path):
    from tools.zoomctl.pedal import ZoomPedal

    pedal = ZoomPedal(FakeTransport(_responses_for_full_backup()))

    result = run_backup(pedal, out_dir=tmp_path / "backups", manifests_dir=tmp_path / "manifests")

    manifest = json.loads(result.manifest_path.read_text())
    assert manifest["identity"]["model"] == "G1 Four"
    assert manifest["patch_bank"]["count"] == 2
    assert [p["location"] for p in manifest["patches"]] == [1, 2]
    assert manifest["patches"][0]["sha256"]
    assert [f["name"] for f in manifest["fs"]["files"]] == ["A.ZD2", "B.ZD2"]
    assert manifest["fs"]["files"][0]["sha256"]
    assert manifest["state_digest"] == result.manifest_path.stem
    assert (result.artifact_dir / "patches" / "001.zptc").read_bytes() == b"patch-one"
    assert (result.artifact_dir / "fs" / "A.ZD2").read_bytes() == b"effect-one"
    assert manifest["timings"]["total_seconds"] >= 0


def test_run_backup_reports_oracle_differences(tmp_path):
    from tools.zoomctl.pedal import ZoomPedal

    oracle = tmp_path / "FS.bin"
    oracle.write_bytes(b"A.ZD2\x00" + b"C.ZD2\x00")
    pedal = ZoomPedal(FakeTransport(_responses_for_full_backup()))

    result = run_backup(
        pedal,
        out_dir=tmp_path / "backups",
        manifests_dir=tmp_path / "manifests",
        oracle_path=oracle,
    )

    assert result.manifest["oracle"]["source"] == str(oracle)
    assert result.manifest["oracle"]["device_only"] == ["B.ZD2"]
    assert result.manifest["oracle"]["oracle_only"] == ["C.ZD2"]
