import json
import numpy as np
import pytest
from nodes.document_retrieval import LocalRetrievalConfig, rerank_local
from nodes.simulator import InProcessNode
from nodes.mcp_client import MCPNodeHandle


@pytest.mark.parametrize("method,expected", [("cosine",[0,1,2,3]),("parent_cap1",[0,3,1,2]),("parent_cap2",[0,1,3,2])])
def test_soft_caps_backfill_without_dropping_chunks(method,expected):
    order=rerank_local([0,1,2,3],[.9,.8,.7,.6],np.eye(4),["a","a","a","b"],LocalRetrievalConfig(method))
    assert order.tolist()==expected


def test_mmr_avoids_redundancy_and_weight_one_reproduces_relevance():
    vectors=np.array([[1,0],[1,0],[0,1]])
    assert rerank_local([0,1,2],[1,.99,.8],vectors,None,LocalRetrievalConfig("mmr")).tolist()==[0,2,1]
    assert rerank_local([0,1,2],[1,.99,.8],vectors,None,LocalRetrievalConfig("mmr",mmr_weight=1)).tolist()==[0,1,2]


def test_tail_and_single_parent_fallback():
    assert rerank_local([0,1,2],[3,2,1],np.eye(3),["a"]*3,LocalRetrievalConfig("parent_cap1",2)).tolist()==[0,1,2]
    with pytest.raises(ValueError):
        rerank_local([0],[1],np.eye(1),None,LocalRetrievalConfig("parent_cap1"))


@pytest.mark.parametrize("kwargs",[{"method":"bad"},{"pool_size":0},{"pool_size":True},{"mmr_weight":float("nan")},{"mmr_weight":2}])
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError): LocalRetrievalConfig(**kwargs)


def test_node_pages_form_one_stable_order():
    node=InProcessNode("s",["a1","a2","b"],np.array([[1,.01],[1,.1],[.6,.8]]),
        parent_document_ids=["a","a","b"],local_retrieval=LocalRetrievalConfig("parent_cap1"))
    full=node.retrieve(np.array([1,0]),top_n=3)
    assert [p.document for p in full]==["a1","b","a2"]
    assert node.retrieve(np.array([1,0]),top_n=1,offset=1)==full[1:2]
    assert node.retrieve(np.array([1,0]),top_n=1,offset=3)==[]


def test_parent_metadata_required_at_node_creation():
    with pytest.raises(ValueError):
        InProcessNode("s",["x"],np.eye(1),local_retrieval=LocalRetrievalConfig("parent_cap1"))


def test_real_mcp_document_aware_paging(tmp_path):
    path=tmp_path/"node.json"
    path.write_text(json.dumps(dict(node_id="s",documents=["finance market", "finance market investment", "sport cricket"],
        parent_document_ids=["a","a","b"],local_retrieval={"method":"parent_cap1"})))
    handle=MCPNodeHandle(node_id="s",data_file=path)
    full=handle.retrieve_from_text("finance market",top_n=3)
    assert "sport" in full[1]["document"]
    assert handle.retrieve_from_text("finance market",top_n=1,offset=1)==full[1:2]
