import pytest

from rttgap import Thresholds, evaluate


def test_direct_when_echo_matches_tcp():
    r = evaluate(20.0, [21.5, 20.8, 23.0])
    assert r.verdict == "direct"
    assert r.gap_ms == pytest.approx(0.8)
    assert r.tcp_rtt_ms == 20.0 and r.min_echo_ms == 20.8


def test_proxied_when_echo_crosses_a_hidden_leg():
    r = evaluate(2.0, [176.0, 174.2, 180.9])
    assert r.verdict == "proxied" and r.is_proxied
    assert r.gap_ms == pytest.approx(172.2)


def test_unsure_band():
    assert evaluate(10.0, [28.0]).verdict == "unsure"        # gap 18
    assert evaluate(10.0, [22.0]).verdict == "direct"        # gap 12 is not above 12
    assert evaluate(10.0, [35.0]).verdict == "unsure"        # gap 25 is not above 25
    assert evaluate(10.0, [35.1]).verdict == "proxied"


def test_minimum_against_minimum():
    # A lucky low TCP sample and a slow first echo must not create a gap: both sides
    # use their fastest value.
    r = evaluate([140.0, 60.0, 95.0], [300.0, 61.0, 150.0])
    assert r.tcp_rtt_ms == 60.0 and r.min_echo_ms == 61.0
    assert r.verdict == "direct"


def test_negative_gap_is_direct():
    assert evaluate(50.0, [10.0]).verdict == "direct"


def test_unknown_without_data():
    assert evaluate(None, [10.0]).verdict == "unknown"
    assert evaluate([], [10.0]).reason == "no TCP round trip"
    assert evaluate(5.0, []).reason == "no echoes"


def test_bad_samples_are_dropped():
    r = evaluate([0, -3, float("nan"), None, 4.0], [0, 9.0])
    assert r.tcp_rtt_ms == 4.0 and r.min_echo_ms == 9.0


def test_custom_thresholds():
    t = Thresholds(proxied=100, unsure=50)
    assert evaluate(0.5, [60.0], t).verdict == "unsure"
    with pytest.raises(ValueError):
        Thresholds(proxied=10, unsure=20)


def test_as_dict_round_trips():
    d = evaluate(2.0, [180.0]).as_dict()
    assert d["verdict"] == "proxied" and d["tcp_source"] is None and d["echoes_ms"] == [180.0]
