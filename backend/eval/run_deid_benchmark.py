"""De-identification benchmark on clinical prose, by HIPAA Safe Harbor category (docs/54).

No public clinical de-identification corpus is available without a data use
agreement (i2b2/n2c2, PhysioNet), so this is a SYNTHETIC benchmark on REAL
clinical text: fictional identifiers are injected, as sentences or phrases,
into PMC-Patients case reports (already de-identified by their journals).

Held-out design. Every category has DEV templates and TEST templates (other
surface forms), and the name / place pools are disjoint between the two. The
`safe_harbor` rules were written against DEV only; TEST is what is reported.
Both halves were written by the same author (stated limitation: not an
independent annotation).

Leak = any of an injection's key strings (the value; for names each name
word; for numbers the longest digit run; for addresses the street and town)
survives in the output as a whole word. Recall = 1 - leak rate, per
category. Cost on clean text: share of untouched PMC reports altered,
placeholders per 1,000 words, and centralized dense MRR on the docs/46 PMC
task (5,000 patients, 986 queries) with the corpus de-identified.

Conditions: basic rules (docs/44 default), basic + NER (the docs/46-53
node setting), safe_harbor, safe_harbor + NER, safe_harbor + NER + the
node's registry (its own patients' and clinicians' names and record numbers;
relatives are not in a registry).

Run: python -m eval.run_deid_benchmark
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import time
from collections import Counter, defaultdict

import numpy as np

from eval.sweep import REPO_ROOT, RESULTS_DIR
from privacy.deidentify import Deidentifier, presidio_backend

CSV_PATH = REPO_ROOT / "backend" / "vendor" / "pmc_patients" / "PMC-Patients.csv"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]

POOLS = {
    "dev": {
        "first": ["Rahul", "Nimali", "Kenji", "Amelia", "Tharindu", "Fatima", "Olumide", "Sofia", "Chen", "Kavya",
                  "Dilani", "Mateo", "Hannah", "Arjun", "Zainab", "Ruwan"],
        "last": ["Menon", "Perera", "Sato", "Hart", "Jayasuriya", "Haddad", "Adeyemi", "Rossi", "Wei", "Iyer",
                 "Wickramasinghe", "Garcia", "Becker", "Sharma", "Rahman", "Bandara"],
        "town": ["Kurunegala", "Nugegoda", "Galle", "Jaffna", "Springfield", "Leeds", "Batticaloa", "Ratnapura"],
        "street": ["Temple", "Station", "Lake", "Kandy"],
        "saint": ["Mary", "John"],
        "country": ["Sri Lanka", "India"],
    },
    "test": {
        "first": ["Sachini", "Kasun", "Aisha", "Liam", "Priya", "Tomasz", "Yuki", "Gayan", "Isla", "Nadia",
                  "Chamari", "Lucas", "Hiroshi", "Ama", "Dinesh", "Thilini"],
        "last": ["Fernando", "Dissanayake", "Khan", "Walsh", "Pillai", "Nowak", "Tanaka", "Rajapaksha", "Morgan",
                 "Petrov", "Gunawardena", "Silva", "Okafor", "Kumarasinghe", "Brennan", "Herath"],
        "town": ["Matara", "Anuradhapura", "Badulla", "Trincomalee", "Manchester", "Dayton", "Puttalam", "Hambantota"],
        "street": ["Church", "Flower", "Queens", "Marine"],
        "saint": ["Luke", "Thomas"],
        "country": ["Sri Lanka", "England"],
    },
    "test2": {
        # fresh held-out set (docs/54): written after the gap fixes, run once
        "first": ["Ishara", "Nuwan", "Mei", "Oliver", "Ananya", "Kwame", "Elena", "Farhan", "Sunethra", "Diego",
                  "Ingrid", "Rohan", "Harini", "Pavel", "Chiara", "Malith"],
        "last": ["Senanayake", "Abeysekara", "Lin", "Hughes", "Krishnan", "Mensah", "Popescu", "Chowdhury",
                 "Ekanayake", "Romero", "Lindqvist", "Mehta", "Ratnayake", "Volkov", "Bianchi", "Weerasinghe"],
        "town": ["Kegalle", "Polonnaruwa", "Negombo", "Vavuniya", "Bristol", "Fresno", "Monaragala", "Chilaw"],
        "street": ["Main", "Park", "Mill", "Bauddhaloka"],
        "saint": ["Joseph", "Michael"],
        "country": ["Sri Lanka", "Wales"],
    },
}


def digits(rng, n):
    return "".join(str(rng.randint(0, 9)) for _ in range(n)).replace("0", str(rng.randint(1, 9)), 1)


def letters(rng, n):
    return "".join(rng.choice("ABCDEFGHJKLMNPRSTUVWXYZ") for _ in range(n))


def ordinal(d):
    return f"{d}{'th' if 10 <= d % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')}"


# Each template: (category, function(rng, pool) -> (text, keys)). DEV and TEST differ in surface form.
def _templates():
    def person(r, p):
        return r.choice(p["first"]), r.choice(p["last"])

    def num_keys(v):
        runs = re.findall(r"\d+", v)
        longest = max(runs, key=len) if runs else ""
        return [v] + ([longest] if len(longest) >= 4 else [])

    def date_parts(r):
        return r.randint(1, 28), r.randint(1, 12), r.randint(1995, 2023)

    T = {"dev": [], "test": [], "test2": []}

    def add(split, cat, fn):
        T[split].append((cat, fn))

    # PATIENT_NAME
    add("dev", "PATIENT_NAME", lambda r, p: (lambda f, l: (f"Patient: {f} {l}.", [f, l]))(*person(r, p)))
    add("dev", "PATIENT_NAME", lambda r, p: (lambda f, l: (f"{f} {l}, a {r.randint(20, 80)}-year-old {r.choice(['man', 'woman'])}, was admitted with chest pain.", [f, l]))(*person(r, p)))
    add("dev", "PATIENT_NAME", lambda r, p: (lambda f, l: (f"Mr. {f} {l} was reviewed in clinic.", [f, l]))(*person(r, p)))
    add("dev", "PATIENT_NAME", lambda r, p: (lambda f, l: (f"NAME: {f.upper()} {l.upper()}.", [f.upper(), l.upper()]))(*person(r, p)))
    add("dev", "PATIENT_NAME", lambda r, p: (lambda f, l: (f"Written consent was obtained from {f} {l}.", [f, l]))(*person(r, p)))
    add("test", "PATIENT_NAME", lambda r, p: (lambda f, l: (f"{f} {l} was referred by the general practitioner.", [f, l]))(*person(r, p)))
    add("test", "PATIENT_NAME", lambda r, p: (lambda f, l: (f"Patient name: {l}, {f}.", [f, l]))(*person(r, p)))
    add("test", "PATIENT_NAME", lambda r, p: (lambda f, l: (f"{f} {l} ({r.randint(20, 80)} y) presented with dyspnoea.", [f, l]))(*person(r, p)))
    add("test", "PATIENT_NAME", lambda r, p: (lambda f, l: (f"Ms. {f} {l} attended for follow-up.", [f, l]))(*person(r, p)))
    add("test", "PATIENT_NAME", lambda r, p: (lambda f, l: (f"The patient, {f} {l}, consented to publication.", [f, l]))(*person(r, p)))
    # RELATIVE
    add("dev", "RELATIVE", lambda r, p: (lambda f, l: (f"Her daughter, {f} {l}, provided the history.", [f, l]))(*person(r, p)))
    add("dev", "RELATIVE", lambda r, p: (lambda f, l: (f"He was accompanied by his wife {f}.", [f]))(*person(r, p)))
    add("test", "RELATIVE", lambda r, p: (lambda f, l: (f"His son {f} {l} was the next of kin.", [f, l]))(*person(r, p)))
    add("test", "RELATIVE", lambda r, p: (lambda f, l: (f"Collateral history was taken from the patient's sister, {f} {l}.", [f, l]))(*person(r, p)))
    # CLINICIAN
    add("dev", "CLINICIAN", lambda r, p: (lambda f, l: (f"Dr. {f} {l} performed the procedure.", [f, l]))(*person(r, p)))
    add("dev", "CLINICIAN", lambda r, p: (lambda f, l: (f"Signed: {f[0]}. {l}, MD.", [l]))(*person(r, p)))
    add("test", "CLINICIAN", lambda r, p: (lambda f, l: (f"The scan was reviewed by consultant {f} {l}.", [f, l]))(*person(r, p)))
    add("test", "CLINICIAN", lambda r, p: (lambda f, l: (f"The case was discussed with Prof. {l}.", [l]))(*person(r, p)))
    add("test", "CLINICIAN", lambda r, p: (lambda f, l: (f"{f[0]}. {l}, MBBS, reported the biopsy.", [l]))(*person(r, p)))
    # DATE (full)
    add("dev", "DATE", lambda r, p: (lambda d, m, y: (f"She was seen on {d:02d}/{m:02d}/{y}.", [f"{d:02d}/{m:02d}/{y}"]))(*date_parts(r)))
    add("dev", "DATE", lambda r, p: (lambda d, m, y: (f"Surgery took place on {d} {MONTHS[m - 1]} {y}.", [f"{d} {MONTHS[m - 1]}"]))(*date_parts(r)))
    add("dev", "DATE", lambda r, p: (lambda d, m, y: (f"He was discharged on {MONTHS[m - 1]} {d}, {y}.", [f"{MONTHS[m - 1]} {d}"]))(*date_parts(r)))
    add("test", "DATE", lambda r, p: (lambda d, m, y: (f"Admission date {y}-{m:02d}-{d:02d}.", [f"{y}-{m:02d}-{d:02d}"]))(*date_parts(r)))
    add("test", "DATE", lambda r, p: (lambda d, m, y: (f"The letter was dated {d:02d}.{m:02d}.{y}.", [f"{d:02d}.{m:02d}.{y}"]))(*date_parts(r)))
    add("test", "DATE", lambda r, p: (lambda d, m, y: (f"Symptoms began on the {ordinal(d)} of {MONTHS[m - 1]} {y}.", [f"{ordinal(d)} of {MONTHS[m - 1]}"]))(*date_parts(r)))
    # DATE without a full date: day-month, month-year (the year itself may stay)
    add("dev", "DATE_PARTIAL", lambda r, p: (lambda d, m, y: (f"She returned on {d} {MONTHS[m - 1]}.", [f"{d} {MONTHS[m - 1]}"]))(*date_parts(r)))
    add("dev", "DATE_PARTIAL", lambda r, p: (lambda d, m, y: (f"He first noticed the lump in {MONTHS[m - 1]} {y}.", [f"{MONTHS[m - 1]} {y}"]))(*date_parts(r)))
    add("dev", "DATE_PARTIAL", lambda r, p: (lambda d, m, y: (f"Bloods were repeated on {d:02d}/{m:02d}.", [f"{d:02d}/{m:02d}"]))(*date_parts(r)))
    add("test", "DATE_PARTIAL", lambda r, p: (lambda d, m, y: (f"The fever settled by {MONTHS[m - 1]} {ordinal(d)}.", [f"{MONTHS[m - 1]} {ordinal(d)}"]))(*date_parts(r)))
    add("test", "DATE_PARTIAL", lambda r, p: (lambda d, m, y: (f"She has been unwell since {MONTHS[m - 1]} {y}.", [f"{MONTHS[m - 1]} {y}"]))(*date_parts(r)))
    add("test", "DATE_PARTIAL", lambda r, p: (lambda d, m, y: (f"Biopsy {d:02d}/{m:02d}/{y % 100:02d} showed granulomas.", [f"{d:02d}/{m:02d}/{y % 100:02d}"]))(*date_parts(r)))
    # AGE over 89
    add("dev", "AGE_OVER_89", lambda r, p: (lambda a: (f"A {a}-year-old woman fell at home.", [f"{a}-year-old"]))(r.randint(90, 104)))
    add("dev", "AGE_OVER_89", lambda r, p: (lambda a: (f"The man, aged {a}, lived alone.", [f"aged {a}"]))(r.randint(90, 104)))
    add("test", "AGE_OVER_89", lambda r, p: (lambda a: (f"A {a} yo man had syncope.", [f"{a} yo"]))(r.randint(90, 104)))
    add("test", "AGE_OVER_89", lambda r, p: (lambda a: (f"This {a}-yr-old was frail.", [f"{a}-yr-old"]))(r.randint(90, 104)))
    # PHONE / FAX
    add("dev", "PHONE", lambda r, p: (lambda v: (f"Contact number +94 77 {v}.", num_keys(v)))(f"{digits(r, 3)} {digits(r, 4)}"))
    add("dev", "PHONE", lambda r, p: (lambda v: (f"Call ({v}) for results.", num_keys(v)))(f"{digits(r, 3)}) {digits(r, 3)}-{digits(r, 4)}".lstrip(")")))
    add("test", "PHONE", lambda r, p: (lambda v: (f"Her mobile is {v}.", num_keys(v)))(f"07{digits(r, 1)} {digits(r, 3)} {digits(r, 4)}"))
    add("test", "PHONE", lambda r, p: (lambda v: (f"Telephone {v}.", num_keys(v)))(f"+44 20 {digits(r, 4)} {digits(r, 4)}"))
    add("test", "PHONE", lambda r, p: (lambda v: (f"Reachable at {v} after hours.", num_keys(v)))(f"{digits(r, 3)}-{digits(r, 3)}-{digits(r, 4)}"))
    add("dev", "FAX", lambda r, p: (lambda v: (f"Fax: {v}.", num_keys(v)))(f"011 {digits(r, 3)} {digits(r, 4)}"))
    add("test", "FAX", lambda r, p: (lambda v: (f"Reports go by fax no. {v}.", num_keys(v)))(f"+94 11 {digits(r, 3)} {digits(r, 4)}"))
    # EMAIL / URL / IP
    add("dev", "EMAIL", lambda r, p: (lambda f, l: (lambda v: (f"Email {v}.", [v]))(f"{f.lower()}.{l.lower()}@gmail.com"))(*person(r, p)))
    add("test", "EMAIL", lambda r, p: (lambda f, l: (lambda v: (f"She wrote from {v} to ask.", [v]))(f"{l.lower()}{digits(r, 2)}@hospital.lk"))(*person(r, p)))
    add("dev", "URL", lambda r, p: (lambda f, l: (lambda v: (f"Photos were posted at {v}.", [v]))(f"https://facebook.com/{f.lower()}.{l.lower()}"))(*person(r, p)))
    add("test", "URL", lambda r, p: (lambda f, l: (lambda v: (f"His blog {v} described the illness.", [v]))(f"www.{f.lower()}{l.lower()}-blog.com"))(*person(r, p)))
    add("dev", "IP", lambda r, p: (lambda v: (f"The portal was accessed from {v}.", [v]))(f"192.168.{r.randint(0, 255)}.{r.randint(0, 255)}"))
    add("test", "IP", lambda r, p: (lambda v: (f"Login IP {v}.", [v]))(f"{r.randint(11, 223)}.{r.randint(0, 255)}.{r.randint(0, 255)}.{r.randint(0, 255)}"))
    # NATIONAL IDs
    add("dev", "SSN_NIC", lambda r, p: (lambda v: (f"SSN {v}.", num_keys(v)))(f"{digits(r, 3)}-{digits(r, 2)}-{digits(r, 4)}"))
    add("dev", "SSN_NIC", lambda r, p: (lambda v: (f"NIC {v}.", num_keys(v)))(f"{digits(r, 9)}V"))
    add("test", "SSN_NIC", lambda r, p: (lambda v: (f"Social security {v} on file.", num_keys(v)))(f"{digits(r, 3)}-{digits(r, 2)}-{digits(r, 4)}"))
    add("test", "SSN_NIC", lambda r, p: (lambda v: (f"Identity card {v}.", num_keys(v)))(f"{r.randint(1950, 2005)}{digits(r, 8)}"))
    # MRN
    add("dev", "MRN", lambda r, p: (lambda v: (f"MRN {v}.", num_keys(v)))(digits(r, 7)))
    add("dev", "MRN", lambda r, p: (lambda v: (f"Hospital No. {v}.", num_keys(v)))(digits(r, 7)))
    add("test", "MRN", lambda r, p: (lambda v: (f"Medical record number: {v}.", num_keys(v)))(digits(r, 8)))
    add("test", "MRN", lambda r, p: (lambda v: (f"Filed under record #{v}.", num_keys(v)))(digits(r, 7)))
    # HEALTH PLAN / ACCOUNT / LICENCE / VEHICLE / DEVICE
    add("dev", "HEALTH_PLAN", lambda r, p: (lambda v: (f"Policy No. {v}.", num_keys(v)))(f"{letters(r, 3)}-{digits(r, 8)}"))
    add("test", "HEALTH_PLAN", lambda r, p: (lambda v: (f"Insurance member ID {v}.", num_keys(v)))(f"{letters(r, 3)} {digits(r, 3)} {digits(r, 3)} {digits(r, 3)}"))
    add("test", "HEALTH_PLAN", lambda r, p: (lambda v: (f"Health plan beneficiary number {v}.", num_keys(v)))(f"{digits(r, 4)} {digits(r, 4)} {digits(r, 4)}"))
    add("dev", "ACCOUNT", lambda r, p: (lambda v: (f"Account number {v}.", num_keys(v)))(f"{digits(r, 4)} {digits(r, 4)} {digits(r, 4)}"))
    add("test", "ACCOUNT", lambda r, p: (lambda v: (f"Charges went to billing account #{v}.", num_keys(v)))(f"{letters(r, 1)}-{digits(r, 8)}"))
    add("dev", "LICENSE", lambda r, p: (lambda v: (f"Driving licence {v}.", num_keys(v)))(f"{letters(r, 1)}{digits(r, 7)}"))
    add("test", "LICENSE", lambda r, p: (lambda v: (f"Medical council registration SLMC {v}.", num_keys(v)))(digits(r, 5)))
    add("test", "LICENSE", lambda r, p: (lambda v: (f"His license no. {v} was suspended.", num_keys(v)))(f"{letters(r, 1)}{digits(r, 3)}-{digits(r, 4)}-{digits(r, 4)}"))
    add("dev", "VEHICLE", lambda r, p: (lambda v: (f"The car, number plate {v}, overturned.", num_keys(v)))(f"WP {letters(r, 3)}-{digits(r, 4)}"))
    add("test", "VEHICLE", lambda r, p: (lambda v: (f"Vehicle registration {v} was recorded.", num_keys(v)))(f"KA-{digits(r, 2)}-{letters(r, 2)}-{digits(r, 4)}"))
    add("test", "VEHICLE", lambda r, p: (lambda v: (f"VIN {v}.", num_keys(v)))(f"1HG{letters(r, 2)}{digits(r, 5)}{letters(r, 1)}{digits(r, 6)}"))
    add("dev", "DEVICE", lambda r, p: (lambda v: (f"A pacemaker, serial {v}, was implanted.", num_keys(v)))(f"{letters(r, 3)} {digits(r, 7)}"))
    add("test", "DEVICE", lambda r, p: (lambda v: (f"Pump S/N: {v}.", num_keys(v)))(f"{letters(r, 3)}-{digits(r, 5)}-X"))
    add("test", "DEVICE", lambda r, p: (lambda v: (f"The insulin pump serial number {v} was logged.", num_keys(v)))(f"{digits(r, 4)}-{digits(r, 4)}"))
    # ADDRESS / RESIDENCE / POSTCODE / INSTITUTION
    add("dev", "ADDRESS", lambda r, p: (lambda s, t: (f"Home address: {r.randint(2, 400)} {s} Road, {t}.", [f"{s} Road", t]))(r.choice(p["street"]), r.choice(p["town"])))
    add("test", "ADDRESS", lambda r, p: (lambda s, t: (f"She lives at {r.randint(2, 99)}/{r.randint(1, 9)}, {s} Mawatha, {t}.", [f"{s} Mawatha", t]))(r.choice(p["street"]), r.choice(p["town"])))
    add("test", "ADDRESS", lambda r, p: (lambda s, t: (f"Address {r.randint(2, 999)} {s} Street, {t} {digits(r, 5)}.", [f"{s} Street", t]))(r.choice(p["street"]), r.choice(p["town"])))
    add("dev", "RESIDENCE", lambda r, p: (lambda t: (f"He is a resident of {t}.", [t]))(r.choice(p["town"])))
    add("dev", "RESIDENCE", lambda r, p: (lambda t: (f"She was born in {t}.", [t]))(r.choice(p["town"])))
    add("test", "RESIDENCE", lambda r, p: (lambda t: (f"She lives in {t} with her family.", [t]))(r.choice(p["town"])))
    add("test", "RESIDENCE", lambda r, p: (lambda t: (f"He came from the village of {t}.", [t]))(r.choice(p["town"])))
    add("test", "RESIDENCE", lambda r, p: (lambda t, c: (f"He works as a farmer in {t}, {c}.", [t]))(r.choice(p["town"]), r.choice(p["country"])))
    add("test", "RESIDENCE", lambda r, p: (lambda t: (f"A fisherman from {t} was brought in.", [t]))(r.choice(p["town"])))
    add("dev", "POSTCODE", lambda r, p: (lambda v: (f"Postcode {v}.", [v]))(f"{letters(r, 2)}{r.randint(1, 9)} {r.randint(1, 9)}{letters(r, 2)}"))
    add("test", "POSTCODE", lambda r, p: (lambda v: (f"ZIP code {v}.", [v]))(digits(r, 5)))
    add("test", "POSTCODE", lambda r, p: (lambda t, v: (f"Springfield, IL {v}.", [v]))(r.choice(p["town"]), digits(r, 5)))
    add("dev", "INSTITUTION", lambda r, p: (lambda t: (f"She was admitted to {t} General Hospital.", [t]))(r.choice(p["town"])))
    add("dev", "INSTITUTION", lambda r, p: (lambda s: (f"He was transferred to St. {s}'s Medical Center.", [f"{s}'s"]))(r.choice(p["saint"])))
    add("test", "INSTITUTION", lambda r, p: (lambda t: (f"She was referred from {t} Base Hospital.", [t]))(r.choice(p["town"])))
    add("test", "INSTITUTION", lambda r, p: (lambda t: (f"He is followed at the {t} Diabetes Clinic.", [t]))(r.choice(p["town"])))
    add("test", "INSTITUTION", lambda r, p: (lambda s: (f"Imaging was done at Saint {s} Hospital.", [s]))(r.choice(p["saint"])))
    # --- test2: fresh held-out templates (new surface forms, several with no cue at all) ---
    MON3 = [m[:3] for m in MONTHS]
    add("test2", "PATIENT_NAME", lambda r, p: (lambda f, l: (f"We are grateful to {f} {l} for agreeing to share this story.", [f, l]))(*person(r, p)))
    add("test2", "PATIENT_NAME", lambda r, p: (lambda f, l: (f"Re: {f} {l}.", [f, l]))(*person(r, p)))
    add("test2", "PATIENT_NAME", lambda r, p: (lambda f, l: (f"Our patient, {f} {l}, is a schoolteacher.", [f, l]))(*person(r, p)))
    add("test2", "PATIENT_NAME", lambda r, p: (lambda f, l: (f"{f} {l} underwent a CT scan of the abdomen.", [f, l]))(*person(r, p)))
    add("test2", "PATIENT_NAME", lambda r, p: (lambda f, l: (f"{l}, {f} - date of birth withheld.", [f, l]))(*person(r, p)))
    add("test2", "RELATIVE", lambda r, p: (lambda f, l: (f"Her husband, {f} {l}, signed the consent form.", [f, l]))(*person(r, p)))
    add("test2", "RELATIVE", lambda r, p: (lambda f, l: (f"The child's mother {f} noticed the rash.", [f]))(*person(r, p)))
    add("test2", "CLINICIAN", lambda r, p: (lambda f, l: (f"Operating surgeon: {f} {l}.", [f, l]))(*person(r, p)))
    add("test2", "CLINICIAN", lambda r, p: (lambda f, l: (f"The case was reviewed with Dr {l} (radiology).", [l]))(*person(r, p)))
    add("test2", "DATE", lambda r, p: (lambda d, m, y: (f"DOB {d:02d}-{MON3[m - 1]}-{y}.", [f"{d:02d}-{MON3[m - 1]}-{y}"]))(*date_parts(r)))
    add("test2", "DATE", lambda r, p: (lambda d, m, y: (f"Seen in clinic {MONTHS[m - 1]} {d} {y}.", [f"{MONTHS[m - 1]} {d}"]))(*date_parts(r)))
    add("test2", "DATE_PARTIAL", lambda r, p: (lambda d, m, y: (f"She was seen again on the {ordinal(d)} of {MONTHS[m - 1]}.", [f"{ordinal(d)} of {MONTHS[m - 1]}"]))(*date_parts(r)))
    add("test2", "DATE_PARTIAL", lambda r, p: (lambda d, m, y: (f"The rash appeared in early {MONTHS[m - 1]} {y}.", [f"{MONTHS[m - 1]} {y}"]))(*date_parts(r)))
    add("test2", "DATE_PARTIAL", lambda r, p: (lambda d, m, y: (f"Sutures were removed on {MON3[m - 1]} {d}.", [f"{MON3[m - 1]} {d}"]))(*date_parts(r)))
    add("test2", "AGE_OVER_89", lambda r, p: (lambda a: (f"A {a}-year-old nonagenarian was assessed.", [f"{a}-year-old"]))(r.randint(90, 99)))
    add("test2", "AGE_OVER_89", lambda r, p: (lambda a: (f"She was {a} years of age.", [f"{a} years"]))(r.randint(90, 104)))
    add("test2", "PHONE", lambda r, p: (lambda v: (f"Tel: {v}.", num_keys(v)))(f"0{digits(r, 3)} {digits(r, 6)}"))
    add("test2", "PHONE", lambda r, p: (lambda v: (f"Call (+94) {v} for appointments.", num_keys(v)))(f"71 {digits(r, 3)} {digits(r, 4)}"))
    add("test2", "FAX", lambda r, p: (lambda v: (f"Fax +44 117 {v}.", num_keys(v)))(f"{digits(r, 3)} {digits(r, 4)}"))
    add("test2", "EMAIL", lambda r, p: (lambda f, l: (lambda v: (f"Reply to {v}.", [v]))(f"{f.lower()}_{l.lower()}@yahoo.co.uk"))(*person(r, p)))
    add("test2", "URL", lambda r, p: (lambda f, l: (lambda v: (f"Updates were shared on {v}.", [v]))(f"http://{l.lower()}family.org/updates"))(*person(r, p)))
    add("test2", "IP", lambda r, p: (lambda v: (f"The device reported to server address {v}.", [v]))(f"10.{r.randint(0, 255)}.{r.randint(0, 255)}.{r.randint(1, 254)}"))
    add("test2", "SSN_NIC", lambda r, p: (lambda v: (f"NIC No: {v}.", num_keys(v)))(f"{digits(r, 9)}V"))
    add("test2", "SSN_NIC", lambda r, p: (lambda v: (f"SSN: {v}.", num_keys(v)))(f"{digits(r, 3)} {digits(r, 2)} {digits(r, 4)}"))
    add("test2", "MRN", lambda r, p: (lambda v: (f"Hospital record: {v}.", num_keys(v)))(digits(r, 7)))
    add("test2", "MRN", lambda r, p: (lambda v: (f"MRN: {v}.", num_keys(v)))(f"{letters(r, 2)}{digits(r, 6)}"))
    add("test2", "MRN", lambda r, p: (lambda v: (f"Clinic file no. {v} was reopened.", num_keys(v)))(digits(r, 6)))
    add("test2", "HEALTH_PLAN", lambda r, p: (lambda v: (f"Insurance policy {v} covered the stay.", num_keys(v)))(f"{letters(r, 2)}/{digits(r, 6)}/{digits(r, 2)}"))
    add("test2", "HEALTH_PLAN", lambda r, p: (lambda v: (f"Medicaid ID {v}.", num_keys(v)))(f"{letters(r, 1)}{digits(r, 8)}"))
    add("test2", "ACCOUNT", lambda r, p: (lambda v: (f"Acct: {v}.", num_keys(v)))(digits(r, 8)))
    add("test2", "ACCOUNT", lambda r, p: (lambda v: (f"Refund to bank account {v}.", num_keys(v)))(f"{digits(r, 4)}-{digits(r, 6)}"))
    add("test2", "LICENSE", lambda r, p: (lambda v: (f"Nursing licence number {v}.", num_keys(v)))(f"RN{digits(r, 6)}"))
    add("test2", "LICENSE", lambda r, p: (lambda v: (f"DEA certificate {v}.", num_keys(v)))(f"{letters(r, 2)}{digits(r, 7)}"))
    add("test2", "VEHICLE", lambda r, p: (lambda v: (f"The registration plate {v} was noted by police.", num_keys(v)))(f"{letters(r, 2)}-{digits(r, 4)}"))
    add("test2", "VEHICLE", lambda r, p: (lambda v: (f"He was riding his motorcycle ({v}) when struck.", num_keys(v)))(f"{letters(r, 3)} {digits(r, 4)}"))
    add("test2", "DEVICE", lambda r, p: (lambda v: (f"ICD serial no. {v}.", num_keys(v)))(f"{letters(r, 3)}{digits(r, 6)}"))
    add("test2", "DEVICE", lambda r, p: (lambda v: (f"Cochlear implant SN {v}.", num_keys(v)))(digits(r, 8)))
    add("test2", "ADDRESS", lambda r, p: (lambda s_, t: (f"Address: {r.randint(2, 300)} {s_} Lane, {t}.", [f"{s_} Lane", t]))(r.choice(p["street"]), r.choice(p["town"])))
    add("test2", "ADDRESS", lambda r, p: (lambda s_, t: (f"She lives at Lot {r.randint(2, 90)}, {s_} Road, {t}.", [f"{s_} Road", t]))(r.choice(p["street"]), r.choice(p["town"])))
    add("test2", "RESIDENCE", lambda r, p: (lambda t: (f"She is a tea plucker from {t}.", [t]))(r.choice(p["town"])))
    add("test2", "RESIDENCE", lambda r, p: (lambda t: (f"A {t} resident was admitted.", [t]))(r.choice(p["town"])))
    add("test2", "RESIDENCE", lambda r, p: (lambda t: (f"He was travelling home to {t}.", [t]))(r.choice(p["town"])))
    add("test2", "RESIDENCE", lambda r, p: (lambda t: (f"They farm near {t}.", [t]))(r.choice(p["town"])))
    add("test2", "POSTCODE", lambda r, p: (lambda v: (f"Post code {v}.", [v]))(f"BS{r.randint(1, 9)} {r.randint(1, 9)}{letters(r, 2)}"))
    add("test2", "POSTCODE", lambda r, p: (lambda v: (f"Postal code {v}.", [v]))(digits(r, 5)))
    add("test2", "INSTITUTION", lambda r, p: (lambda t: (f"She was managed at the {t} Teaching Hospital.", [t]))(r.choice(p["town"])))
    add("test2", "INSTITUTION", lambda r, p: (lambda s_, t: (f"He was seen at St {s_} Hospital, {t}.", [s_, t]))(r.choice(p["saint"]), r.choice(p["town"])))
    add("test2", "INSTITUTION", lambda r, p: (lambda t: (f"Transferred from {t} District General Hospital.", [t]))(r.choice(p["town"])))
    return T


def leaked(text: str, keys: list[str]) -> bool:
    return any(re.search(rf"(?<![\w]){re.escape(k)}(?![\w])", text) for k in keys)


def inject(doc: str, rng: random.Random, split: str, templates, n: int):
    """Insert n identifiers at sentence boundaries. Returns text and [(category, keys)]."""
    sents = re.split(r"(?<=[.!?])\s+", doc)
    items = []
    tries = 0
    while len(items) < n and tries < 50:
        tries += 1
        cat, fn = rng.choice(templates[split])
        text, keys = fn(rng, POOLS[split])
        if any(leaked(doc, [k]) for k in keys):           # the base text already contains the key
            continue
        sents.insert(rng.randint(0, len(sents)), text)
        items.append((cat, keys))
    return " ".join(sents), items


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--docs", type=int, default=400, help="documents per split (dev, test)")
    parser.add_argument("--per-doc", type=int, default=6)
    parser.add_argument("--clean", type=int, default=1000, help="untouched reports for the false-positive rate")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--split", choices=["dev", "test", "both", "test2", "all"], default="all")
    parser.add_argument("--skip-retrieval", action="store_true")
    args = parser.parse_args()

    import pandas as pd

    t0 = time.perf_counter()
    df = pd.read_csv(CSV_PATH, usecols=["patient_uid", "patient"])
    rng = random.Random(args.seed)
    pool = [t for t in df["patient"].tolist() if isinstance(t, str) and 400 < len(t) < 6000]
    rng.shuffle(pool)
    base = {"dev": pool[: args.docs], "test": pool[args.docs: 2 * args.docs],
            "test2": pool[2 * args.docs + args.clean: 3 * args.docs + args.clean]}   # unused reports
    # Rules were tuned against the dev split and a DIFFERENT clean slice (the
    # end of the pool); the reported run uses the middle slice.
    clean = pool[-args.clean:] if args.split == "dev" else pool[2 * args.docs: 2 * args.docs + args.clean]
    templates = _templates()
    print(f"{len(pool)} PMC reports available; {args.docs} per split, {args.clean} clean "
          f"({time.perf_counter() - t0:.0f}s)", flush=True)

    ner = presidio_backend()
    conditions = {
        "basic": lambda reg: Deidentifier(),
        "basic + NER": lambda reg: Deidentifier(backend=ner),
        "safe_harbor": lambda reg: Deidentifier(level="safe_harbor"),
        "safe_harbor + NER": lambda reg: Deidentifier(level="safe_harbor", backend=ner),
        "safe_harbor + NER + registry": lambda reg: Deidentifier(level="safe_harbor", backend=ner, known_identifiers=reg),
    }
    rows = []
    splits = {"both": ["dev", "test"], "all": ["dev", "test", "test2"]}.get(args.split, [args.split])
    for split in splits:
        drng = random.Random(args.seed + {"dev": 0, "test": 1, "test2": 2}[split])
        docs = [inject(d, drng, split, templates, args.per_doc) for d in base[split]]
        for cname, make in conditions.items():
            tot, leak = Counter(), Counter()
            t_c = time.perf_counter()
            for text, items in docs:
                # The node's registry: its patients' and clinicians' names and record numbers.
                reg = [" ".join(keys) if cat != "MRN" else keys[0] for cat, keys in items
                       if cat in ("PATIENT_NAME", "CLINICIAN", "MRN")]
                out = make(reg).redact(text)
                for cat, keys in items:
                    tot[cat] += 1
                    leak[cat] += leaked(out, keys)
            ms = (time.perf_counter() - t_c) * 1000 / len(docs)
            overall = 1 - sum(leak.values()) / sum(tot.values())
            row = {"part": "recall", "split": split, "condition": cname, "overall_recall": overall,
                   "injected": sum(tot.values()), "ms_per_doc": ms}
            row.update({f"recall_{c}": 1 - leak[c] / tot[c] for c in sorted(tot)})
            rows.append(row)
            weak = ", ".join(f"{c} {1 - leak[c] / tot[c]:.2f}" for c in sorted(tot) if leak[c])
            print(f"  [{split}] {cname:<30} recall {overall:.3f} over {sum(tot.values())} | {ms:.0f} ms/doc | "
                  f"misses: {weak or 'none'}", flush=True)

    # Cost on clean clinical text.
    for cname, make in conditions.items():
        if "registry" in cname:
            continue
        deid = make([])
        altered, words, kept, ph = 0, 0, 0, Counter()
        for d in clean:
            out = deid.redact(d)
            altered += out != d
            words += len(d.split())
            ph.update(re.findall(r"\[([A-Z_]+)\]", out))
        rows.append({"part": "clean_cost", "condition": cname, "docs": len(clean), "docs_altered": altered / len(clean),
                     "placeholders_per_1000_words": 1000 * sum(ph.values()) / words,
                     "placeholders_by_type": json.dumps(dict(ph.most_common()))})
        print(f"  [clean] {cname:<30} altered {altered / len(clean):.3f} | "
              f"{1000 * sum(ph.values()) / words:.2f} placeholders / 1,000 words | {dict(ph.most_common(6))}", flush=True)

    if not args.skip_retrieval:
        # Retrieval cost: the docs/46 PMC task, centralized dense MRR, corpus de-identified.
        from eval.embed_cache import CachedEmbedder
        from eval.run_hyfedrag_compare import load, mrr
        from nodes.embedding import SentenceTransformerEmbedder

        corpus, queries = load(1000, 5000, 11)
        uids = list(corpus)
        bge = CachedEmbedder(SentenceTransformerEmbedder("BAAI/bge-base-en-v1.5"))
        qv = bge.embed([t for _, t, _ in queries])
        qv = qv / np.linalg.norm(qv, axis=1, keepdims=True)
        variants = {"raw": None, "basic + NER": conditions["basic + NER"]([]),
                    "safe_harbor + NER": conditions["safe_harbor + NER"]([])}
        for vname, deid in variants.items():
            texts = [corpus[u] if deid is None else deid.redact(corpus[u]) for u in uids]
            dv = bge.embed(texts)
            dv = dv / np.linalg.norm(dv, axis=1, keepdims=True)
            scores = dv @ qv.T
            m = [mrr([uids[j] for j in np.argsort(-scores[:, i])[:10]], rel) for i, (_, _, rel) in enumerate(queries)]
            rows.append({"part": "retrieval", "condition": vname, "pmc_queries": len(queries), "centralized_mrr": float(np.mean(m)),
                         "per_query_mrr": json.dumps([round(float(x), 4) for x in m])})
            print(f"  [retrieval] {vname:<24} centralized dense MRR {np.mean(m):.4f} ({time.perf_counter() - t0:.0f}s)", flush=True)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"deid_benchmark_{args.split}_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    with out.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out} ({time.perf_counter() - t0:.0f}s)")


if __name__ == "__main__":
    main()
