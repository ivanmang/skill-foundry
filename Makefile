# == skill-foundry ==
#
#   make check    run the self-check (compile + skill-spec + demo smoke)
#   make validate check suites/arches/cann configs
#   make help     show this

.PHONY: check help validate

check:
	./skill_foundry/cli/selfcheck.sh

validate:
	python3 -m skill_foundry.cli.validate

help:
	@./harness help
