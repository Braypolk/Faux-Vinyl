DEV_ADDR ?= 127.0.0.1:18787
BIN := .local/bin/fauxvinyl

.PHONY: dev build test test-race

build:
	@mkdir -p .local/bin
	go build -o $(BIN) .

dev: build
	$(BIN) -dev -listen $(DEV_ADDR)

test:
	$(MAKE) -C .. test

test-race:
	$(MAKE) -C .. test-race
