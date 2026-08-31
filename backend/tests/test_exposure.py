from router.exposure import ExposureFactors, ExposureWeights, enforce_exposure_budget, exposure_cost


def test_exposure_cost_sums_weighted_factors():
    factors = ExposureFactors(
        sensitive_token_fraction_sent=0.5,
        query_specificity=0.5,
        probability_source_is_irrelevant=0.5,
        route_linkability=0.5,
    )
    weights = ExposureWeights(1.0, 1.0, 1.0, 1.0)
    assert exposure_cost(factors, weights) == 2.0


def test_enforce_exposure_budget_keeps_protected_sources_regardless_of_cost():
    dispatched = ["real", "decoy1", "decoy2"]
    costs = {"real": 5.0, "decoy1": 1.0, "decoy2": 1.0}
    kept = enforce_exposure_budget(dispatched, costs, exposure_budget=0.5, protected=frozenset({"real"}))
    assert "real" in kept


def test_enforce_exposure_budget_truncates_decoys_over_budget():
    dispatched = ["real", "decoy1", "decoy2", "decoy3"]
    costs = {"real": 0.0, "decoy1": 1.0, "decoy2": 1.0, "decoy3": 1.0}
    kept = enforce_exposure_budget(dispatched, costs, exposure_budget=1.5, protected=frozenset({"real"}))
    assert "real" in kept
    assert len(kept) == 2  # real + exactly one decoy fits the budget
