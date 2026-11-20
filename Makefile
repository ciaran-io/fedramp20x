PY ?= python3
CLASS ?= c

.PHONY: frmr all test evidencecheck envcheck scopelog registry validate mas policies docs site serve check clean

all: frmr envcheck scopelog registry validate evidencecheck mas policies docs site

frmr:       ## download the FedRAMP rules data (pinned commit, not stored in this repo)
	$(PY) tools/fetch_frmr.py

envcheck:   ## check the fictional environment against the scope record
	$(PY) tools/check_environment.py

scopelog:   ## check that scope record changes have a log entry
	$(PY) tools/check_scope_changes.py

registry:   ## resolve KSIs from the vendored FRMR data
	$(PY) tools/build_registry.py $(CLASS)

validate:   ## run all automated validation methods, write evidence/
	$(PY) tools/run_validators.py

evidencecheck: ## check evidence/latest.json against its schema and roll-up rules
	$(PY) tools/check_evidence.py

test:       ## run unit tests
	$(PY) -m unittest discover -s tests -t . -v

mas:        ## validate mas/mas-record.json and render the scope document + diagram
	$(PY) tools/build_mas.py

policies:   ## render the policy set from policies/policy-set.json
	$(PY) tools/build_policies.py

docs:       ## generate the rules matrix
	$(PY) tools/build_docs.py

site:       ## build the trust center snapshot trust-center/index.html
	$(PY) tools/build_trust_center.py

serve: site ## preview at http://localhost:8000
	cd trust-center && $(PY) -m http.server 8000

check: frmr ## validate the downloaded FRMR file against its schema
	$(PY) tools/check_frmr.py

clean:
	rm -f evidence/latest.json evidence/rules-matrix.json
