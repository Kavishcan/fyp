from eval.instrument import Instrumentation, QueryLog


def test_instrumentation_round_trips_query_log(tmp_path):
    log_path = tmp_path / "queries.jsonl"
    instrumentation = Instrumentation(log_path)
    log = QueryLog(
        query_id="q1",
        topic_key="oncology",
        coarse_candidate_ids=["a", "b", "c"],
        genuine_source_ids=["a"],
        dispatched_source_ids=["a", "b"],
    )
    instrumentation.record(log)

    records = instrumentation.read_all()
    assert len(records) == 1
    assert records[0]["query_id"] == "q1"
    assert records[0]["dispatched_source_ids"] == ["a", "b"]


def test_query_log_decoy_source_ids_excludes_genuine():
    log = QueryLog(
        query_id="q1",
        topic_key="oncology",
        genuine_source_ids=["a"],
        dispatched_source_ids=["a", "b", "c"],
    )
    assert log.decoy_source_ids == ["b", "c"]


def test_instrumentation_appends_across_multiple_records(tmp_path):
    log_path = tmp_path / "queries.jsonl"
    instrumentation = Instrumentation(log_path)
    instrumentation.record(QueryLog(query_id="q1", topic_key="t"))
    instrumentation.record(QueryLog(query_id="q2", topic_key="t"))
    assert len(instrumentation.read_all()) == 2
