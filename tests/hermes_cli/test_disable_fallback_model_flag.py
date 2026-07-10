from __future__ import annotations


def test_chat_parser_accepts_disable_fallback_model_for_paperclip_contract() -> None:
    from hermes_cli._parser import build_top_level_parser

    parser, _subparsers, chat_parser = build_top_level_parser()
    chat_parser.set_defaults(func=lambda _args: None)

    args = parser.parse_args(
        [
            "chat",
            "-Q",
            "-q",
            "run adapter task",
            "--source",
            "paperclip",
            "--disable-fallback-model",
        ]
    )

    assert args.command == "chat"
    assert args.quiet is True
    assert args.source == "paperclip"
    assert args.disable_fallback_model is True
