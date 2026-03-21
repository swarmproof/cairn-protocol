.PHONY: extract-abi install codegen build deploy clean

# Extract ABI from compiled contract
extract-abi:
	@echo "Extracting ABI from compiled contract..."
	@node scripts/extract-abi.js

# Install dependencies
install:
	@echo "Installing dependencies..."
	@npm install

# Generate types from schema and ABI
codegen: extract-abi
	@echo "Generating types..."
	@npm run codegen

# Build the subgraph
build: codegen
	@echo "Building subgraph..."
	@npm run build

# Deploy to The Graph Studio
deploy: build
	@echo "Deploying to The Graph Studio..."
	@npm run deploy

# Deploy to local graph node
deploy-local: build
	@echo "Creating local subgraph..."
	@npm run create-local || true
	@echo "Deploying to local graph node..."
	@npm run deploy-local

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	@rm -rf generated/ build/ abis/CairnCore.json

# Complete setup from scratch
setup: clean install extract-abi codegen build
	@echo "Setup complete!"

# Help
help:
	@echo "CAIRN Protocol Subgraph - Available Commands:"
	@echo ""
	@echo "  make extract-abi   - Extract ABI from compiled contract"
	@echo "  make install       - Install npm dependencies"
	@echo "  make codegen       - Generate types from schema and ABI"
	@echo "  make build         - Build the subgraph"
	@echo "  make deploy        - Deploy to The Graph Studio"
	@echo "  make deploy-local  - Deploy to local graph node"
	@echo "  make clean         - Remove generated files"
	@echo "  make setup         - Complete setup from scratch"
	@echo ""
