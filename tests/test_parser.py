from parser import clean_content, parse_command


# ─── clean_content ─────────────────────────────────────────────────────────

def test_clean_strips_simple_tags():
    assert clean_content("<p>hello world</p>") == "hello world"


def test_clean_strips_h_card_mention_span():
    html = (
        '<p><span class="h-card"><a href="https://x.test/@bot" class="u-url mention">'
        '@<span>bot</span></a></span> the dude</p>'
    )
    assert clean_content(html) == "the dude"


def test_clean_strips_multiple_mentions():
    html = (
        '<p><span class="h-card"><a href="x">@<span>vinz</span></a></span> '
        '<span class="h-card"><a href="y">@<span>bot</span></a></span> '
        'happy cat</p>'
    )
    assert clean_content(html) == "happy cat"


def test_clean_handles_html_entities():
    assert clean_content("<p>hello &amp; goodbye</p>") == "hello & goodbye"


def test_clean_collapses_whitespace():
    assert clean_content("<p>foo\n\n   bar</p>") == "foo bar"


def test_clean_falls_back_to_at_regex_when_no_h_card():
    assert clean_content("@bot hello there") == "hello there"


# ─── parse_command ─────────────────────────────────────────────────────────

def test_parse_search():
    assert parse_command("the dude") == ("search", "the dude")


def test_parse_shuffle():
    assert parse_command("shuffle") == ("shuffle", "")
    assert parse_command("Shuffle") == ("shuffle", "")
    assert parse_command("random") == ("shuffle", "")


def test_parse_next():
    assert parse_command("next") == ("next", "")
    assert parse_command("NEXT") == ("next", "")


def test_parse_send_default_index():
    assert parse_command("send") == ("send", "1")


def test_parse_send_with_index():
    assert parse_command("send 3") == ("send", "3")


def test_parse_block():
    assert parse_command("block") == ("block", "")


def test_parse_cancel():
    assert parse_command("cancel") == ("cancel", "")


def test_parse_empty():
    assert parse_command("") == ("empty", "")
    assert parse_command("   ") == ("empty", "")


def test_parse_multiword_keyword_is_search():
    assert parse_command("happy excited dog") == ("search", "happy excited dog")


def test_parse_keyword_starting_with_send_word_is_search():
    assert parse_command("sending love") == ("search", "sending love")
