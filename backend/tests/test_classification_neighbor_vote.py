from learning_os.classification.neighbor_vote import classify_by_neighbor_vote
from learning_os.config import get_settings


def write_vault(tmp_path, files: dict[str, str]):
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def test_classifies_by_clear_plurality_among_neighbors(tmp_path, monkeypatch):
    write_vault(
        tmp_path,
        {
            "Switch.md": "---\ndomain: networking\n---\nswitch content.",
            "Firewall.md": "---\ndomain: networking\n---\nfirewall content.",
            "Modem.md": "---\ndomain: networking\n---\nmodem content.",
            "Router.md": "Connects to [[Switch]], [[Firewall]], and [[Modem]].",
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    results = classify_by_neighbor_vote(min_votes=3)

    assert len(results) == 1
    assert results[0].note_title == "Router"
    assert results[0].domain == "networking"
    assert results[0].confidence == 1.0


def test_no_classification_on_a_tie(tmp_path, monkeypatch):
    write_vault(
        tmp_path,
        {
            "A1.md": "---\ndomain: alpha\n---\na1 content.",
            "A2.md": "---\ndomain: alpha\n---\na2 content.",
            "B1.md": "---\ndomain: beta\n---\nb1 content.",
            "B2.md": "---\ndomain: beta\n---\nb2 content.",
            "Ambiguous.md": "Related to [[A1]], [[A2]], [[B1]], and [[B2]].",
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    results = classify_by_neighbor_vote(min_votes=2)

    assert results == []


def test_below_min_votes_is_excluded(tmp_path, monkeypatch):
    write_vault(
        tmp_path,
        {
            "C1.md": "---\ndomain: gamma\n---\nc1 content.",
            "C2.md": "---\ndomain: gamma\n---\nc2 content.",
            "TooFewVotes.md": "Related to [[C1]] and [[C2]].",
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    assert classify_by_neighbor_vote(min_votes=3) == []

    results = classify_by_neighbor_vote(min_votes=2)
    assert len(results) == 1
    assert results[0].note_title == "TooFewVotes"
    assert results[0].domain == "gamma"


def test_excluded_class_domain_neighbor_does_not_count_as_a_vote(tmp_path, monkeypatch):
    write_vault(
        tmp_path,
        {
            "D1.md": "---\ndomain: delta\n---\nd1 content.",
            "D2.md": "---\ndomain: delta\n---\nd2 content.",
            "D3.md": "---\ndomain: delta\n---\nd3 content.",
            "Meta.md": "a cross-cutting note.\n#transconcept",
            "Target.md": "Related to [[D1]], [[D2]], [[D3]], and [[Meta]].",
        },
    )
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    results = classify_by_neighbor_vote(min_votes=3)

    assert len(results) == 1
    assert results[0].note_title == "Target"
    assert results[0].domain == "delta"
    assert results[0].confidence == 1.0  # 3/3, "Meta" excluded from both numerator and denominator


def test_no_neighbors_is_left_unclassified(tmp_path, monkeypatch):
    write_vault(tmp_path, {"Isolated.md": "no links, no frontmatter, no tag."})
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    assert classify_by_neighbor_vote() == []
