IMAGE_NAME=chromium-webide

build:
	docker build . -t $(IMAGE_NAME)

run:
	docker run -it -p 3000:3000 -v "$(pwd):/home/depot_tools" $(IMAGE_NAME)
