"""Demo hospital federation for the studio (docs/45).

Three simulated hospitals, each holding three collections — a public
patient-leaflet collection, a research collection and restricted clinical
notes carrying FICTIONAL patient identifiers — plus three demo identities
issued by the (simulated) federation operator. It exists so every
privacy mechanism is visible in the UI in one click:

- de-identification: the clinical notes contain names, MRNs, dates of birth,
  phones and emails; nodes redact them at load (docs/44);
- role-based access: researcher reads research; clinician reads research +
  clinical notes; everyone authorised reads public (docs/45);
- role-scoped publication: restricted centroids are not in the profile;
- credential gate: each node has an allow-list with a daily budget (docs/43);
- PSI + cells: pick routing mode "psi" and decoy policy "cells" (docs/36, 40).

Every value is fictional (example.invalid, generated names). Simulated,
in-process nodes; the same code runs over real MCP (tests/test_rbac.py).
"""
from __future__ import annotations

import numpy as np

from nodes.simulator import build_simulated_source
from privacy.credentials import Authorizer, ClientPolicy, new_credential

ACCESS_POLICY = {"researcher": ["research"], "clinician": ["research", "clinical_notes"]}
IDENTITIES = {"demo-no-role": (), "demo-researcher": ("researcher",), "demo-clinician": ("clinician",)}
DAILY_BUDGET = 500

HOSPITALS = {
    "st_marys_cardiology": {
        "public": ["What to expect after a heart attack: rest, cardiac rehabilitation and medication.",
                   "Blood pressure leaflet: reduce salt, stay active and take medication as prescribed.",
                   "Chest pain: when to call emergency services and what symptoms matter.",
                   "Cholesterol explained: statins, diet and lifestyle changes for heart health.",
                   "Atrial fibrillation leaflet: irregular heartbeat, stroke risk and anticoagulants.",
                   "Heart failure self-care: daily weight checks, fluid limits and breathlessness."],
        "research": ["Randomised trial of high-intensity statins after acute coronary syndrome reduced events.",
                     "Cohort study: troponin thresholds and 30-day mortality in chest pain presentations.",
                     "Meta-analysis of beta blockers in heart failure with reduced ejection fraction.",
                     "SGLT2 inhibitors lowered heart failure hospitalisation in a multicentre trial.",
                     "Anticoagulation in atrial fibrillation: bleeding risk versus stroke prevention.",
                     "Cardiac rehabilitation attendance and readmission rates: a registry analysis."],
        "clinical_notes": ["Patient {n}, MRN {m}, DOB {d}, tel {p}: admitted with central chest pain, troponin raised, "
                           "started on dual antiplatelet therapy.",
                           "Patient {n} ({m}), email {e}: follow-up after myocardial infarction, ejection fraction 40%.",
                           "Patient {n}, MRN {m}: new atrial fibrillation, apixaban started, CHA2DS2-VASc 3.",
                           "Patient {n}, DOB {d}: decompensated heart failure, diuresed, weight down 3 kg."],
    },
    "city_general_oncology": {
        "public": ["Chemotherapy leaflet: common side effects, infection risk and when to seek help.",
                   "Breast screening explained: mammography, recalls and what results mean.",
                   "Living with cancer fatigue: pacing, exercise and support services.",
                   "Radiotherapy leaflet: skin care during treatment and follow-up appointments.",
                   "Healthy eating during cancer treatment: protein, fluids and managing nausea.",
                   "Bowel cancer screening: the home test kit and what a positive result means."],
        "research": ["Immunotherapy with checkpoint inhibitors improved survival in advanced melanoma.",
                     "Neoadjuvant chemotherapy response and outcomes in triple-negative breast cancer.",
                     "Circulating tumour DNA as an early marker of colorectal cancer recurrence.",
                     "Exercise interventions reduced chemotherapy-related fatigue in a randomised trial.",
                     "Hypofractionated radiotherapy was non-inferior for early breast cancer.",
                     "Screening uptake and stage at diagnosis in bowel cancer: a population study."],
        "clinical_notes": ["Patient {n}, MRN {m}, DOB {d}: cycle 3 of FEC chemotherapy, neutropenic, G-CSF given.",
                           "Patient {n} ({m}), tel {p}: triple-negative breast cancer, partial response on imaging.",
                           "Patient {n}, email {e}: colorectal cancer follow-up, ctDNA negative, CEA normal.",
                           "Patient {n}, MRN {m}: radiotherapy week 2, grade 1 skin reaction, emollients advised."],
    },
    "northside_nutrition": {
        "public": ["Healthy diet leaflet: vegetables, whole grains and limiting processed food.",
                   "Vitamin D: sunlight, supplements in winter and who needs them.",
                   "Weight management: portion sizes, activity and realistic goals.",
                   "Diabetes and diet: carbohydrates, glycaemic index and meal planning.",
                   "Protein on a vegetarian diet: beans, lentils, dairy and soy.",
                   "Hydration leaflet: how much water, tea and coffee count."],
        "research": ["Mediterranean diet reduced cardiovascular events in a primary prevention trial.",
                     "Vitamin D supplementation and fracture risk: a systematic review.",
                     "Low-calorie diets achieved type 2 diabetes remission in primary care.",
                     "Plant-based diets and protein adequacy in older adults: a cohort study.",
                     "Sugar-sweetened beverage taxes and population weight: an interrupted time series.",
                     "Dietary fibre intake and colorectal cancer risk: a prospective cohort."],
        "clinical_notes": ["Patient {n}, MRN {m}, DOB {d}: type 2 diabetes, HbA1c 64, referred for low-calorie diet.",
                           "Patient {n} ({m}), tel {p}: vitamin D deficiency, 25-OH D 18 nmol/L, loading dose started.",
                           "Patient {n}, email {e}: weight management review, lost 6 kg in 12 weeks.",
                           "Patient {n}, MRN {m}: coeliac disease, gluten-free diet education given."],
    },
}

