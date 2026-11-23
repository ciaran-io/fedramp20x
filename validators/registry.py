"""Maps KSI IDs to their automated validation methods.

To add coverage for another KSI: write two methods in methods.py (ideally one
static, one live), then register them here. KSIs with no entry are reported as
`not_implemented` rather than silently passing.
"""
from . import methods as m
from . import methods_tech as t
from . import methods_ops as o
from . import methods_grc as g
from . import methods_cover as c

KSI_METHODS = {
    "KSI-CNA-RNT": [m.rnt_static, m.rnt_live],
    "KSI-CNA-EIS": [m.eis_static, m.eis_live, c.eis_remediation],
    "KSI-IAM-APM": [m.apm_static, m.apm_live],
    "KSI-IAM-ELP": [m.elp_static, m.elp_live],
    "KSI-SVC-SIN": [m.sin_static, m.sin_live, c.sin_modification],
    "KSI-SVC-ASM": [m.asm_static, m.asm_live, c.asm_keys_certs],
    "KSI-MLA-LET": [m.let_static, m.let_live, c.let_list],
    "KSI-RPL-ABO": [m.abo_static, m.abo_live, m.abo_alert],
    "KSI-SVC-VCM": [m.vcm_static, m.vcm_live, c.vcm_client_auth],
    "KSI-CMT-LMC": [t.lmc_static, t.lmc_live, t.lmc_change_types],
    "KSI-CMT-RMV": [t.rmv_static, t.rmv_live],
    "KSI-CMT-VTD": [t.vtd_static, t.vtd_live],
    "KSI-CNA-DFP": [t.dfp_static, t.dfp_live, c.dfp_network_data],
    "KSI-CNA-IBP": [t.ibp_static, t.ibp_live, c.ibp_saas],
    "KSI-CNA-MAT": [t.mat_static, t.mat_live],
    "KSI-CNA-OFA": [t.ofa_static, t.ofa_live, c.ofa_recovery],
    "KSI-CNA-ULN": [t.uln_static, t.uln_live, c.uln_review],
    "KSI-IAM-AAM": [t.aam_static, t.aam_live, c.aam_role_group_lifecycle],
    "KSI-IAM-JIT": [t.jit_static, t.jit_live, c.jit_non_user],
    "KSI-IAM-SNU": [t.snu_static, t.snu_live],
    "KSI-IAM-SUS": [t.sus_static, t.sus_live],
    "KSI-SVC-ACM": [t.acm_static, t.acm_live],
    "KSI-SVC-EIS": [t.eis_svc_static, t.eis_svc_live],
    "KSI-SVC-PRR": [t.prr_static, t.prr_live, c.prr_plans],
    "KSI-SVC-RUD": [t.rud_static, t.rud_live, c.rud_terms],
    "KSI-SVC-VRI": [t.vri_static, t.vri_live, c.vri_artifacts],
    "KSI-MLA-ALA": [o.ala_static, o.ala_live, c.ala_classes],
    "KSI-MLA-EVC": [o.evc_static, o.evc_live, c.evc_saas],
    "KSI-MLA-OSM": [o.osm_static, o.osm_live, c.osm_review],
    "KSI-MLA-RVL": [o.rvl_static, o.rvl_live],
    "KSI-PIY-GIV": [o.giv_static, o.giv_live, c.giv_people],
    "KSI-PIY-RSD": [o.rsd_static, o.rsd_live],
    "KSI-RPL-ARP": [o.arp_static, o.arp_live],
    "KSI-RPL-TRC": [o.trc_static, o.trc_live, c.trc_history],
    "KSI-SCR-MIT": [o.mit_static, o.mit_live],
    "KSI-SCR-MON": [o.mon_static, o.mon_live],
    "KSI-RPL-RRO": [g.rpl_rro_static, g.rpl_rro_live],
    "KSI-INR-RIR": [g.inr_rir_static, g.inr_rir_live],
    "KSI-CNA-RVP": [g.cna_rvp_static, g.cna_rvp_live, g.cna_rvp_change],
    "KSI-CMT-RVP": [g.cmt_rvp_static, g.cmt_rvp_live, g.cmt_rvp_change],
}

# Known gaps between what the methods check and the OFFICIAL Class C KSI statement
# (frmr/fedramp-consolidated-rules.json). A KSI with a gap cannot roll up to a clean
# "pass" even when every method passes. Remove an entry only when the gap is closed.
KSI_NOTES = {
    "KSI-MLA-RVL": "Limit: methods prove that logs are reviewed and findings are triaged on time; they do not judge the quality of each review.",
    "KSI-PIY-RSD": "Limit: methods check the principles Orrinwick selected in its SDLC review record, not every principle in the CISA pledge. POL-PIY PIY-4 does not yet name the selected principles.",
    "KSI-RPL-ARP": "Methods compare the recovery plan record with the recovery objectives and check the age of its last review.",
    "KSI-RPL-TRC": "Limit: methods check recorded restore test results, their age and the test history; they do not run a restore. The test cadence differs between RPL-4 and SD-003 (issue #20); the history check uses the 90-day cycle in environment/recovery-objectives.json.",
    "KSI-SCR-MIT": "Limit: methods check review recency, stale risks and contract clauses; they do not judge the quality of each risk assessment.",
    "KSI-SCR-MON": "Methods check that upstream advisories are checked on time and that the SBOM is current. Action on each advisory is checked under the VDR process.",
    "KSI-CMT-LMC": "Monitoring is by alert on manual changes. Methods do not check a separate review of change logs.",
    "KSI-CNA-MAT": "Limit: methods count known lateral movement paths on each run; they do not run a full path analysis.",
    "KSI-IAM-SNU": "Official statement covers a persistent review of non-user authentication; methods check key age and declared key use, not a review record.",
    "KSI-IAM-SUS": "Limit: methods check response time on sampled privileged-account events, not every event.",
    "KSI-SVC-EIS": "Official statement requires improvements to be made; methods check that open items are not stale, not that each improvement was effective.",
    "KSI-SVC-RUD": "Methods check deletion requests against the 30-day term in Orrinwick's standard customer agreement (docs/customer-agreement-standard.md).",
    "KSI-RPL-ABO": "Methods check that backup configuration aligns with the recovery objectives in environment/recovery-objectives.json. Proof that a restore works and meets the RTO is under KSI-RPL-TRC.",
}

# A gap blocks a pass: the KSI stays at partial until a method covers the missing part (issue #39).
# Each entry names a part of the official statement that no method proves. The notes above record
# limits of depth that do not leave any part unproven. The triage of 23 Nov 2026 found 19 gaps; 17 are
# closed by the methods in methods_cover.py. The two left are the planned failures.
KSI_GAPS: dict[str, str] = {
    "KSI-IAM-SNU": "No method checks a review record for non-user authentication.",
    "KSI-SVC-EIS": "No method checks that improvements are made; methods check only that open items are not stale.",
}
