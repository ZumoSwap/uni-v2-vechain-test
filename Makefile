export vvet=../vvet/vvet/build/contracts/VVET9.json
export factory=../uni-v2/uniswap-v2-core/build/UniswapV2Factory.json
export router02=../uni-v2/uniswap-v2-periphery/build/UniswapV2Router02.json
export v2pair=../uni-v2/uniswap-v2-core/build/UniswapV2Pair.json

install:
	python3 -m venv .env
	. .env/bin/activate && pip3 install -r requirements.txt

test:
	if [ ! -d "./build" ]; then mkdir "./build"; fi
	if [ ! -d "./build/contracts" ]; then mkdir "./build/contracts"; fi
	cp $(vvet) ./build/contracts/
	cp $(factory) ./build/contracts/
	cp $(router02) ./build/contracts/
	cp $(v2pair) ./build/contracts/
	. .env/bin/activate && python3 -m pytest -vv -s
