PICO8    ?= $(HOME)/Downloads/pico-8\ 2/PICO-8.app/Contents/MacOS/pico8
CART      = game.p8
DEBUGVIEW = uv run tools/debugview.py

.PHONY: run lint test debug web png bin clean

PICO8_RUN = $(PICO8) -root_path $(CURDIR) -run $(CART)

# Launch the game in PICO-8 (suppress debug output)
run:
	$(PICO8_RUN) > /dev/null

# Launch game with live debug viewer (printh output piped to debugview)
debug:
	$(PICO8_RUN) | $(DEBUGVIEW)

# Lint all Lua code referenced by the cart
lint:
	uv run tools/p8lint.py $(CART)

# Run linter unit tests
test:
	uv run --with pytest pytest tests/ -v

# Export as a standalone web page (game.html + game.js)
web:
	$(PICO8) $(CART) -export game.html

# Export as a cartridge PNG (shareable on Lexaloffle BBS)
# Note: requires a label — run the game, press F7 to capture one, then save
png:
	$(PICO8) $(CART) -export game.p8.png

# Export as native executables (Mac/Win/Linux)
bin:
	$(PICO8) $(CART) -export game.bin

clean:
	rm -f game.html game.js game.p8.png game.bin
