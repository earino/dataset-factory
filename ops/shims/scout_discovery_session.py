#!/usr/bin/env python3
"""Deployed shim for the discovery tick. Source of truth is the repository
(`scripts/scout_research_schedule.py`); this shim supplies the discovery brief plus a rotating
regional focus, so the scheduler path stays argument-free.

The five-minute check resumes a due four-hour slot; it does not discover every five minutes.

The rotation is deterministic on the wall clock rather than random: the same tick always carries
the same region, so a report can be reproduced from its timestamp. Cron requires the job's script
to sit under the scheduler's scripts directory, hence the forward.
"""
import runpy
import sys
from datetime import datetime, timezone

TARGET = "/opt/data/dataset-factory/scripts/scout_research_schedule.py"

# Regions the routine must cover to be genuinely international. Ordered so that two consecutive
# ticks never share a region.
REGIONS = (
    ("Europe - EU/EEA", "EU agencies (Eurostat, EEA, ECDC, EFSA), national statistical offices "
                        "and sector regulators in the EU/EEA. Start with data.europa.eu."),
    ("United Kingdom", "ONS, NHS Digital, Defra, Environment Agency, Companies House, "
                       "data.gov.uk. Post-Brexit the licences are often OGL and clean."),
    ("Canada", "Statistics Canada, ECCC, Health Canada, open.canada.ca. Beware the Open "
               "Government Licence's attribution terms."),
    ("Latin America", "Brazil (dados.gov.br, INPE, DATASUS), Mexico (datos.gob.mx), Chile, "
                      "Colombia, Argentina. Portuguese/Spanish documentation is expected."),
    ("Africa", "South Africa (data.gov.za, SAPS, StatsSA), Kenya, Nigeria, Ghana, Morocco, "
               "plus African Development Bank and UNECA."),
    ("South and Southeast Asia", "India (data.gov.in, IMD, CPCB), Indonesia (BPS), Philippines "
                                 "(PSA), Thailand, Vietnam, Malaysia."),
    ("East Asia", "Japan (e-Stat, JMA), South Korea (KOSIS, KMA), Taiwan, Hong Kong, Singapore."),
    ("Oceania", "Australia (data.gov.au, ABS, BoM) and New Zealand (data.govt.nz, Stats NZ). "
                "Check each state's licence separately - several are not open."),
    ("International organisations", "World Bank, OECD, UN agencies (UNHCR, UNICEF, UNODC), WHO, "
                                    "IMF, ITU. State the publisher's own jurisdiction in the "
                                    "record; 'international' is not a country."),
)


def regional_focus(moment=None):
    """Pick this tick's region from the clock, stable for any given tick."""
    moment = moment or datetime.now(timezone.utc)
    tick = (moment.timetuple().tm_yday * 6) + (moment.hour // 4)
    return REGIONS[tick % len(REGIONS)]


if __name__ == "__main__":
    region, detail = regional_focus()
    extra = (
        f"REGIONAL FOCUS FOR THIS TICK: {region}. Prioritize this region: {detail} "
        "Choose probes for decision value, not a verdict quota. If the region yields nothing "
        "viable, report the coverage and evidence; do not pad it with familiar US sources."
    )
    # Existing 90-minute / 120-iteration ceiling; the brief reserves time for close-out.
    sys.argv = ([TARGET, "--role", "discovery", "--prompt-file", "docs/discovery-session-prompt.md", "--extra", extra,
                 "--run-budget", "5400", "--max-turns", "120"]
                + sys.argv[1:])
    runpy.run_path(TARGET, run_name="__main__")
