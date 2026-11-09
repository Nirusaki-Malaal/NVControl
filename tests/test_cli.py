"""Unit tests for NVControl command-line argument parser."""

import pytest
from nvcontrol.cli import build_parser
from nvcontrol.constants import VERSION


def test_parser_version():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(['--version'])


def test_parser_query():
    parser = build_parser()
    args = parser.parse_args(['-q'])
    assert args.query is True


def test_parser_status():
    parser = build_parser()
    args = parser.parse_args(['--status'])
    assert args.status is True


def test_parser_switch_modes():
    parser = build_parser()
    for mode in ['integrated', 'hybrid', 'nvidia']:
        args = parser.parse_args(['-s', mode])
        assert args.switch == mode


def test_parser_coolbits():
    parser = build_parser()
    # No coolbits
    args = parser.parse_args(['-s', 'nvidia'])
    assert args.coolbits is None

    # Flag with no value defaults to const (28)
    args = parser.parse_args(['-s', 'nvidia', '--coolbits'])
    assert args.coolbits == 28

    # Flag with explicit value
    args = parser.parse_args(['-s', 'nvidia', '--coolbits', '24'])
    assert args.coolbits == 24


def test_parser_rtd3():
    parser = build_parser()
    # Flag with no value defaults to const (2)
    args = parser.parse_args(['-s', 'hybrid', '--rtd3'])
    assert args.rtd3 == 2

    # Mode 3 (supported on Ada Lovelace and Blackwell)
    args = parser.parse_args(['-s', 'hybrid', '--rtd3', '3'])
    assert args.rtd3 == 3


def test_parser_preserve_video_memory():
    parser = build_parser()
    args = parser.parse_args(['-s', 'hybrid', '--preserve-video-memory'])
    assert args.preserve_video_memory is True


def test_parser_no_fbdev():
    parser = build_parser()
    args = parser.parse_args(['-s', 'hybrid', '--no-fbdev'])
    assert args.no_fbdev is True
