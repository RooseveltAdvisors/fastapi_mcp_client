#!/bin/bash
set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting package publication process...${NC}"

# Allow specifying custom .pypirc location
PYPIRC_PATH="${PYPIRC_PATH:-$HOME/.pypirc}"
echo -e "${GREEN}Using credentials from: $PYPIRC_PATH${NC}"

# Check if credentials file exists
if [ ! -f "$PYPIRC_PATH" ]; then
    echo -e "${YELLOW}Creating .pypirc template at $PYPIRC_PATH${NC}"
    cat > "$PYPIRC_PATH" << EOF
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-your-token-here

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-test-your-token-here
EOF
    chmod 600 "$PYPIRC_PATH"
    echo -e "${RED}IMPORTANT: Edit $PYPIRC_PATH with your actual tokens from:${NC}"
    echo -e "${YELLOW}- PyPI: https://pypi.org/manage/account/token/${NC}"
    echo -e "${YELLOW}- TestPyPI: https://test.pypi.org/manage/account/token/${NC}"
    exit 1
fi

# Check for template values in .pypirc
if grep -q "pypi-your-token-here\|pypi-test-your-token-here" "$PYPIRC_PATH"; then
    echo -e "${RED}WARNING: Your $PYPIRC_PATH still contains template tokens!${NC}"
    echo -e "${RED}Replace them with your actual tokens before continuing.${NC}"
    exit 1
fi

# Run pytest first - fail if tests don't pass
echo -e "${GREEN}Running tests...${NC}"
uv add --dev pytest
if ! uv run -m pytest; then
    echo -e "${RED}Tests failed! Aborting publication process.${NC}"
    exit 1
fi
echo -e "${GREEN}All tests passed.${NC}"

# Run ruff format
echo -e "${GREEN}Running code formatting...${NC}"
uv add --dev ruff
uv run -m ruff format .
echo -e "${GREEN}Code formatting completed.${NC}"

# Run ruff check
echo -e "${GREEN}Running code linting...${NC}"
if ! uv run -m ruff check .; then
    echo -e "${RED}Code linting failed! Please fix the issues and try again.${NC}"
    exit 1
fi
echo -e "${GREEN}Code linting passed.${NC}"

# Get version information interactively
echo -e "${GREEN}Version management${NC}"
# Extract current version
CURRENT_VERSION=$(sed -n 's/^version = "\([^"]*\)"/\1/p' pyproject.toml)
if [ -z "$CURRENT_VERSION" ]; then
    echo -e "${RED}Could not find version in pyproject.toml${NC}"
    exit 1
fi

echo -e "${YELLOW}Current version: ${CURRENT_VERSION}${NC}"
read -p "Enter new version (leave empty to keep current): " NEW_VERSION
NEW_VERSION=${NEW_VERSION:-$CURRENT_VERSION}

if [ "$NEW_VERSION" != "$CURRENT_VERSION" ]; then
    # Update version in pyproject.toml
    sed -i.bak "s/version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml
    rm -f pyproject.toml.bak  # Remove backup file created by sed
    echo -e "${GREEN}Version updated from $CURRENT_VERSION to $NEW_VERSION${NC}"
    
    # Get commit message
    read -p "Enter commit message (default: Bump version to $NEW_VERSION): " COMMIT_MSG
    COMMIT_MSG=${COMMIT_MSG:-"Bump version to $NEW_VERSION"}
    
    # Commit the version change
    git add pyproject.toml
    git commit -m "$COMMIT_MSG"
    
    # Create a git tag
    git tag -a "v$NEW_VERSION" -m "Version $NEW_VERSION"
    echo -e "${GREEN}Created git tag v$NEW_VERSION${NC}"
    
    # Push changes and tag to remote
    echo -e "${GREEN}Pushing changes to remote...${NC}"
    git push origin main
    git push origin "v$NEW_VERSION"
    echo -e "${GREEN}Changes pushed to remote.${NC}"
else
    echo -e "${YELLOW}Version unchanged.${NC}"
    read -p "Continue with the current version? (y/n) " continue
    if [[ ! "$continue" =~ ^[Yy]$ ]]; then
        echo -e "${RED}Publication process aborted.${NC}"
        exit 0
    fi
fi

# Install dependencies if needed
command -v twine &> /dev/null || pip install --user twine

# Clean and build
echo -e "${GREEN}Building package...${NC}"
rm -rf dist build
uv add --dev build
uv run -m build

# Validate and upload to TestPyPI
echo -e "${GREEN}Uploading to Test PyPI...${NC}"
twine check dist/*
echo -e "${GREEN}Using config file: $PYPIRC_PATH${NC}"
twine upload --verbose --config-file "$PYPIRC_PATH" --repository testpypi dist/*

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Test PyPI upload successful! View at: https://test.pypi.org/project/fastapi-mcp-client/${NC}"
else
    echo -e "${RED}Test PyPI upload failed.${NC}"
    echo -e "${YELLOW}Common issues:${NC}"
    echo -e "${YELLOW}1. Check if your tokens in $PYPIRC_PATH are correct${NC}"
    echo -e "${YELLOW}2. Package version may already exist (update version in pyproject.toml)${NC}"
    echo -e "${YELLOW}3. Package name might be taken or reserved${NC}"
    echo -e "${YELLOW}For detailed error info, run:${NC}"
    echo -e "${YELLOW}  twine upload --verbose --config-file $PYPIRC_PATH --repository testpypi dist/*${NC}"
    exit 1
fi

# Upload to PyPI after confirmation
read -p "Proceed with uploading to PyPI? (y/n) " proceed
if [[ "$proceed" =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Uploading to PyPI...${NC}"
    twine upload --verbose --config-file "$PYPIRC_PATH" dist/*
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}PyPI upload successful! View at: https://pypi.org/project/fastapi-mcp-client/${NC}"
    else
        echo -e "${RED}PyPI upload failed.${NC}"
        echo -e "${YELLOW}Run with --verbose for more details.${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Upload to PyPI aborted.${NC}"
    exit 0
fi

echo -e "${GREEN}Publication process completed!${NC}"