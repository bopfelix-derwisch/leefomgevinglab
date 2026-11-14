import pytest
from leefomgevinglab.usecases.afval import chat


def test_select_krijgt_limit():
    out = chat.valideer_sql("SELECT * FROM afval_feit")
    assert out.lower().endswith("limit 200")


def test_bestaande_limit_te_hoog_wordt_verlaagd():
    out = chat.valideer_sql("SELECT * FROM afval_feit LIMIT 9999")
    assert "200" in out and "9999" not in out


def test_stringliteral_met_limit_blijft_ongemoeid_bij_verlagen():
    """Fix 1 (taakrapport): een tekst-brede re.sub trof ook een stringliteral die toevallig op
    "limit <getal>" lijkt, waardoor de query naar iets anders zocht dan wat ze liet zien. De
    letterlijke waarde moet intact blijven; alleen de echte LIMIT-clausule wordt verlaagd."""
    out = chat.valideer_sql(
        "SELECT naam FROM afval_feit WHERE naam = 'limit 99999' LIMIT 999999")
    assert out == "SELECT naam FROM afval_feit WHERE naam = 'limit 99999' LIMIT 200"


def test_stringliteral_met_limit_en_geldige_limit_blijft_exact_gelijk():
    """Een legitieme query met een stringliteral die "limit" bevat én een LIMIT binnen de cap
    moet ongewijzigd doorgegeven worden -- geen enkele herschrijving, ook niet toevallig."""
    sql = "SELECT naam FROM afval_feit WHERE naam LIKE '%limit 50%' LIMIT 50"
    assert chat.valideer_sql(sql) == sql


def test_with_is_toegestaan():
    out = chat.valideer_sql("WITH x AS (SELECT 1 AS n) SELECT n FROM x")
    assert out.lower().startswith("with")


def test_trailing_semicolon_gestript():
    out = chat.valideer_sql("SELECT 1 AS n;")
    assert ";" not in out


@pytest.mark.parametrize("bad", [
    "DELETE FROM afval_feit",
    "DROP TABLE afval_feit",
    "INSERT INTO afval_feit VALUES (1)",
    "UPDATE afval_feit SET jaar=0",
    "ATTACH 'x.db'",
    "COPY afval_feit TO 'out.csv'",
    "PRAGMA database_list",
    "SELECT 1; DROP TABLE afval_feit",
    "CREATE TABLE t (x int)",
])
def test_gevaarlijke_sql_wordt_geweigerd(bad):
    with pytest.raises(chat.OngeldigeSQL):
        chat.valideer_sql(bad)
