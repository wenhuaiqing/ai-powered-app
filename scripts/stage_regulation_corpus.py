"""Stage the NSW regulation corpus as markdown files in data/regulations/docs/.

20 hand-curated documents covering: NSW Fair Trading (agent conduct,
underquoting, disclosure), Residential Tenancies Act 2010 (bonds, notice,
rent, repairs), stamp duty (thresholds, first-home, foreign surcharge),
FIRB residential rules, and Strata Schemes Management Act basics.

Run once after cloning:
    uv run python scripts/stage_regulation_corpus.py

The output files are committed to git, so this only needs re-running when the
corpus itself changes. The build_regulation_corpus.py script then chunks and
embeds these into embeddings.parquet.

Each file uses a tiny custom frontmatter format:
    SOURCE: <publisher>
    URL: <link>
    SECTION: <human-readable section name>

    <body markdown>

Content is summarised from public NSW Government and ATO/FIRB sources for a
portfolio demo. NOT legal advice — for production use, replace with verified
extracts from legislation.nsw.gov.au, fairtrading.nsw.gov.au, etc.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "data" / "regulations" / "docs"


DOCUMENTS: list[dict[str, str]] = [
    {
        "filename": "fair-trading-agent-obligations.md",
        "source": "Fair Trading NSW",
        "url": "https://www.fairtrading.nsw.gov.au/housing-and-property/property-professionals",
        "section": "Agent obligations and conduct",
        "body": (
            "Real estate agents in NSW must hold a current Class 1 or Class 2 licence "
            "issued by NSW Fair Trading and act in their client's best interests at all "
            "times. Agents must disclose any material fact about a property that could "
            "reasonably affect a buyer's decision — including known defects, easements, "
            "and any interest the agent has in the property. The Property and Stock "
            "Agents Act 2002 requires agents to keep trust account records, deposit "
            "client money into a separate trust account within one business day, and "
            "use the standard Agency Agreement for sales (Form 6) and residential "
            "rentals.\n\n"
            "Continuing professional development (CPD) is mandatory: 3 hours of "
            "compulsory topics plus 6 hours of elective topics per licence year. "
            "Breaches can result in fines, licence suspension or disqualification by "
            "the Secretary of NSW Fair Trading."
        ),
    },
    {
        "filename": "fair-trading-underquoting.md",
        "source": "Fair Trading NSW",
        "url": "https://www.fairtrading.nsw.gov.au/housing-and-property/buying-and-selling-property/underquoting-laws",
        "section": "Underquoting laws",
        "body": (
            "Underquoting — advertising or quoting a property price below the agent's "
            "reasonable estimate or the seller's reserve — is illegal in NSW. Agents "
            "must not state an estimated selling price unless it is reasonable and "
            "based on comparable sales evidence. The Agency Agreement (Form 6) must "
            "record the agent's reasonable estimated selling price (a single figure or "
            "a price range where the highest is no more than 10% above the lowest).\n\n"
            "If a vendor sets a reserve higher than the advertised range, the agent "
            "must immediately update the advertised price. Agents are required to keep "
            "records of every price quoted and to revise their estimate within two "
            "business days of new evidence. Penalties: up to $22,000 per offence, plus "
            "forfeiture of commission. The Office of NSW Fair Trading proactively "
            "audits advertised listings."
        ),
    },
    {
        "filename": "fair-trading-disclosure.md",
        "source": "Fair Trading NSW",
        "url": "https://www.fairtrading.nsw.gov.au/housing-and-property/buying-and-selling-property",
        "section": "Vendor and agent disclosure",
        "body": (
            "Before signing a contract for sale, a vendor must attach prescribed "
            "documents under the Conveyancing (Sale of Land) Regulation 2017. These "
            "include: a copy of the title, drainage diagram, planning certificate "
            "(s10.7), and — for strata — the strata roll search. Agents must take "
            "reasonable steps to confirm these are present and current.\n\n"
            "Material facts that must be disclosed include flooding history, "
            "significant termite damage, prior use as a clandestine drug lab, and "
            "violent crime committed on the property in the last 5 years. A failure "
            "to disclose entitles the buyer to rescind the contract within the "
            "cooling-off period (5 business days for houses, none for auctions). "
            "Vendors who knowingly mislead can be liable for damages."
        ),
    },
    {
        "filename": "tenancy-bond-limits.md",
        "source": "Residential Tenancies Act 2010 (NSW)",
        "url": "https://legislation.nsw.gov.au/view/html/inforce/current/act-2010-042",
        "section": "Rental bonds",
        "body": (
            "The maximum bond a landlord can request in NSW is four weeks' rent for an "
            "ongoing residential tenancy, regardless of whether the property is "
            "furnished or unfurnished. Holiday lets and boarding houses are excluded.\n\n"
            "All bonds must be lodged with NSW Fair Trading via Rental Bonds Online "
            "(RBO) within 10 working days of receipt. Landlords or agents who fail to "
            "lodge can be fined up to $2,200. A tenant can apply to the NSW Civil and "
            "Administrative Tribunal (NCAT) to recover an unlodged bond.\n\n"
            "Claims on the bond at the end of a tenancy are made through RBO. If the "
            "parties agree on the split, the bond is refunded within two business "
            "days. If there is a dispute, either party can apply to NCAT within "
            "three months of the tenancy end."
        ),
    },
    {
        "filename": "tenancy-notice-periods.md",
        "source": "Residential Tenancies Act 2010 (NSW)",
        "url": "https://www.fairtrading.nsw.gov.au/housing-and-property/renting/ending-a-tenancy",
        "section": "Notice periods to end tenancy",
        "body": (
            "Notice periods (s84 - s90 RTA 2010) depend on who ends the tenancy and "
            "why:\n\n"
            "- Tenant ending a fixed-term tenancy without grounds: 14 days notice if "
            "  given on or after the end date, otherwise pay break-fee equal to 4 "
            "  weeks (≤25% of fixed term remaining), 3 weeks (25-50%), 2 weeks "
            "  (50-75%) or 1 week (75-100%) of rent.\n"
            "- Tenant ending a periodic tenancy: 21 days notice.\n"
            "- Landlord ending a periodic tenancy without grounds: 90 days notice "
            "  (reformed in 2024 — no-grounds termination is being phased out).\n"
            "- Landlord ending for sale of premises: 30 days notice with contract "
            "  attached.\n"
            "- Landlord ending for non-payment of rent (≥14 days arrears): 14 days "
            "  termination notice.\n"
            "- Domestic violence circumstances: tenant may end immediately, no "
            "  break-fee."
        ),
    },
    {
        "filename": "tenancy-rent-increases.md",
        "source": "Residential Tenancies Act 2010 (NSW)",
        "url": "https://www.fairtrading.nsw.gov.au/housing-and-property/renting/during-a-tenancy/rent-increases",
        "section": "Rent increases",
        "body": (
            "A landlord may increase rent in a periodic agreement no more than once "
            "every 12 months and must give the tenant at least 60 days written notice "
            "specifying the new amount and effective date. In a fixed-term agreement "
            "of less than 2 years, rent cannot be increased unless the agreement "
            "states the new amount or the calculation method.\n\n"
            "Tenants can challenge an excessive rent increase by applying to NCAT "
            "within 30 days of receiving notice. NCAT will compare the new rent to "
            "market rates for comparable premises in the area and may order a lower "
            "increase or no increase."
        ),
    },
    {
        "filename": "tenancy-repairs.md",
        "source": "Residential Tenancies Act 2010 (NSW)",
        "url": "https://www.fairtrading.nsw.gov.au/housing-and-property/renting/during-a-tenancy/repairs-and-maintenance",
        "section": "Repairs and maintenance",
        "body": (
            "Landlords must ensure the premises are reasonably clean, fit for "
            "habitation, and maintain them in a reasonable state of repair (s63 RTA "
            "2010). The 2020 minimum standards require: a structurally sound dwelling, "
            "adequate natural light and ventilation, electricity, water and gas "
            "connection, working toilet, bath or shower, kitchen with cooking "
            "facilities, and window coverings in bedrooms and living rooms.\n\n"
            "Urgent repairs (burst pipe, blocked toilet, broken hot water, dangerous "
            "electrical fault, gas leak, serious roof leak, broken fixed heater in "
            "winter) must be arranged immediately. If the landlord cannot be reached, "
            "the tenant may organise repairs up to $1,000 and be reimbursed within 14 "
            "days on production of receipts. For non-urgent repairs, tenants must "
            "give written notice and allow reasonable time."
        ),
    },
    {
        "filename": "stamp-duty-thresholds.md",
        "source": "Revenue NSW",
        "url": "https://www.revenue.nsw.gov.au/taxes-duties-levies-royalties/transfer-duty",
        "section": "Transfer duty (stamp duty) rates",
        "body": (
            "Transfer duty in NSW is calculated on a sliding scale based on the "
            "dutiable value (greater of purchase price or market value) of residential "
            "property. Approximate brackets (subject to annual indexation):\n\n"
            "- Up to $17,000: $1.25 per $100 (min $20)\n"
            "- $17,001 - $36,000: $212 + $1.50 per $100 over $17,000\n"
            "- $36,001 - $97,000: $497 + $1.75 per $100 over $36,000\n"
            "- $97,001 - $364,000: $1,564 + $3.50 per $100 over $97,000\n"
            "- $364,001 - $1,212,000: $10,909 + $4.50 per $100 over $364,000\n"
            "- $1,212,001 - $3,636,000: $49,069 + $5.50 per $100 over $1,212,000\n"
            "- Above $3,636,000 (premium): $182,389 + $7.00 per $100 over $3,636,000\n\n"
            "Worked example: on a $900,000 purchase, duty is approximately "
            "$10,909 + 4.50% × ($900,000 − $364,000) = $10,909 + $24,120 = $35,029. "
            "Duty is payable within 3 months of contract date."
        ),
    },
    {
        "filename": "stamp-duty-first-home.md",
        "source": "Revenue NSW",
        "url": "https://www.revenue.nsw.gov.au/grants-schemes/first-home-buyer/first-home-buyers-assistance-scheme",
        "section": "First Home Buyers Assistance Scheme (FHBAS)",
        "body": (
            "Eligible first home buyers in NSW receive full or partial transfer duty "
            "exemption under the First Home Buyers Assistance Scheme:\n\n"
            "- New or existing home up to $800,000: full duty exemption.\n"
            "- New or existing home $800,000 to $1,000,000: concessional rate, "
            "  tapering to zero at the threshold.\n"
            "- Vacant land up to $350,000: full exemption; $350,000 - $450,000: "
            "  concessional.\n\n"
            "Eligibility requires the buyer to be an Australian citizen or permanent "
            "resident, aged 18 or over, never previously owned residential property "
            "in Australia (including investment), and intend to occupy the home "
            "within 12 months for a minimum continuous 6 months. Joint purchasers "
            "must all qualify."
        ),
    },
    {
        "filename": "stamp-duty-foreign-surcharge.md",
        "source": "Revenue NSW",
        "url": "https://www.revenue.nsw.gov.au/taxes-duties-levies-royalties/surcharge-purchaser-duty",
        "section": "Surcharge purchaser duty (foreign buyers)",
        "body": (
            "Foreign persons acquiring residential property in NSW pay an additional "
            "8% surcharge purchaser duty on top of standard transfer duty. A foreign "
            "person is any individual who is not an Australian citizen and is not "
            "ordinarily resident in Australia (defined as physically present for at "
            "least 200 days in the preceding 12 months without immigration "
            "restrictions). Companies and trusts are foreign if a foreign person, "
            "alone or with associates, holds a substantial interest of 20% or more.\n\n"
            "The surcharge is payable in addition to FIRB approval requirements. "
            "Surcharge land tax of 4% annually also applies to foreign-owned "
            "residential land. Certain treaty-country nationals (NZ, Finland, Germany, "
            "South Africa) may be exempt from the surcharge under double-taxation "
            "agreements, subject to Revenue NSW assessment."
        ),
    },
    {
        "filename": "firb-residential.md",
        "source": "Foreign Investment Review Board (FIRB)",
        "url": "https://firb.gov.au/residential-real-estate",
        "section": "FIRB residential real estate rules",
        "body": (
            "Foreign persons must obtain FIRB approval before acquiring residential "
            "real estate in Australia. The rules differ by buyer status:\n\n"
            "- Temporary residents: may purchase one established dwelling to live in "
            "  as their principal residence; must sell within 6 months of leaving "
            "  Australia.\n"
            "- Non-residents: cannot purchase established dwellings (with very limited "
            "  exceptions). May purchase new/off-the-plan dwellings or vacant "
            "  residential land to build on (with development conditions).\n"
            "- All foreign purchases of residential land trigger FIRB application "
            "  fees, which scale with property value: ~$14,700 for properties up to "
            "  $1M, with fees increasing in $1M brackets above that.\n\n"
            "Two-year ban: from April 2025 to April 2027, foreign persons (including "
            "temporary residents) are banned from purchasing established dwellings in "
            "Australia (very narrow exceptions for certain visa holders). Breaches "
            "carry criminal penalties up to 3 years prison and civil penalties of "
            "$3.3M+ for individuals, $16.5M+ for companies."
        ),
    },
    {
        "filename": "strata-levies.md",
        "source": "Strata Schemes Management Act 2015 (NSW)",
        "url": "https://www.fairtrading.nsw.gov.au/housing-and-property/strata-and-community-living",
        "section": "Strata levies and special levies",
        "body": (
            "Owners corporations must set two annual levies at each AGM under "
            "ss79-80 of the Strata Schemes Management Act 2015:\n\n"
            "- Administrative Fund levy: covers day-to-day running costs (insurance, "
            "  utilities for common property, management fees, minor maintenance).\n"
            "- Capital Works Fund levy (formerly sinking fund): for major repairs and "
            "  capital expenditure over the 10-year capital works plan.\n\n"
            "Levies are apportioned by unit entitlement and payable quarterly unless "
            "otherwise resolved. Unpaid levies attract default interest (10% p.a. by "
            "statute unless otherwise resolved) and can be recovered in the Local "
            "Court within 6 years of the due date. Special levies for unforeseen "
            "expenses require a general meeting resolution."
        ),
    },
    {
        "filename": "strata-bylaws.md",
        "source": "Strata Schemes Management Act 2015 (NSW)",
        "url": "https://legislation.nsw.gov.au/view/html/inforce/current/act-2015-050",
        "section": "By-laws and common pet rules",
        "body": (
            "An owners corporation may make, change, or repeal by-laws by special "
            "resolution at a general meeting (75% in favour by unit entitlement). "
            "By-laws bind owners, tenants, and occupiers. They cannot be harsh, "
            "unconscionable, or oppressive, and a tribunal may revoke any by-law that "
            "is.\n\n"
            "A 2020 NSW Court of Appeal decision (Cooper v The Owners — Strata Plan "
            "No 58068) established that blanket bans on pets are oppressive and "
            "therefore invalid. Owners corporations may impose reasonable conditions "
            "(noise, leashing, common-property behaviour) but cannot prohibit "
            "outright. Refusal to permit a pet must be on reasonable grounds notified "
            "to the owner within a reasonable time."
        ),
    },
    {
        "filename": "strata-disclosure.md",
        "source": "Strata Schemes Management Act 2015 (NSW)",
        "url": "https://www.fairtrading.nsw.gov.au/housing-and-property/strata-and-community-living/buying-into-a-scheme",
        "section": "Buyer disclosure (section 184 certificate)",
        "body": (
            "Before buying into a strata scheme, a purchaser is entitled to inspect "
            "the strata roll and request a section 184 Certificate. The certificate "
            "lists the unit entitlement, current levies and arrears, balance of the "
            "administrative and capital works funds, insurance details, by-laws, "
            "minutes of recent meetings, and any current Tribunal orders.\n\n"
            "The fee for a s184 certificate is currently capped at $43.40 (CPI "
            "indexed). The owners corporation must provide the certificate within 14 "
            "days of payment. Buyers should also consider commissioning a strata "
            "search (broader review of books and records by a strata reporting "
            "company) before exchanging contracts."
        ),
    },
    {
        "filename": "tenancy-domestic-violence.md",
        "source": "Residential Tenancies Act 2010 (NSW)",
        "url": "https://www.fairtrading.nsw.gov.au/housing-and-property/renting/ending-a-tenancy/domestic-violence",
        "section": "Domestic violence termination",
        "body": (
            "Since 2019, a tenant who is a victim of domestic violence can terminate "
            "their tenancy immediately and without penalty by giving the landlord a "
            "Domestic Violence Termination Notice (s105B - s105E RTA 2010) "
            "accompanied by one of: a final apprehended domestic violence order "
            "against the perpetrator; a court order, conviction, or charge for a "
            "relevant offence; or a declaration in the prescribed form by a "
            "qualified medical practitioner.\n\n"
            "Co-tenants who are not victims continue to be liable for their share of "
            "the rent. The landlord cannot list the departing tenant on a residential "
            "tenancy database (rental blacklist) for any debt arising from the early "
            "termination. Bond claims continue under the standard process via NSW "
            "Fair Trading."
        ),
    },
    {
        "filename": "stamp-duty-off-the-plan.md",
        "source": "Revenue NSW",
        "url": "https://www.revenue.nsw.gov.au/taxes-duties-levies-royalties/transfer-duty/off-the-plan",
        "section": "Off-the-plan duty concession",
        "body": (
            "Buyers purchasing residential property off-the-plan may defer the "
            "payment of transfer duty for up to 12 months from the date of contract, "
            "or until completion, whichever is earlier. To qualify, the buyer must "
            "intend to occupy the dwelling as their principal place of residence for "
            "at least a continuous 6-month period commencing within 12 months of "
            "settlement.\n\n"
            "First home buyers acquiring off-the-plan under the FHBAS retain their "
            "concessional thresholds (full exemption up to $800,000). Investors do "
            "not qualify for the deferral. The off-the-plan concession runs alongside, "
            "not in place of, the standard duty calculation."
        ),
    },
    {
        "filename": "fair-trading-cooling-off.md",
        "source": "Fair Trading NSW",
        "url": "https://www.fairtrading.nsw.gov.au/housing-and-property/buying-and-selling-property/cooling-off-period",
        "section": "Cooling-off period",
        "body": (
            "A buyer has a statutory 5 business day cooling-off period after exchange "
            "of contracts for the sale of residential land in NSW. The buyer may "
            "rescind the contract by serving written notice of rescission on the "
            "vendor or agent during this period.\n\n"
            "If the buyer rescinds, they forfeit 0.25% of the purchase price as a "
            "termination fee. The cooling-off period does NOT apply to: sales by "
            "auction; sales to a buyer whose solicitor or conveyancer has provided a "
            "s66W certificate waiving cooling off; sales of commercial or rural "
            "land; or contracts signed on the day of an auction. The cooling-off "
            "period may be extended or shortened by written agreement."
        ),
    },
    {
        "filename": "tenancy-database-rules.md",
        "source": "Residential Tenancies Act 2010 (NSW)",
        "url": "https://www.fairtrading.nsw.gov.au/housing-and-property/renting/residential-tenancy-databases",
        "section": "Residential tenancy databases (blacklists)",
        "body": (
            "A landlord or agent may only list a former tenant on a residential "
            "tenancy database (e.g. TICA, NTD) if all three conditions are met: the "
            "tenant's tenancy has ended; the tenant has been notified in writing of "
            "the proposed listing and given at least 14 days to respond; and the "
            "listing is for a permitted reason — typically rent arrears exceeding the "
            "bond, or a Tribunal order for breach.\n\n"
            "Listings must be removed when the listed amount is paid in full, or "
            "after 3 years, whichever is earlier. Tenants have the right to know if "
            "they are listed (request copy within 14 days, no fee from the operator) "
            "and to apply to NCAT for an order requiring inaccurate or unjust "
            "listings to be removed."
        ),
    },
    {
        "filename": "tenancy-water-charges.md",
        "source": "Residential Tenancies Act 2010 (NSW)",
        "url": "https://www.fairtrading.nsw.gov.au/housing-and-property/renting/during-a-tenancy/water-usage-charges",
        "section": "Water usage charges",
        "body": (
            "Landlords may only pass on water USAGE charges (not fixed service "
            "charges) to tenants if all three conditions are met: the premises are "
            "separately metered; the premises meet the water-efficiency standards "
            "(specified maximum flow rates for showerheads, taps, dual-flush toilet "
            "cisterns); and all leaks are repaired.\n\n"
            "Bills must be passed on within 3 months of the landlord receiving the "
            "bill from the water utility. The tenant is to pay only the usage portion "
            "(measured kilolitres × rate), not the daily service availability fee. "
            "Where premises are not separately metered, no usage charge can be passed "
            "on regardless of any contrary term in the tenancy agreement."
        ),
    },
    {
        "filename": "fair-trading-trust-money.md",
        "source": "Property and Stock Agents Act 2002 (NSW)",
        "url": "https://legislation.nsw.gov.au/view/html/inforce/current/act-2002-066",
        "section": "Trust account requirements",
        "body": (
            "Licensed agents holding client money (deposits, rent collected, sale "
            "proceeds) must maintain a trust account at an authorised deposit-taking "
            "institution in NSW under section 86 of the Property and Stock Agents "
            "Act 2002. Money must be deposited intact and within one business day of "
            "receipt; agents must not draw from a trust account except as authorised "
            "by the principal or by court order.\n\n"
            "Trust accounts must be audited annually by a registered company auditor; "
            "the audit report is due 3 months after the year end (30 June). Agents "
            "must keep records of every receipt, withdrawal, and reconciliation for "
            "at least 3 years. Misappropriation is a serious offence carrying "
            "imprisonment up to 14 years and licence cancellation."
        ),
    },
]


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    written = 0
    for doc in DOCUMENTS:
        path = DOCS / doc["filename"]
        content = (
            f"SOURCE: {doc['source']}\n"
            f"URL: {doc['url']}\n"
            f"SECTION: {doc['section']}\n"
            f"\n"
            f"{doc['body']}\n"
        )
        path.write_text(content, encoding="utf-8")
        written += 1
    print(f"Wrote {written} documents to {DOCS}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"stage_regulation_corpus failed: {exc}", file=sys.stderr)
        raise
