# StarcraftStockfish Development Instructions

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Project Overview

StarcraftStockfish is a StarCraft II AI bot framework built on top of sharpy-sc2 and python-sc2. It implements competitive AI bots for StarCraft II, with the main "Stockfish" bot being a Terran strategy bot. The framework includes bot loading, ladder management, and competitive play infrastructure.

## Working Effectively

### Bootstrap, Build, and Test the Repository:

**CRITICAL: All commands require proper PYTHONPATH setup:**
```bash
export PYTHONPATH=python-sc2:.
```

**Install Dependencies (2-3 minutes):**
```bash
pip install -r requirements.txt
pip install -r requirements.dev.txt
```

**Linting (takes ~2 seconds, ALWAYS run before committing):**
```bash
python -m flake8 --config .flake8 stockfish/ sharpy/ --count
```

**Testing:**
```bash
# Python-sc2 unit tests (takes ~1 second):
cd python-sc2 && PYTHONPATH=.. python -m pytest test/test_directions.py test/test_expiring_dict.py test/test_replays.py -v

# NEVER CANCEL: Full python-sc2 tests with SC2 client take 15+ minutes
# Sharpy tests require sc2pathlib binary (currently missing - see Limitations below)
```

**Code Formatting:**
```bash
# WARNING: Black formatter has compatibility issues with current environment
# Use flake8 for linting only - black --version fails due to click import error
```

## Validation

**Always run these validation steps after making changes:**

1. **Linting validation (REQUIRED before committing):**
   ```bash
   PYTHONPATH=python-sc2:. python -m flake8 --config .flake8 stockfish/ sharpy/ --count
   ```

2. **Import validation:**
   ```bash
   PYTHONPATH=python-sc2:. python -c "
   from sc2.data import Race
   from sc2.ids.unit_typeid import UnitTypeId
   from config import get_config
   print('✓ Core imports successful')
   "
   ```

3. **Configuration validation:**
   ```bash
   PYTHONPATH=python-sc2:. python -c "
   from config import get_config
   config = get_config()
   print('✓ Configuration loaded:', config.get('general', 'debug'))
   "
   ```

**Manual Testing Scenarios:**
- Configuration file parsing and loading
- Basic sc2 data structure imports and manipulation
- Flake8 linting across the entire codebase
- Python-sc2 framework unit tests

## Common Tasks

### Repository Structure
```
.
├── README.md                 # Main documentation
├── requirements.txt          # Production dependencies
├── requirements.dev.txt      # Development dependencies
├── config.ini               # Bot configuration
├── stockfish/               # Main Stockfish bot implementation
├── sharpy/                  # Sharpy-sc2 framework
├── python-sc2/              # Python-sc2 submodule
├── bot_loader/              # Bot loading and management
├── sc2pathlib/              # Pathfinding library (binary missing)
├── tools/                   # Utility scripts
└── test/                    # Test files
```

### Key Files and Locations

**Bot Implementation:**
- `stockfish/stockfish.py` - Main bot logic and build orders
- `stockfish/run.py` - Bot entry point for ladder games
- `run_custom.py` - Custom game runner

**Configuration:**
- `config.ini` - Main configuration file
- `pyproject.toml` - Black formatter settings (excluded directories)
- `.flake8` - Linting configuration
- `pytest.ini` - Test configuration

**Framework Files (frequently modified):**
- `sharpy/` - Core AI framework components
- `bot_loader/` - Bot definitions and game management
- Always check these after making changes to core AI logic

### Development Commands

**Start Development:**
```bash
cd /path/to/StarcraftStockfish
export PYTHONPATH=python-sc2:.
pip install -r requirements.txt
pip install -r requirements.dev.txt
```

**Validate Changes:**
```bash
# Lint code (REQUIRED before committing)
python -m flake8 --config .flake8 stockfish/ sharpy/ --count

# Test basic imports
PYTHONPATH=python-sc2:. python -c "from stockfish import Stockfish; print('✓ Imports work')"

# Run working tests
cd python-sc2 && PYTHONPATH=.. python -m pytest test/test_directions.py test/test_expiring_dict.py -v
```

**Create Ladder Bots:**
```bash
# Build bot packages for competitive play
PYTHONPATH=python-sc2:. python dummy_ladder_zip.py
# Output appears in publish/ folder
```

## Limitations and Known Issues

**CRITICAL LIMITATIONS:**

1. **sc2pathlib Binary Missing:**
   - The compiled pathfinding library `sc2pathlib.sc2pathlib` is not available
   - This prevents full bot instantiation and sharpy tests from running
   - Framework core functionality works, but advanced pathfinding features don't
   - DO NOT attempt to fix this - it requires platform-specific compiled binaries

2. **StarCraft II Client Required:**
   - Full bot testing requires StarCraft II game client installation
   - Bot vs bot games and ladder functionality cannot be tested without SC2
   - Use import validation and unit tests for development validation

3. **Black Formatter Incompatibility:**
   - `python -m black --version` fails due to click library version conflicts
   - Use flake8 for linting only
   - Manual code formatting may be required

4. **Test Limitations:**
   - Only python-sc2 unit tests work without SC2 client
   - Sharpy tests require sc2pathlib binary
   - Full integration tests require SC2 client + maps

## Development Workflow

**Always follow this workflow:**

1. Set up environment: `export PYTHONPATH=python-sc2:.`
2. Install dependencies if needed
3. Make your changes to stockfish/, sharpy/, or other relevant areas
4. Validate imports: Test basic Python imports work
5. Run linting: `python -m flake8 --config .flake8 stockfish/ sharpy/ --count`
6. Run available tests: python-sc2 unit tests
7. Test configuration loading if you changed config-related code
8. Commit changes only after linting passes

**For AI Logic Changes:**
- Always test basic bot imports after changes
- Verify configuration loading works
- Check that build order logic compiles (imports successfully)
- Consider running `dummy_ladder_zip.py` to verify packaging works

**File Pattern Matching:**
- Test files: `*_test.py` or `test_*.py`
- Bot implementations: `stockfish/*.py`
- Framework core: `sharpy/managers/`, `sharpy/plans/`
- Configuration: `config*.ini`, `*.toml`, `.flake8`

This framework is designed for competitive StarCraft II AI development. Focus on code quality, proper imports, and linting compliance rather than full end-to-end testing without the SC2 client.