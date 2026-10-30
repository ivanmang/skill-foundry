# == skill-foundry ==
#
#   make check       run the full self-check (compile + spec + demo + tilelangGym)
#   make push-check  run the lightweight pre-push gate (spec + refs + index + tests)
#   make hooks       enable the .githooks pre-push hook
#   make validate    check suites/arches/cann configs
#   make help        show this

.PHONY: check push-check hooks validate help

check:
	./skill_foundry/cli/selfcheck.sh

push-check:
	./scripts/check.sh

hooks:
	git config core.hooksPath .githooks

validate:
	python3 -m skill_foundry.cli.validate

help:
	@./harness help
