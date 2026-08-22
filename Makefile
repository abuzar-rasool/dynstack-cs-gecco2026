SIM_ID     ?= 658f9b28-6686-40d2-8800-611bd8466215
SCENARIO   ?= default
STRATEGIES ?=
WORKERS    ?= 8
SEEDS      ?= 10
EVAL_FLAGS ?=

RUNNER_DLL = server/simulation/DynStack.SimulationRunner/bin/Debug/net10.0/DynStack.SimulationRunner.dll

.DEFAULT_GOAL := eval
.PHONY: eval build server server-async client clean

eval: $(RUNNER_DLL)
	cd client && uv run python -m eval \
	    $(if $(STRATEGIES),$(STRATEGIES),--interactive) \
	    --seeds $(SEEDS) --workers $(WORKERS) $(EVAL_FLAGS) --no-build

build $(RUNNER_DLL):
	cd server/simulation && dotnet build --nologo

server: $(RUNNER_DLL)
	cd client && uv run python -m scenarios --name "$(SCENARIO)" --out /tmp/dynstack-scenario.buf
	dotnet exec "$(RUNNER_DLL)" \
	    --sim CS --settings /tmp/dynstack-scenario.buf \
	    --url tcp://127.0.0.1:8080 --id "$(SIM_ID)" \
	    --syncurl tcp://127.0.0.1:2222

server-async: $(RUNNER_DLL)
	cd client && uv run python -m scenarios --name "$(SCENARIO)" --out /tmp/dynstack-scenario.buf
	dotnet exec "$(RUNNER_DLL)" \
	    --sim CS --settings /tmp/dynstack-scenario.buf \
	    --url tcp://127.0.0.1:8080 --id "$(SIM_ID)"

client:
	cd client && uv run python -u main.py --interactive

clean:
	rm -rf .venv /tmp/dynstack-scenario.buf /tmp/dynstack-eval
	find . -type d \( -name bin -o -name obj -o -name __pycache__ \) -exec rm -rf {} +
