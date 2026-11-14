"""SEC-12 helper: supplier names -> labels without corrupting other words."""
from app.services.snapshot_service import _scrub, name_patterns


def test_scrub_whole_words_only() -> None:
    pats = name_patterns({"Ali": "Supplier 1", "রহিম": "Supplier 2", "Karim Traders": "Supplier 3",
                          "Karim": "Supplier 4", "AB": "Supplier 5"})
    out = _scrub({"a": "Quality rice from ALI, Alimuddin paid",
                  "b": ["রহিমের দোকান থেকে, রহিম ভাই", "Karim Traders and Karim"],
                  "c": "AB store", "n": 5}, pats)
    assert out == {"a": "Quality rice from Supplier 1, Alimuddin paid",
                   "b": ["Supplier 2ের দোকান থেকে, Supplier 2 ভাই", "Supplier 3 and Supplier 4"],
                   "c": "AB store", "n": 5}
