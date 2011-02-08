all: build commit

build:
	python poole.py --build # --base-url=http://www.the-pulsar.com/

update: build
	-git add .
	-git commit -am "Web site udpdate."
	-git push

serve:
	poole.py --serve

serve:
	python poole.py serve
