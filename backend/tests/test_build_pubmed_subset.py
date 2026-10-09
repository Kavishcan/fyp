"""PubMed XML parsing for the C-FedRAG-style corpus (eval/build_pubmed_subset.py).
No network: the E-utilities response is a fixture."""
from eval import build_pubmed_subset as b

XML = b"""<?xml version="1.0" ?>
<PubmedArticleSet>
<PubmedArticle><MedlineCitation><PMID Version="1">111</PMID><Article>
<ArticleTitle>Is <i>X</i> useful?</ArticleTitle>
<Abstract><AbstractText Label="AIMS">Find out.</AbstractText>
<AbstractText Label="CONCLUSIONS">Yes.</AbstractText></Abstract>
</Article></MedlineCitation></PubmedArticle>
<PubmedArticle><MedlineCitation><PMID Version="1">222</PMID><Article>
<ArticleTitle>No abstract here</ArticleTitle>
</Article></MedlineCitation></PubmedArticle>
<PubmedArticle><MedlineCitation><PMID Version="1">333</PMID><Article>
<ArticleTitle>Plain</ArticleTitle>
<Abstract><AbstractText>Unlabelled text.</AbstractText></Abstract>
</Article></MedlineCitation></PubmedArticle>
</PubmedArticleSet>"""


def test_efetch_keeps_labelled_sections_and_drops_empty_abstracts(monkeypatch):
    monkeypatch.setattr(b, "_get", lambda url, params: XML)
    out = b.efetch(["111", "222", "333"])
    assert set(out) == {"111", "333"}
    assert out["111"] == ("Is X useful?", "Aims: Find out. Conclusions: Yes.")
    assert out["333"] == ("Plain", "Unlabelled text.")
