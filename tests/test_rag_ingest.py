from leefomgevinglab.rag import ingest


def test_html_to_text_strips_tags():
    html = "<html><body><h1>Titel</h1><p>Hallo <b>wereld</b></p><script>x=1</script></body></html>"
    txt = ingest.html_to_text(html)
    assert "Titel" in txt and "Hallo" in txt and "wereld" in txt
    assert "x=1" not in txt          # script-inhoud weg
    assert "<" not in txt            # geen tags


def test_chunk_text_overlap():
    text = "abcdefghij" * 30          # 300 tekens
    chunks = ingest.chunk_text(text, chunk_chars=100, overlap=20)
    assert len(chunks) >= 3
    assert all(len(c) <= 100 for c in chunks)
    # overlap: einde van chunk0 komt terug in begin van chunk1
    assert chunks[0][-20:] == chunks[1][:20]


def test_build_index_uses_embed_fn(monkeypatch):
    monkeypatch.setattr(ingest, "fetch_url", lambda url, timeout_s=20.0: f"<p>inhoud van {url}</p>")
    captured = {}
    def fake_embed(texts):
        captured["n"] = len(texts)
        return [[float(i), 0.0] for i in range(len(texts))]
    store = ingest.build_index(["https://iplo.nl/a"], fake_embed, chunk_chars=1000, overlap=100)
    assert store.size == captured["n"] >= 1
    assert store.chunks[0]["url"] == "https://iplo.nl/a"
    assert "inhoud" in store.chunks[0]["text"]


def test_build_index_slaat_kapotte_url_over(monkeypatch, capsys):
    """Eén onbereikbare URL mag de hele bouw niet afbreken."""
    from leefomgevinglab.connectors.base import ConnectorError

    def flaky(url, timeout_s=20.0):
        if "stuk" in url:
            raise ConnectorError(f"IPLO-pagina niet beschikbaar: {url}")
        return f"<p>inhoud van {url}</p>"

    monkeypatch.setattr(ingest, "fetch_url", flaky)
    store = ingest.build_index(
        ["https://iplo.nl/goed", "https://iplo.nl/stuk", "https://iplo.nl/ook-goed"],
        lambda texts: [[1.0, 0.0] for _ in texts],
        chunk_chars=1000, overlap=100, pogingen=1,
    )
    assert store.size == 2
    assert all("stuk" not in c["url"] for c in store.chunks)
    assert "1 van 3 URL's overgeslagen" in capsys.readouterr().err


def test_build_index_probeert_opnieuw_na_tijdelijke_fout(monkeypatch):
    """Een fout die bij de tweede poging weg is, mag geen chunks kosten."""
    from leefomgevinglab.connectors.base import ConnectorError

    pogingen = {"n": 0}

    def eenmalig_stuk(url, timeout_s=20.0):
        pogingen["n"] += 1
        if pogingen["n"] == 1:
            raise ConnectorError("tijdelijk")
        return "<p>eindelijk</p>"

    monkeypatch.setattr(ingest, "fetch_url", eenmalig_stuk)
    monkeypatch.setattr(ingest.time, "sleep", lambda s: None)
    store = ingest.build_index(["https://iplo.nl/a"], lambda t: [[1.0] for _ in t],
                               chunk_chars=1000, overlap=100)
    assert store.size == 1
    assert pogingen["n"] == 2
