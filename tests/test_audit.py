"""Audit export gives each auditor an isolated directory, with a fixed overlap, and never the key."""

from boundary_probe import audit


def test_export_split_and_overlap(tmp_path, monkeypatch):
    src = tmp_path / "audit"
    (src / "packets").mkdir(parents=True)
    (src / "packets" / "INSTRUCTIONS.md").write_text("instructions")
    for i in range(21):
        (src / "packets" / f"P{i:06x}.md").write_text(f"packet {i}")
    (src / "key.json").write_text("{}")
    monkeypatch.setattr(audit, "AUDIT_DIR", src)
    audit.export(str(tmp_path / "out"), overlap=3)
    a1 = {p.name for p in (tmp_path / "out" / "auditor1").glob("P*.md")}
    a2 = {p.name for p in (tmp_path / "out" / "auditor2").glob("P*.md")}
    assert len(a1) == len(a2) == 12 and len(a1 & a2) == 3 and len(a1 | a2) == 21
    assert not list((tmp_path / "out").rglob("key.json"))


def test_spearman():
    assert audit._spearman([1, 2, 3, 4], [1, 3, 2, 4]) == 0.8
    assert audit._spearman([1, 1, 2, 3], [2, 2, 1, 0]) == -1.0
    assert audit._spearman([1, 2], [2, 1]) is None