_NAMES = ["Amelia Hart", "Rahul Menon", "Chen Wei", "Olumide Adeyemi", "Sofia Rossi", "Kavya Iyer",
          "Liam Walsh", "Aisha Rahman", "Mateo Garcia", "Hannah Becker", "Tomasz Nowak", "Priya Sharma"]


def _fill(template: str, i: int) -> tuple[str, str]:
    name = _NAMES[i % len(_NAMES)]
    first, last = name.split()
    return template.format(n=name, m=f"MRN {4400000 + 137 * i}", d=f"{(i % 27) + 1:02d}/0{(i % 9) + 1}/19{60 + i % 40}",
                           p=f"+44 7700 {900100 + i}", e=f"{first.lower()}.{last.lower()}@example.invalid"), name


def build_demo_federation(state) -> dict:
    """Registers the demo hospitals on `state` and issues demo identities.
    Idempotent: re-running replaces the nodes and keeps the identities."""
    if not state.demo_identities:
        state.demo_identities = {cid: new_credential(cid, roles=roles) for cid, roles in IDENTITIES.items()}
    registered = []
    for h, (node_id, spec) in enumerate(HOSPITALS.items()):
        docs, cols, registry = [], [], []
        for collection in ("public", "research", "clinical_notes"):
            for i, text in enumerate(spec[collection]):
                if collection == "clinical_notes":
                    text, name = _fill(text, 10 * h + i)
                    registry.append(name)          # the hospital's own patient index
                docs.append(text)
                cols.append(collection)
        if state.registry.get(node_id) is not None:
            state.remove_node(node_id)
        node, profile = build_simulated_source(
            node_id, docs, state.routing_embedder, k=2, sigma=0.0, rng=np.random.default_rng(h),
            collections=cols, access_policy=ACCESS_POLICY, known_identifiers=registry)
        node.authorizer = Authorizer(node_id, {cid: ClientPolicy(c.key, DAILY_BUDGET, c.roles)
                                               for cid, c in state.demo_identities.items()})
        state._publish(node_id, node, profile, state.routing_embedder.model_name)
        registered.append(node_id)
    return {"nodes": registered, "identities": list_identities(state)}


def list_identities(state) -> list[dict]:
    return [{"client_id": cid, "roles": list(c.roles)} for cid, c in state.demo_identities.items()]
