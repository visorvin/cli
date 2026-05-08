.PHONY: build test lint install clean

build:
	go build -o bin/visor ./cmd/visor

test:
	go test ./...

lint:
	golangci-lint run

install:
	go install ./cmd/visor

clean:
	rm -rf bin/

build-mcp:
	go build -o bin/visor-mcp ./cmd/visor-mcp

install-mcp:
	go install ./cmd/visor-mcp

build-all: build build-mcp
