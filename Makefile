.PHONY: dev build test

dev build test:
	$(MAKE) -C server $@
