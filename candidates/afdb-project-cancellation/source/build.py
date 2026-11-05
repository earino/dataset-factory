#!/usr/bin/env python3
"""AfDB operation-cancellation panel construction (job afdb-build-001).

Candidate: afdb-project-cancellation. This script ONLY constructs the runner-layout
artifact and the diagnostics the qualification gate recomputes. NO performance
metric of any kind is computed here - no AUC, no accuracy, no rate presented as a
finding; the reference stage (score.py) runs only after the gate passes on the
full artifact and --accept re-verifies the exact bytes (run.sh enforces the order).

Task: at the board-approval instant of an African Development Bank Group
operation (IATI activity-date type 1, the planned start the publisher records
at approval), using only at-approval attributes, predict whether the operation
ultimately terminates CANCELLED (IATI activity-status 5) rather than COMPLETED
(status 3). Terminal statuses only; statuses 1 (Approved) and 2 (Ongoing) are
right-censored and never scored.

Population (pre-registered in the candidate record 2026-11-05, before any score):
  * source vintage: the 57 afdb.org IATI XML registry files, pinned by sha256 in
    PINNED_SHA256 (measured by worker probe afdb-panel-probe-001, 2026-11-05,
    57/57 HTTP 200 from the Hetzner worker, 164.5 MiB in 7.2 s). A file that
    hashes differently, or a registry with a different dataset set, refuses the
    build - vintage drift is never silently absorbed.
  * scored rows: statuses 3/5 with a type-1 (approval) date, approval year
    1967..2023 (the earliest measured approval is 1967; 2024+ approvals are 4
    terminal rows with 0 positives, excluded as a cohort boundary and counted).
  * splits (pre-registered, temporal on approval year): train <=2000,
    eval 2001-2011, holdout 2012-2023. The eval end was extended from 2010 to
    2011 BEFORE any score because the original window carried 29 positives, one
    short of the gate's 30 minimum (recorded in the candidate record).
  * event/cluster key: country_or_region x approval year (13 positive rows carry
    no recipient-country; they resolve to recipient-region, else MULTINATIONAL).
  * label: status 5 -> 1, status 3 -> 0. The label source (activity-status) is
    NOT among the shipped columns; its absence is asserted.

Shipped columns (runner contract: every non-target column is model input):
  iati_identifier (id), approval_date (the prediction instant; time column),
  country_or_region, sector_code (IATI vocabulary 1), finance_type
  (default-finance-type), commitment_xdr (sum of iati:budget value elements
  with budget@type=1, the original budget; 0.0 when absent), planned_span_days
  (type-3 planned end minus type-1 approval, in days; -1 sentinel with
  planned_end_missing=1 when type 3 is absent - 38 terminal rows measured),
  planned_end_missing, era (approval decade), event_key
  (country_or_region|approval_year, the declared cluster key), cancelled.

Timing posture (declared, current-vintage retrospective): the registry files are
re-published in full, so only the CURRENT vintage exists. Features are the
current-vintage values of attributes the publisher records at approval; no
historical point-in-time availability is claimed anywhere. The type-3 planned
end is the current-vintage plan (revision-contaminated; measured 4/32 completed
operations overran it), stated in quality.json limitations. Retrospective
research only - never an operational historical forecasting claim.

Hard anchors (measured by afdb-panel-probe-001 on the pinned vintage) are
asserted exactly: population totals, the per-year terminal/positive/censored
table, split row and positive counts. A mismatch fails the build loudly rather
than shipping a different dataset than the one the record describes.

Licence: CC BY 4.0 (license_id cc-by on all 57 IATI Registry dataset records for
publisher afdb, re-verified from the worker 2026-11-05; also stated on
MapAfrica's data-product modal). Attribution "African Development Bank Group"
carries to any release; the dataset is derived research, never AfDB's official
product. Stdlib only. No credentials in the container.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

NAME = "afdb-project-cancellation"
TARGET = "cancelled"
POSITIVE_LABEL = 1
ID_COLUMN = "iati_identifier"
TIME_COLUMN = "approval_date"
EVENT_KEY_COLUMN = "event_key"

COLUMNS = [ID_COLUMN, TIME_COLUMN, "country_or_region", "sector_code",
           "finance_type", "commitment_xdr", "planned_span_days",
           "planned_end_missing", "era", EVENT_KEY_COLUMN, TARGET]
FEATURES = COLUMNS[1:-1]

TRAIN_END_YEAR = 2000          # train: approval years <= 2000
EVAL_START_YEAR = 2001
EVAL_END_YEAR = 2011
HOLDOUT_START_YEAR = 2012
HOLDOUT_END_YEAR = 2023
LAST_SCORED_YEAR = 2023

# Registry inventory (58th dataset would refuse); URLs measured by the probe.
SOURCE_URLS = {
 "afdb-algeria": "https://www.afdb.org/sites/default/files/iati/iatialgeriadata.xml",
 "afdb-angola": "https://www.afdb.org/sites/default/files/iati/iatiangoladata.xml",
 "afdb-benin": "https://www.afdb.org/sites/default/files/iati/iatibenindata.xml",
 "afdb-botswana": "https://www.afdb.org/sites/default/files/iati/iatibotswanadata.xml",
 "afdb-burkinafaso": "https://www.afdb.org/sites/default/files/iati/iatiburkinafasodata.xml",
 "afdb-burundi": "https://www.afdb.org/sites/default/files/iati/iatiburundidata.xml",
 "afdb-cameroon": "https://www.afdb.org/sites/default/files/iati/iaticameroondata.xml",
 "afdb-capeverde": "https://www.afdb.org/sites/default/files/iati/iaticapeverdedata.xml",
 "afdb-centralafricanrepublic": "https://www.afdb.org/sites/default/files/iati/iaticardata.xml",
 "afdb-chad": "https://www.afdb.org/sites/default/files/iati/iatichaddata.xml",
 "afdb-ci": "https://www.afdb.org/sites/default/files/iati/iaticotedivoiredata.xml",
 "afdb-comoros": "https://www.afdb.org/sites/default/files/iati/iaticomorosdata.xml",
 "afdb-congo": "https://www.afdb.org/sites/default/files/iati/iaticongodata.xml",
 "afdb-djibouti": "https://www.afdb.org/sites/default/files/iati/iatidjiboutidata.xml",
 "afdb-drc": "https://www.afdb.org/sites/default/files/iati/iatidrcdata.xml",
 "afdb-egypt": "https://www.afdb.org/sites/default/files/iati/iatiegyptdata.xml",
 "afdb-equatorialguinea": "https://www.afdb.org/sites/default/files/iati/iatiequatorialguineadata.xml",
 "afdb-eritrea": "https://www.afdb.org/sites/default/files/iati/iatieritreadata.xml",
 "afdb-ethiopia": "https://www.afdb.org/sites/default/files/iati/iatiethiopiadata.xml",
 "afdb-gabon": "https://www.afdb.org/sites/default/files/iati/iatigabondata.xml",
 "afdb-gambia": "https://www.afdb.org/sites/default/files/iati/iatigambiadata.xml",
 "afdb-ghana": "https://www.afdb.org/sites/default/files/iati/iatighanadata.xml",
 "afdb-guinea": "https://www.afdb.org/sites/default/files/iati/iatiguineadata.xml",
 "afdb-guineabissau": "https://www.afdb.org/sites/default/files/iati/iatiguineabissaudata.xml",
 "afdb-kenya": "https://www.afdb.org/sites/default/files/iati/iatikenyadata.xml",
 "afdb-lesotho": "https://www.afdb.org/sites/default/files/iati/iatilesothodata.xml",
 "afdb-liberia": "https://www.afdb.org/sites/default/files/iati/iatiliberiadata.xml",
 "afdb-madagascar": "https://www.afdb.org/sites/default/files/iati/iatimadagascardata.xml",
 "afdb-malawi": "https://www.afdb.org/sites/default/files/iati/iatimalawidata.xml",
 "afdb-mali": "https://www.afdb.org/sites/default/files/iati/iatimalidata.xml",
 "afdb-mauritania": "https://www.afdb.org/sites/default/files/iati/iatimauritaniadata.xml",
 "afdb-mauritius": "https://www.afdb.org/sites/default/files/iati/iatimauritiusdata.xml",
 "afdb-morocco": "https://www.afdb.org/sites/default/files/iati/iatimoroccodata.xml",
 "afdb-mozambique": "https://www.afdb.org/sites/default/files/iati/iatimozambiquedata.xml",
 "afdb-multinational": "https://www.afdb.org/sites/default/files/iati/iatimultinationaldata.xml",
 "afdb-namibia": "https://www.afdb.org/sites/default/files/iati/iatinamibiadata.xml",
 "afdb-niger": "https://www.afdb.org/sites/default/files/iati/iatinigerdata.xml",
 "afdb-nigeria": "https://www.afdb.org/sites/default/files/iati/iatinigeriadata.xml",
 "afdb-nonsovereign": "https://www.afdb.org/sites/default/files/iati/iatinonsovereignprojectsdata.xml",
 "afdb-org": "https://www.afdb.org/sites/default/files/iati/iatiorganisationdata.xml",
 "afdb-rwanda": "https://www.afdb.org/sites/default/files/iati/iatirwandadata.xml",
 "afdb-saotome": "https://www.afdb.org/sites/default/files/iati/iatisaotomeandprincipedata.xml",
 "afdb-senegal": "https://www.afdb.org/sites/default/files/iati/iatisenegaldata.xml",
 "afdb-seychelles": "https://www.afdb.org/sites/default/files/iati/iatiseychellesdata.xml",
 "afdb-sierraleone": "https://www.afdb.org/sites/default/files/iati/iatisierraleonedata.xml",
 "afdb-somalia": "https://www.afdb.org/sites/default/files/iati/iatisomaliadata.xml",
 "afdb-southafrica": "https://www.afdb.org/sites/default/files/iati/iatisouthafricadata.xml",
 "afdb-southsudan": "https://www.afdb.org/sites/default/files/iati/iatisouthsudandata.xml",
 "afdb-sudan": "https://www.afdb.org/sites/default/files/iati/iatisudandata.xml",
 "afdb-swaziland": "https://www.afdb.org/sites/default/files/iati/iatiswazilanddata.xml",
 "afdb-tanzania": "https://www.afdb.org/sites/default/files/iati/iatitanzaniadata.xml",
 "afdb-togo": "https://www.afdb.org/sites/default/files/iati/iatitogodata.xml",
 "afdb-tunisia": "https://www.afdb.org/sites/default/files/iati/iatitunisiadata.xml",
 "afdb-uganda": "https://www.afdb.org/sites/default/files/iati/iatiugandadata.xml",
 "afdb-zambia": "https://www.afdb.org/sites/default/files/iati/iatizambiadata.xml",
 "afdb-zimbabwe": "https://www.afdb.org/sites/default/files/iati/iatizimbabwedata.xml",
 "libya": "https://www.afdb.org/sites/default/files/iati/iatilibyadata.xml"
}

# Source vintage pin: the build refuses any file whose digest differs.
PINNED_SHA256 = {
 "afdb-algeria": "7817d83c692f0429b08539818933ca6a13232ae213f13595568235fe415d098f",
 "afdb-angola": "fdf3453887c377137bb7f1e6cacbcb467389967f1235e99315f2c59aea348051",
 "afdb-benin": "dda51b4f887f3f0b70ed7edcefeed1bc17be4506a4f427f90b77f02aa7434f32",
 "afdb-botswana": "47621e12c4ea542495eb3399fdd9b0b107dd948ce8f19a3889a370ed7f3ac0ec",
 "afdb-burkinafaso": "8612ff1cb150c4531cfddfd55fce56890f515c7803b85d3dea0d6698d18a44a0",
 "afdb-burundi": "25e01a74446eaa7ded061eeadaca386d1005100e271c82d338486a19263a4328",
 "afdb-cameroon": "9beb672f5100bc02f7575b968940493307ced12d98563937e8f63ac0a4b24545",
 "afdb-capeverde": "6248fb13753dd9f24b26c594be740145d0d14f496f2e46d55a4b8bbaa803aec5",
 "afdb-centralafricanrepublic": "c3dec5b9324ba09d6837b736493c821007bf31964187c36ca72a3b2941c24152",
 "afdb-chad": "68d6fa049b8897a8a01d8410e6445de072bcc50e6046aee9e1b2d39e9a29e990",
 "afdb-ci": "4cb2d695c903a12b4aab61dd7769bca7192e7ea890ca3b6bb3111ea6ec6bd631",
 "afdb-comoros": "3ac02657ca88f5251c33d531978bbfcf20c4806f3a1ffb3eaf15ab61a0723d50",
 "afdb-congo": "c31470a8599c3ca541b60a0f2cb209778e434cbd986672c5393abf6a7c2d7df8",
 "afdb-djibouti": "ffa49df2652d78459f820cd2985d3b5d5d817fb84f0899b1fef20cd76b9fcb14",
 "afdb-drc": "47fa6ca3a791a1c67e1581030d8e09aeb1e5d5f2698418b952c6451bb1d72337",
 "afdb-egypt": "5b00daa0ef71c65d74ce1835557a11c6d8316bb9fd6caced8e1b60ee7c140845",
 "afdb-equatorialguinea": "1b03c2c986815108036cfb4040a82b941906b210c3ec4da76aae07c6b7f41080",
 "afdb-eritrea": "427904f7b6cc3ada375b68aa757625c96b560aa28a3e2a94e2517551f29f0c87",
 "afdb-ethiopia": "050dccd55561347ee7e62b676b5538087989211093723bab4784aa0829adf0dc",
 "afdb-gabon": "3edececd2866cb30482e74ea00cc989b2f90f17726f4fdb0195bf8d7c9077e6c",
 "afdb-gambia": "7013425aa66c9842fee8583fa7324af63b3379c0d24b30abacc7b29a25cac8d8",
 "afdb-ghana": "4241c1574cfa72ecf788b22e0a75bed44783efa67c2677aed3e59b3d44c2f75e",
 "afdb-guinea": "45f8926370670278b506089bde4fd920b6a5ed6135e144925915e2d2c43b6aef",
 "afdb-guineabissau": "efd6737a1c251808dd4f44753f701ac6886ae85e4a5a88614c12a7d6e2fdb2fa",
 "afdb-kenya": "6bd14e3d76892da8a3ffea320754ee50ab6fb92f952c3195812a103a10e7a3ac",
 "afdb-lesotho": "b59d4c5003caa8cabce6f7b3c826b996605b930ab05d3328625d5e619f8645bd",
 "afdb-liberia": "279afa59b00800ff19905a5cfc05176012515771c6191de95b7c625dc26260ff",
 "afdb-madagascar": "e86d41e1b491f37e854a9d9d1c7b82e97165bd82499f465d6f28911c575931ea",
 "afdb-malawi": "68fb70b487f1c6607f814f0ce63d754c30c0868fa45a14b9993720b76322c699",
 "afdb-mali": "ee1667c1820ea4b730e48085ca114b5f323544187aa61723a8e9ddf31b9116a0",
 "afdb-mauritania": "d8e148d59b0dfb5622e072e9239294e763ead433333e7144b6256271b7f45c05",
 "afdb-mauritius": "6fd1817ed8e7da70236b06db5ad6ce84d88f89a1cb8bb938bac8d75e88dc2a22",
 "afdb-morocco": "dc12f7f27869bc3abac1fa6478e9351264db311cc5513c7c1de681cf4b91fae6",
 "afdb-mozambique": "fb1fe6ac28a35706b4c834d52d9d998e45b4d53556900045c915430364300039",
 "afdb-multinational": "01fe1be370d5caf8a0b551fed0e9d1525ccf1bbf67765ae50da72d5d557d04f9",
 "afdb-namibia": "531798b9a2f7abded37467889d688743e1d69bae7f008094d6fe001d636fa194",
 "afdb-niger": "8f248318a1d65cd729c4b1665138aafecb6f4ac69075e257b8d5ee7e5a3ff46e",
 "afdb-nigeria": "b722a1c4dfc1f51d3161f34053add05bd0c6d4f23a264e3dfd9e344263a1677d",
 "afdb-nonsovereign": "e21b38e32903cce47ce3fbff14a4c902cca3ad736e76dc2b73e164824015522d",
 "afdb-org": "5e234b740518a9d9903848de99db6bafbbf289215ee5a9d296a1782612997801",
 "afdb-rwanda": "e2e6fcce07b1c298f3b41893a7153df73995b7d8612e5880b6ea251cb0a00e30",
 "afdb-saotome": "4f6111c50929f75834fcba9fb1efee66bc89f4d45979595592d03c9d36ed9a44",
 "afdb-senegal": "bfbe8cd63b76990b0bc33fa8dc9b7c6a3188d0b4532c880c103dfc542ab18412",
 "afdb-seychelles": "3f362364ec3307f54b9005e9bf8201b72340fec33a9af5054e74fea0188b6208",
 "afdb-sierraleone": "33c14bd11955a3dc7f368e08a5e4c3714f2facedde929bb41375954b76776222",
 "afdb-somalia": "3c357b7cd8641011eccd556876d973b428451469b2c81d6509cecf52a12ce1ec",
 "afdb-southafrica": "2e8c1efa162887cc62f698b0aafdc79401d128c8910bbad2c316985359f227fd",
 "afdb-southsudan": "ed5b75d9ab8ef8d784ba87022d69a4eb7e64235f26e959644f6b34ab90add40a",
 "afdb-sudan": "7e8e48a4de36a705e24e26c0d1542237f2b2722a3360b4d2788f7618b2cae8f5",
 "afdb-swaziland": "df8276bb3c2f3695423447bd6f7adce2559b0f08c04ee92e3c843b6141031f15",
 "afdb-tanzania": "f93dca1f09ac37a7818760e41c8f1b4cf461bb55421ae6bcaba2b041bf13a23d",
 "afdb-togo": "d9ca40210fd172f37eec72ddb64e5be405aedea0fb8e8cd0b83735a784e8ca46",
 "afdb-tunisia": "0c41f6e97fb4edca984c8ccd62a621e7582d40e1e78ccbaeb2d8e3c239523d00",
 "afdb-uganda": "a4f0865b4a575e56995a9c5d810e0d6b7f3a87e6f419f607e3d378df9b1f520e",
 "afdb-zambia": "dd0bee76c45eb2fa1369e51c95022db93cc06f8274ef757b29e8a20a05665718",
 "afdb-zimbabwe": "cf16c47115d9746a21025fd529730705fad84e654d6f0b4b85ae43c482ff51e5",
 "libya": "a806e7d132c6386a63fcaa4127dd65c8e915e24fd3a83cee2db656ff106938dd"
}

# Per-approval-year anchors measured on the pinned vintage by the probe
# (term = statuses 3+5, pos = status 5, cens = statuses 1+2).
YEAR_ANCHORS = {
 "1967": {
  "cens": 0,
  "pos": 0,
  "term": 1
 },
 "1968": {
  "cens": 0,
  "pos": 0,
  "term": 2
 },
 "1969": {
  "cens": 0,
  "pos": 1,
  "term": 4
 },
 "1970": {
  "cens": 0,
  "pos": 0,
  "term": 6
 },
 "1971": {
  "cens": 0,
  "pos": 0,
  "term": 10
 },
 "1972": {
  "cens": 0,
  "pos": 1,
  "term": 16
 },
 "1973": {
  "cens": 0,
  "pos": 0,
  "term": 14
 },
 "1974": {
  "cens": 0,
  "pos": 0,
  "term": 39
 },
 "1975": {
  "cens": 0,
  "pos": 3,
  "term": 42
 },
 "1976": {
  "cens": 0,
  "pos": 2,
  "term": 37
 },
 "1977": {
  "cens": 0,
  "pos": 3,
  "term": 49
 },
 "1978": {
  "cens": 0,
  "pos": 0,
  "term": 62
 },
 "1979": {
  "cens": 0,
  "pos": 5,
  "term": 53
 },
 "1980": {
  "cens": 0,
  "pos": 0,
  "term": 51
 },
 "1981": {
  "cens": 0,
  "pos": 5,
  "term": 61
 },
 "1982": {
  "cens": 0,
  "pos": 5,
  "term": 56
 },
 "1983": {
  "cens": 0,
  "pos": 4,
  "term": 62
 },
 "1984": {
  "cens": 0,
  "pos": 6,
  "term": 65
 },
 "1985": {
  "cens": 0,
  "pos": 7,
  "term": 70
 },
 "1986": {
  "cens": 0,
  "pos": 3,
  "term": 71
 },
 "1987": {
  "cens": 0,
  "pos": 4,
  "term": 80
 },
 "1988": {
  "cens": 0,
  "pos": 2,
  "term": 67
 },
 "1989": {
  "cens": 0,
  "pos": 8,
  "term": 105
 },
 "1990": {
  "cens": 0,
  "pos": 8,
  "term": 109
 },
 "1991": {
  "cens": 0,
  "pos": 7,
  "term": 130
 },
 "1992": {
  "cens": 0,
  "pos": 9,
  "term": 103
 },
 "1993": {
  "cens": 0,
  "pos": 13,
  "term": 121
 },
 "1994": {
  "cens": 0,
  "pos": 1,
  "term": 19
 },
 "1995": {
  "cens": 0,
  "pos": 1,
  "term": 7
 },
 "1996": {
  "cens": 0,
  "pos": 1,
  "term": 24
 },
 "1997": {
  "cens": 0,
  "pos": 8,
  "term": 89
 },
 "1998": {
  "cens": 0,
  "pos": 6,
  "term": 107
 },
 "1999": {
  "cens": 0,
  "pos": 4,
  "term": 55
 },
 "2000": {
  "cens": 0,
  "pos": 4,
  "term": 84
 },
 "2001": {
  "cens": 0,
  "pos": 7,
  "term": 97
 },
 "2002": {
  "cens": 0,
  "pos": 6,
  "term": 88
 },
 "2003": {
  "cens": 0,
  "pos": 2,
  "term": 88
 },
 "2004": {
  "cens": 0,
  "pos": 1,
  "term": 107
 },
 "2005": {
  "cens": 0,
  "pos": 1,
  "term": 66
 },
 "2006": {
  "cens": 0,
  "pos": 2,
  "term": 108
 },
 "2007": {
  "cens": 1,
  "pos": 0,
  "term": 80
 },
 "2008": {
  "cens": 2,
  "pos": 0,
  "term": 92
 },
 "2009": {
  "cens": 2,
  "pos": 6,
  "term": 148
 },
 "2010": {
  "cens": 0,
  "pos": 4,
  "term": 111
 },
 "2011": {
  "cens": 0,
  "pos": 3,
  "term": 141
 },
 "2012": {
  "cens": 6,
  "pos": 3,
  "term": 110
 },
 "2013": {
  "cens": 7,
  "pos": 6,
  "term": 182
 },
 "2014": {
  "cens": 12,
  "pos": 2,
  "term": 136
 },
 "2015": {
  "cens": 29,
  "pos": 6,
  "term": 123
 },
 "2016": {
  "cens": 33,
  "pos": 2,
  "term": 131
 },
 "2017": {
  "cens": 40,
  "pos": 5,
  "term": 92
 },
 "2018": {
  "cens": 73,
  "pos": 3,
  "term": 69
 },
 "2019": {
  "cens": 88,
  "pos": 7,
  "term": 71
 },
 "2020": {
  "cens": 43,
  "pos": 0,
  "term": 90
 },
 "2021": {
  "cens": 109,
  "pos": 1,
  "term": 25
 },
 "2022": {
  "cens": 150,
  "pos": 1,
  "term": 42
 },
 "2023": {
  "cens": 142,
  "pos": 2,
  "term": 16
 },
 "2024": {
  "cens": 150,
  "pos": 0,
  "term": 3
 },
 "2025": {
  "cens": 131,
  "pos": 0,
  "term": 1
 },
 "2026": {
  "cens": 82,
  "pos": 0,
  "term": 0
 }
}

ANCHORS = {
    "activities_total": 5188,
    "duplicate_identifiers": 0,
    "status_histogram": {"1": 281, "2": 819, "3": 3897, "5": 191},
    "terminal_rows": 4088,
    "terminal_missing_type1": 0,
    "splits": {"train": {"rows": 1871, "positives": 121},
               "eval": {"rows": 1126, "positives": 32},
               "holdout": {"rows": 1087, "positives": 38}},
    "excluded_2024plus_terminal": 4,
    "excluded_2024plus_positives": 0,
    "censored_excluded": 1100,
    "eval_positive_cells_lower": 27,
    "holdout_positive_cells_lower": 31,
}

FETCH_TIMEOUT_S = 60
FETCH_RETRIES = 3
USER_AGENT = "dataset-factory-construction/1.0 (+afdb-project-cancellation build)"


def fail(message: str) -> None:
    print(f"BUILD REFUSED: {message}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(url: str, to_path: Path, timeout: int = FETCH_TIMEOUT_S) -> dict:
    last = None
    for attempt in range(1, FETCH_RETRIES + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                to_path.unlink(missing_ok=True)
                with to_path.open("wb") as handle:
                    total = 0
                    while True:
                        chunk = response.read(1 << 20)
                        if not chunk:
                            break
                        handle.write(chunk)
                        total += len(chunk)
                return {"url": url, "status": response.status, "bytes": total,
                        "attempt": attempt}
        except Exception as exc:  # noqa: BLE001 - a blocked channel is a measurement
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(2 * attempt)
    return {"url": url, "status": None, "error": last,
            "attempt": FETCH_RETRIES}


def parse_iso(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def parse_activities(path: Path) -> list[dict]:
    """Stream one registry XML file; per-activity at-approval fields only."""
    rows = []
    for _, element in ET.iterparse(str(path), events=("end",)):
        if element.tag != "iati-activity":
            continue
        ident = (element.findtext("iati-identifier") or "").strip()
        status = None
        node = element.find("activity-status")
        if node is not None:
            status = node.get("code")
        dates = {}
        for node in element.findall("activity-date"):
            dates[node.get("type")] = node.get("iso-date")
        countries = [c.get("code") for c in element.findall("recipient-country")
                     if c.get("code")]
        regions = [r.get("code") for r in element.findall("recipient-region")
                   if r.get("code")]
        sector = None
        for node in element.findall("sector"):
            if node.get("vocabulary") == "1" and node.get("code"):
                sector = node.get("code")
                break
        finance = None
        node = element.find("default-finance-type")
        if node is not None:
            finance = node.get("code")
        commitment = 0.0
        has_budget = False
        for budget in element.findall("budget"):
            if budget.get("type") != "1":
                continue
            for value in budget.findall("value"):
                try:
                    commitment += float((value.text or "").strip())
                    has_budget = True
                except ValueError:
                    pass
        rows.append({
            "id": ident,
            "status": status,
            "type1": dates.get("1"),
            "type2": dates.get("2"),
            "type3": dates.get("3"),
            "type4": dates.get("4"),
            "country": countries[0] if countries else None,
            "n_countries": len(countries),
            "region": regions[0] if regions else None,
            "sector": sector,
            "finance": finance,
            "commitment": round(commitment, 2),
            "has_budget": has_budget,
        })
        element.clear()
    return rows


def split_of(year: int):
    if year <= TRAIN_END_YEAR:
        return "train"
    if EVAL_START_YEAR <= year <= EVAL_END_YEAR:
        return "eval"
    if HOLDOUT_START_YEAR <= year <= HOLDOUT_END_YEAR:
        return "holdout"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--work-dir", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    work = Path(args.work_dir)
    (out / "public").mkdir(parents=True, exist_ok=True)
    (out / "private").mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)

    # ---- 1. fetch the pinned vintage, refusing any digest drift ------------------
    receipts = []
    for dataset in sorted(SOURCE_URLS):
        target = work / f"{dataset}.xml"
        step = fetch(SOURCE_URLS[dataset], target)
        step["dataset"] = dataset
        if step.get("status") != 200:
            fail(f"source fetch failed for {dataset}: {step.get('error') or step.get('status')}")
        digest = sha256_of(target)
        step["sha256"] = digest
        step["pin_match"] = digest == PINNED_SHA256[dataset]
        receipts.append(step)
        if not step["pin_match"]:
            fail(f"vintage pin mismatch for {dataset}: {digest} != "
                 f"{PINNED_SHA256[dataset]}")
    print(f"fetched {len(receipts)}/57 pinned files, all digests match", flush=True)

    # ---- 2. parse the panel ------------------------------------------------------
    activities = []
    for step in receipts:
        activities.extend(parse_activities(work / f"{step['dataset']}.xml"))
    identifiers = [a["id"] for a in activities]
    duplicates = len(identifiers) - len(set(identifiers))
    from collections import Counter
    histogram = Counter(a["status"] for a in activities)
    if len(activities) != ANCHORS["activities_total"]:
        fail(f"activities_total {len(activities)} != {ANCHORS['activities_total']}")
    if duplicates != ANCHORS["duplicate_identifiers"]:
        fail(f"duplicate identifiers {duplicates} != 0")
    if dict(histogram) != ANCHORS["status_histogram"]:
        fail(f"status histogram {dict(histogram)} != {ANCHORS['status_histogram']}")

    # ---- 3. population, exclusions and per-year anchors -------------------------
    terminal = [a for a in activities if a["status"] in ("3", "5")]
    censored = [a for a in activities if a["status"] in ("1", "2")]
    if len(terminal) != ANCHORS["terminal_rows"]:
        fail(f"terminal rows {len(terminal)} != {ANCHORS['terminal_rows']}")
    if len(censored) != ANCHORS["censored_excluded"]:
        fail(f"censored rows {len(censored)} != {ANCHORS['censored_excluded']}")
    if sum(1 for a in terminal if not a["type1"]) != ANCHORS["terminal_missing_type1"]:
        fail("terminal rows without a type-1 (approval) date exist")
    for a in terminal:
        if a["type1"] and parse_iso(a["type1"]) is None:
            fail(f"terminal row {a['id']} carries an unparseable type-1 date "
                 f"{a['type1']!r}")

    measured_years = {}
    for a in activities:
        day = parse_iso(a["type1"]) if a["type1"] else None
        if a["type1"] and day is None:
            fail(f"activity {a['id']} carries an unparseable type-1 date {a['type1']!r}")
        year = day.year if day else None
        key = str(year) if year is not None else "missing_type1"
        bucket = measured_years.setdefault(key, {"term": 0, "pos": 0, "cens": 0})
        if a["status"] in ("3", "5"):
            bucket["term"] += 1
            bucket["pos"] += int(a["status"] == "5")
        else:
            bucket["cens"] += 1
    if measured_years != YEAR_ANCHORS:
        differing = {key: (measured_years.get(key), YEAR_ANCHORS.get(key))
                     for key in set(measured_years) | set(YEAR_ANCHORS)
                     if measured_years.get(key) != YEAR_ANCHORS.get(key)}
        fail(f"per-approval-year anchors drifted: {differing}")
    if "missing_type1" in measured_years:
        fail("activities without a type-1 date exist")

    scored = []
    excluded_2024 = {"rows": 0, "positives": 0}
    for a in terminal:
        day = parse_iso(a["type1"])
        year = day.year
        label = 1 if a["status"] == "5" else 0
        if year > LAST_SCORED_YEAR:
            excluded_2024["rows"] += 1
            excluded_2024["positives"] += label
            continue
        if split_of(year) is None:
            fail(f"approval year {year} outside every declared window")
        scored.append((a, day, label))
    if excluded_2024 != {"rows": ANCHORS["excluded_2024plus_terminal"],
                         "positives": ANCHORS["excluded_2024plus_positives"]}:
        fail(f"2024+ exclusions {excluded_2024} disagree with the anchor")

    # ---- 4. rows, splits and hard split anchors ----------------------------------
    split_rows = {"train": [], "eval": [], "holdout": []}
    no_country = {"rows": 0, "positives": 0, "with_region": 0}
    for a, day, label in scored:
        country_or_region = a["country"] or a["region"] or "MULTINATIONAL"
        if a["country"] is None:
            no_country["rows"] += 1
            no_country["positives"] += label
            no_country["with_region"] += int(a["region"] is not None)
        end = parse_iso(a["type3"])
        span = (end - day).days if end is not None else -1
        row = {
            ID_COLUMN: a["id"],
            TIME_COLUMN: day.isoformat(),
            "country_or_region": country_or_region,
            "sector_code": a["sector"] or "NONE",
            "finance_type": a["finance"] or "NONE",
            "commitment_xdr": a["commitment"],
            "planned_span_days": span,
            "planned_end_missing": 0 if end is not None else 1,
            "era": f"{(day.year // 10) * 10}s",
            EVENT_KEY_COLUMN: f"{country_or_region}|{day.year}",
            TARGET: label,
        }
        split_rows[split_of(day.year)].append(row)

    counts = {}
    for key, rows in split_rows.items():
        positives = sum(r[TARGET] for r in rows)
        counts[key] = {"rows": len(rows), "positives": positives}
        anchor = ANCHORS["splits"][key]
        if counts[key] != anchor:
            fail(f"split {key} measured {counts[key]} != pre-registered {anchor}")
        cells = {r[EVENT_KEY_COLUMN] for r in rows if r[TARGET] == 1}
        counts[key]["positive_cells"] = len(cells)
        counts[key]["positive_rate"] = round(positives / len(rows), 6) if rows else None
        rows.sort(key=lambda r: (r[TIME_COLUMN], r[ID_COLUMN]))
    if counts["eval"]["positive_cells"] < ANCHORS["eval_positive_cells_lower"]:
        fail(f"eval positive cells {counts['eval']['positive_cells']} below the "
             f"recorded lower bound {ANCHORS['eval_positive_cells_lower']}")
    if counts["holdout"]["positive_cells"] < ANCHORS["holdout_positive_cells_lower"]:
        fail(f"holdout positive cells {counts['holdout']['positive_cells']} below the "
             f"recorded lower bound {ANCHORS['holdout_positive_cells_lower']}")
    print(f"splits: {json.dumps(counts)}", flush=True)

    # ---- 5. write the artifact ----------------------------------------------------
    paths = {"train": out / "public" / "train.csv",
             "eval": out / "public" / "eval.csv",
             "holdout": out / "private" / "holdout.csv"}
    for key, path in paths.items():
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
            writer.writeheader()
            for row in split_rows[key]:
                writer.writerow(row)

    meta = {
        "name": NAME,
        "target": TARGET,
        "positive_label": POSITIVE_LABEL,
        "id_columns": [ID_COLUMN],
        "columns": COLUMNS,
        "rows": {key: counts[key]["rows"] for key in ("train", "eval", "holdout")},
        "positive_rate": {key: counts[key]["positive_rate"]
                          for key in ("train", "eval", "holdout")},
        "split_description": (
            "temporal split on the board-approval instant (IATI activity-date type 1): "
            "train approvals 1967-2000, eval 2001-2011, holdout 2012-2023; "
            "terminal AfDB operations only (activity-status 3 Completed / 5 Cancelled); "
            "right-censored statuses 1/2 (1,100 rows, all approvals >=2007) and 2024+ "
            "approvals (4 terminal rows, 0 positives) are excluded and counted"),
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")

    # label source must be structurally absent from the shipped files
    assert "activity_status" not in COLUMNS and "status" not in COLUMNS

    quality = QUALITY_JSON.copy()
    quality["positive_events"] = {
        key: {"positives": counts[key]["positives"],
              "distinct_events": counts[key]["positive_cells"]}
        for key in ("train", "eval", "holdout")}
    quality["split_windows"] = {
        "train": {"start": "1967-01-01", "end": f"{EVAL_START_YEAR}-01-01"},
        "eval": {"start": f"{EVAL_START_YEAR}-01-01", "end": f"{HOLDOUT_START_YEAR}-01-01"},
        "holdout": {"start": f"{HOLDOUT_START_YEAR}-01-01",
                    "end": f"{LAST_SCORED_YEAR + 1}-01-01"},
    }
    quality["evaluation_contract"]["feature_evidence"] = FE_EVIDENCE.copy()
    (out / "quality.json").write_text(json.dumps(quality, indent=1) + "\n")

    # ---- 6. bounded diagnostics (no performance metric) ----------------------------
    per_split_year = {}
    for key, rows in split_rows.items():
        table = {}
        for row in rows:
            year = row[TIME_COLUMN][:4]
            bucket = table.setdefault(year, {"rows": 0, "positives": 0})
            bucket["rows"] += 1
            bucket["positives"] += row[TARGET]
        per_split_year[key] = table
    censored_by_year = {}
    for a in censored:
        day = parse_iso(a["type1"])
        if day:
            censored_by_year[str(day.year)] = censored_by_year.get(str(day.year), 0) + 1

    summary = {
        "job": "afdb-build-001",
        "name": NAME,
        "source_vintage": {
            "files": len(receipts),
            "pin_matches": sum(1 for r in receipts if r["pin_match"]),
            "bytes": sum(r["bytes"] for r in receipts),
            "registry_urls": len(SOURCE_URLS),
        },
        "population": {
            "activities_total": len(activities),
            "duplicate_identifiers": duplicates,
            "status_histogram": dict(histogram),
            "terminal_rows": len(terminal),
            "terminal_missing_type1": sum(1 for a in terminal if not a["type1"]),
            "terminal_missing_type3": sum(1 for a in terminal if not a["type3"]),
            "cancelled_with_actual_end": sum(1 for a in terminal
                                             if a["status"] == "5" and a["type4"]),
            "censored_excluded": len(censored),
            "censored_by_approval_year": censored_by_year,
            "excluded_2024plus": excluded_2024,
        },
        "splits": counts,
        "per_split_per_year": per_split_year,
        "feature_diagnostics": {
            "no_recipient_country_rows": no_country,
            "multinational_rows": sum(1 for a in terminal if a["n_countries"] > 1),
            "sector_none_rows": sum(1 for a in terminal if not a["sector"]),
            "finance_none_rows": sum(1 for a in terminal if not a["finance"]),
            "no_budget_rows": sum(1 for a in terminal if not a["has_budget"]),
            "planned_end_missing_rows": sum(1 for a in terminal if not a["type3"]),
            "countries": len({(a["country"] or a["region"] or "MULTINATIONAL")
                              for a in terminal}),
            "sectors": len({a["sector"] for a in terminal if a["sector"]}),
            "finance_types": len({a["finance"] for a in terminal if a["finance"]}),
        },
        "anchors_verified": {
            "activities_total": True, "per_year_table": True,
            "split_counts": {k: v["positives"] for k, v in ANCHORS["splits"].items()},
            "note": "every anchor asserted exactly; the build refuses on drift",
        },
        "no_metric_computed": ("no AUC, accuracy or rate-vs-label performance number "
                               "is computed anywhere in this build; score.py runs "
                               "only after the gate passes and --accept re-verifies"),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({"splits": counts, "no_country": no_country,
                      "files": {key: str(path.relative_to(out))
                                for key, path in paths.items()}}), flush=True)
    return 0


QUALITY_JSON = {
 "name": "afdb-project-cancellation",
 "target": "cancelled",
 "positive_label": 1,
 "id_columns": [
  "iati_identifier"
 ],
 "features": [
  "approval_date",
  "country_or_region",
  "sector_code",
  "finance_type",
  "commitment_xdr",
  "planned_span_days",
  "planned_end_missing",
  "era",
  "event_key"
 ],
 "high_cardinality_columns": [
  "approval_date",
  "event_key"
 ],
 "carry_columns": [],
 "splits": {
  "train": "public/train.csv",
  "eval": "public/eval.csv",
  "holdout": "private/holdout.csv"
 },
 "time_column": "approval_date",
 "event_key_column": "event_key",
 "expected_duplicate_ids": 0,
 "id_columns_are_entity_keys": True,
 "external_threshold": False,
 "features_documented_at": "prediction_time",
 "label_source_columns": [
  "activity_status"
 ],
 "post_hoc_columns": [
  "actual_start_date",
  "actual_end_date",
  "activity_status"
 ],
 "task": {
  "prediction_time": "the board-approval instant: IATI activity-date type 1 (planned start) in AfDB's IATI activity files, the date the operation enters the published record",
  "target_definition": "terminal activity-status 5 (Cancelled) = 1 vs 3 (Completed) = 0, observed at the current registry vintage's coverage end",
  "description": "at approval, using only at-approval attributes (country/region, sector, financing instrument, commitment, planned span, era), predict whether the AfDB operation is ultimately cancelled"
 },
 "measurements": [
  {
   "column": "commitment_xdr",
   "unit": "XDR (IMF special drawing rights accounting units)",
   "frame": "sum of iati:budget/value where budget@type=1 (original) in the current registry vintage; 0.0 when the activity carries no budget element"
  },
  {
   "column": "planned_span_days",
   "unit": "days",
   "frame": "current-vintage activity-date type 3 (planned end) minus type 1 (approval); -1 sentinel with planned_end_missing=1 when type 3 is absent (38 terminal rows measured on the pinned vintage)"
  }
 ],
 "timing": {
  "prediction_instant": {
   "kind": "event_time",
   "period": "D",
   "days_after_period_end": 0,
   "citation": "AfDB IATI activity files, activity-date type 1; registry https://iatiregistry.org/api/3/action/package_search?fq=organization:afdb (57 datasets, cc-by); the type-1 date is present on 100% of terminal rows (measured, probe afdb-panel-probe-001 2026-11-05)"
  },
  "features": {
   "period": "D",
   "published_days_after_period_end": 0,
   "source_kind": "administrative_record"
  },
  "row_selection": {
   "latest_period_used": "2023",
   "fields": [
    "approval_date",
    "country_or_region",
    "sector_code",
    "finance_type",
    "commitment_xdr",
    "planned_span_days",
    "era"
   ],
   "basis": "scored rows are terminal operations (status 3 or 5 in the current registry vintage) approved 1967..2023; right-censored statuses 1/2 (1,100 rows, all approvals >=2007) and 2024+ approvals (4 terminal rows, 0 positives) are excluded and counted; the exclusions are outcome-observability and cohort-boundary rules and never read the label value"
  },
  "observations": []
 },
 "evaluation_contract": {
  "use": "retrospective_research",
  "access": "isolated_rows",
  "training_label_timing": "unverified",
  "scope_note": "each row is one AfDB operation whose features are at-approval record attributes; the runner predicts row-wise from the shipped columns. Labeled eval is development/validation; the holdout is the final test and stays outside evaluated agents' workspaces. Training-label timing is UNVERIFIED: the terminal status resolves years after the approval instant and the registry publishes no historical as-of ledger, so no full-row availability ledger can be constructed - retrospective research only, never a certified historical forecasting setup",
  "vintage": {
   "kind": "current_snapshot",
   "evidence": "the 57 afdb.org IATI registry files are re-published in full (iati-activities generated-datetime 2026-10-29 on the pinned vintage; every file fetched 2026-11-05 and pinned by sha256 in the build). No historical vintages are kept by the publisher, so no as-of slice exists; every shipped feature is the current-vintage value of an attribute recorded at approval. The MapAfrica channel is not used for the population (its 230 cancelled rows are a larger, different population; the registry's 191 cancelled agree exactly with the community datastore's 191 - reconciliation recorded in the candidate record 2026-11-05)"
  },
  "selection": {
   "kind": "prediction_time",
   "evidence": "membership is fixed by the approval instant (approval year 1967..2023) and terminal-status observability at the current snapshot: statuses 1/2 are right-censored and excluded (1,100 rows, all approvals >=2007, counted per year in summary.json; their planned ends are overwhelmingly >2026 - 0 censored rows have planned end <=2015 - so the pre-2007 scored era carries an empty censoring backlog). This is an outcome-observability exclusion that never reads the label value, mirroring the maturity censoring in the wb-loan family precedent; both label values are retained in every window. 2024+ approvals (4 terminal rows, 0 positives) are excluded as a cohort boundary"
  },
  "limitations": [
   "current_snapshot vintage: features are current-vintage values of attributes documented as set at approval; no historical point-in-time availability is claimed",
   "planned_span_days uses the current-vintage planned end, which the publisher revises (4/32 measured completed operations overran it), so it is revision-contaminated",
   "outcome-observability selection: recent approval years are scored only on operations that resolved by the snapshot, so the holdout's recent years under-represent slow, still-ongoing operations (1,100 censored rows, all approvals >=2007, counted per year)",
   "training_label_timing is unverified: no as-of ledger exists for when each terminal status was first published",
   "positives cluster by country-or-region and approval year; the independent positive evidence is the declared positive_cells count, not the row count",
   "labeled eval is development/validation, never an untouched final test; the holdout is the final test and remains sealed until the design is frozen"
  ],
  "cross_row_audit": {
   "probes": [],
   "probes_note": "no generic probe applies, reviewed per docs/PREDICTION-CONTRACT.md: the generic machinery donates a later row's shipped feature to an earlier row's label, and every shipped feature is a static at-approval attribute of the operation itself (identity, geography, sector, instrument, commitment, planned span, era) - no later row's feature encodes any earlier row's outcome, so the donation has nothing to expose. The reverse-direction exposure - an earlier operation's terminal status readable through a join - is eliminated by construction: the label source (activity-status) is absent from the shipped columns (asserted), no aggregate or history feature ships, and iati-identifier is unique across the whole panel (0 duplicates measured), so no row can carry another row's outcome",
   "rationale": "rows are one-shot operation outcomes with no panel self-answering structure: the label is the terminal activity-status, excludable and excluded from the shipped columns, and no shipped column is another row's outcome. Reference trailing rates (country, sector x decade) are computed by score.py from train rows only after acceptance - they are not shipped columns. Access is isolated_rows",
   "auxiliary_files_review": "the extract ships exactly the runner layout - public/train.csv, public/eval.csv, private/holdout.csv, meta.json, quality.json - plus summary.json, which carries counts and anchors only, no row-level data and no performance metric. The fetched registry XML files stay in the job's scratch directory outside /output and are never uploaded"
  }
 }
}

FE_EVIDENCE = {
 "iati_identifier": {
  "source": "iati-identifier element in the AfDB IATI registry XML",
  "availability": "the operation's own record identity, assigned when the operation enters the published record at approval",
  "status": "verified"
 },
 "approval_date": {
  "source": "activity-date type 1 (planned start) in the AfDB IATI registry XML",
  "availability": "the prediction instant itself; present on 100% of terminal rows (measured 2026-11-05, probe afdb-panel-probe-001); the record's own MapAfrica display-offset sample (P-KE-KF0-013: UI 23 Sept 2026 vs planned_start 2026-09-24) treats the type-1 date as the approval instant, an explicitly assumed ~1-day display offset",
  "status": "verified"
 },
 "country_or_region": {
  "source": "first recipient-country code, else first recipient-region code, else MULTINATIONAL",
  "availability": "recipient geography recorded when the operation enters the record",
  "status": "assumed",
  "assumption": "current-vintage registry value of an attribute documented as fixed at approval; no as-of reconstruction performed"
 },
 "sector_code": {
  "source": "sector@code with IATI vocabulary 1 in the registry XML",
  "availability": "sector classification recorded at approval",
  "status": "assumed",
  "assumption": "current-vintage value of a static approval attribute"
 },
 "finance_type": {
  "source": "default-finance-type@code in the registry XML",
  "availability": "financing instrument recorded at approval",
  "status": "assumed",
  "assumption": "current-vintage value of a static approval attribute"
 },
 "commitment_xdr": {
  "source": "sum of budget/value elements with budget@type=1 (original budget) in the registry XML",
  "availability": "the original approved budget recorded at approval; 0.0 when the activity carries no budget element (counted in summary.json)",
  "status": "assumed",
  "assumption": "current-vintage value of the at-approval budget; unit XDR (IMF accounting units) declared in measurements"
 },
 "planned_span_days": {
  "source": "activity-date type 3 (planned end) minus type 1 (approval), in days",
  "availability": "the approved plan's span, recorded at approval",
  "status": "assumed",
  "assumption": "the type-3 date in the current vintage is the plan as revised to date: measured 4/32 completed Sao Tome operations overran their planned end, so the current-vintage value is revision-contaminated and no as-of value is claimed; -1 sentinel with planned_end_missing=1 when type 3 is absent (38 terminal rows measured)"
 },
 "planned_end_missing": {
  "source": "derived: 1 when activity-date type 3 is absent, else 0",
  "availability": "availability flag of the planned-end attribute, knowable at approval as 'the record carries no planned end'",
  "status": "assumed"
 },
 "era": {
  "source": "derived arithmetically from approval_date (approval decade, e.g. 1980s)",
  "availability": "the prediction instant's own decade",
  "status": "verified"
 },
 "event_key": {
  "source": "derived: country_or_region + approval year (the declared cluster key)",
  "availability": "derived only from shipped at-approval columns",
  "status": "verified"
 }
}


if __name__ == "__main__":
    raise SystemExit(main())
