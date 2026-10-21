.PHONY: test manifest verify ci spend
test:
	python3 -m unittest discover -s tests -t . -v
manifest:
	python3 -m agentkit.manifest build .
verify:
	python3 -m agentkit.manifest verify .
ci:
	./scripts/pipeline.sh
spend:
	python3 -m agentkit.spend examples/usage.sample.jsonl --group-by agent --prices examples/prices.example.json
