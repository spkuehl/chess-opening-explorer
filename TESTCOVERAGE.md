# Test Coverage Documentation

## Overview

The Chess Explorer project implements a comprehensive test suite using **pytest** and **pytest-django**, covering four testing dimensions:

1. **Functional Coverage** - Features work as expected from a user perspective
2. **Requirements Coverage** - Data contracts and specifications are enforced
3. **Risk-Based Coverage** - High-risk, high-impact components are thoroughly tested
4. **Structural Coverage** - All code paths are executed

**Current Status:** 140 tests passing with **99% code coverage**

---

## Test Infrastructure

### Dependencies

```toml
# pyproject.toml [dependency-groups.dev]
pytest = ">=8.0"
pytest-django = ">=4.8"
pytest-cov = ">=4.1"       # Code coverage reporting
factory-boy = ">=3.3"       # Test data factories
```

### Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "chess_explorer.settings"
python_files = ["test_*.py", "*_test.py"]
addopts = "--cov=games --cov-report=term-missing"
testpaths = ["games/tests"]
```

### Directory Structure

```
games/
├── tests/
│   ├── __init__.py           # Test package
│   ├── conftest.py           # Shared fixtures
│   ├── factories.py          # Model factories (OpeningFactory, GameFactory)
│   ├── test_models.py        # Model tests (24 tests)
│   ├── test_parsers.py       # Parser tests (38 tests)
│   ├── test_services.py      # OpeningDetector tests (26 tests)
│   ├── test_repositories.py  # Repository tests (31 tests)
│   └── test_commands.py      # Management command tests (21 tests)
```

---

## Coverage by Component

| Component | Tests | Coverage | Status |
|-----------|-------|----------|--------|
| `models.py` | 24 | 100% | Complete |
| `parsers/pgn.py` | 38 | 97% | Complete |
| `services/openings.py` | 26 | 100% | Complete |
| `repositories.py` | 31 | 100% | Complete |
| `commands/detect_openings.py` | - | 100% | Complete |
| `commands/import_games.py` | - | 95% | Complete |
| `commands/load_openings.py` | - | 95% | Complete |
| **Total** | **140** | **99%** | **Complete** |

---

## 1. Functional Coverage (Features)

Tests that verify each feature works as expected from a user perspective.

### Feature: Game Import

| Test Case | Description | File |
|-----------|-------------|------|
| `test_import_single_game` | Import PGN with one game | `test_commands.py` |
| `test_import_multiple_games` | Import PGN with many games | `test_commands.py` |
| `test_import_with_opening_detection` | Games get openings assigned | `test_commands.py` |
| `test_import_skips_duplicates` | Duplicate games are skipped | `test_commands.py` |
| `test_import_with_batch_size` | Custom batch size works | `test_commands.py` |
| `test_import_file_not_found` | Error handling for missing files | `test_commands.py` |

### Feature: Opening Detection

| Test Case | Description | File |
|-----------|-------------|------|
| `test_detect_ruy_lopez` | Detect well-known opening | `test_services.py` |
| `test_detect_deepest_match` | Return most specific variation | `test_services.py` |
| `test_detect_no_match` | Handle games with no opening | `test_services.py` |
| `test_detect_without_move_numbers` | Handle various move formats | `test_services.py` |
| `test_detect_invalid_move_stops_parsing` | Graceful error handling | `test_services.py` |

### Feature: Opening Data Loading

| Test Case | Description | File |
|-----------|-------------|------|
| `test_load_openings_from_data_directory` | All ECO files loaded | `test_commands.py` |
| `test_load_openings_handles_duplicates` | Duplicate FENs ignored | `test_commands.py` |
| `test_load_openings_with_clear` | --clear flag works | `test_commands.py` |

---

## 2. Requirements Coverage (Data Contracts)

Tests that verify documented requirements and data contracts are enforced.

### Opening Model Contract

| Test Case | Requirement |
|-----------|-------------|
| `test_opening_fen_unique_constraint` | FEN must be unique |
| `test_opening_required_fields` | eco_code, name, moves, ply_count required |
| `test_str_representation` | `__str__` returns "eco_code: name" |

### Game Model Contract

| Test Case | Requirement |
|-----------|-------------|
| `test_source_id_unique_constraint` | source_id must be unique |
| `test_opening_foreign_key_nullable` | opening FK can be null |
| `test_opening_on_delete_set_null` | Deleting Opening sets FK to NULL |
| `test_raw_headers_json_field` | JSON field stores data correctly |

### GameData Contract

| Test Case | Requirement |
|-----------|-------------|
| `test_parse_extracts_all_fields` | All fields populated from PGN |
| `test_parse_without_detector` | opening_fen defaults to empty string |

---

## 3. Risk-Based Coverage (Critical Paths)

High-risk components with potential for data loss or corruption.

### Data Integrity (HIGH RISK)

| Test Case | Risk Mitigated |
|-----------|----------------|
| `test_save_batch_multiple_games` | All games in batch persisted |
| `test_save_batch_skips_duplicates` | No duplicate inserts |
| `test_cache_populated_on_init` | Opening cache consistent with DB |
| `test_save_batch_with_generator` | Streaming data handled correctly |

### Parser Robustness (HIGH RISK)

| Test Case | Risk Mitigated |
|-----------|----------------|
| `test_parse_empty_file` | Handle empty PGN files |
| `test_parse_missing_white_player` | Handle missing headers |
| `test_parse_missing_optional_headers` | Graceful defaults |
| `test_parse_date_invalid` | Invalid dates don't crash |

### Opening Detection Accuracy (HIGH RISK)

| Test Case | Risk Mitigated |
|-----------|----------------|
| `test_detect_invalid_move_stops_parsing` | Invalid moves handled |
| `test_detect_empty_fen_set` | Empty database handled |
| `test_detect_empty_moves` | Empty input handled |

---

## 4. Structural Coverage (Branch Testing)

Tests ensuring all conditional branches are executed.

### PGN Parser Branches

```python
# Opening detector present/absent
test_parse_with_detector_match()      # Detector enabled, match found
test_parse_with_detector_no_match()   # Detector enabled, no match
test_parse_without_detector()         # Detector disabled

# Date parsing branches
test_parse_date_valid()               # "2024.01.15"
test_parse_date_partial_day_unknown() # "2024.01.??"
test_parse_date_all_unknown()         # "????.??.??"
test_parse_date_empty_string()        # ""
test_parse_date_invalid_format()      # "invalid"

# Elo parsing branches
test_parse_int_valid()                # "2800"
test_parse_int_question_mark()        # "?"
test_parse_int_dash()                 # "-"
test_parse_int_none()                 # None
test_parse_int_invalid_string()       # "abc"
```

### Opening Detector Branches

```python
# Move parsing
test_parse_moves_with_numbers()       # "1. e4 e5"
test_parse_moves_without_numbers()    # "e4 e5"
test_parse_moves_with_result()        # "1. e4 1-0"
test_parse_moves_empty()              # ""

# FEN matching
test_fen_in_set()                     # Match found
test_fen_not_in_set()                 # No match
```

### Repository Branches

```python
# Opening FEN resolution
test_opening_fen_in_cache()           # Returns opening_id
test_opening_fen_not_in_cache()       # Returns None
test_opening_fen_empty()              # Returns None

# Batch processing
test_batch_smaller_than_size()        # Single flush
test_batch_equals_size()              # Exactly one flush
test_batch_larger_than_size()         # Multiple flushes
```

---

## Test Fixtures

### conftest.py Fixtures

| Fixture | Description |
|---------|-------------|
| `sample_pgn_content` | Valid PGN with one complete game |
| `multi_game_pgn` | PGN with three games |
| `malformed_pgn` | Invalid PGN for error testing |
| `pgn_with_missing_headers` | Minimal PGN headers |
| `pgn_with_partial_date` | PGN with "2024.??.??" date |
| `temp_pgn_file` | Temporary file with sample PGN |
| `sample_opening` | King's Pawn opening (1. e4) |
| `ruy_lopez_opening` | Ruy Lopez opening |
| `opening_set` | Set of 5 related openings |

### factories.py Factories

```python
class OpeningFactory(DjangoModelFactory):
    """Creates Opening instances with sequential FENs."""
    fen = factory.Sequence(lambda n: f"fen_{n}")
    eco_code = factory.Sequence(lambda n: f"A{n:02d}")
    name = factory.Sequence(lambda n: f"Test Opening {n}")
    moves = "1. e4"
    ply_count = 1

class GameFactory(DjangoModelFactory):
    """Creates Game instances with sequential source_ids."""
    source_id = factory.Sequence(lambda n: f"game_{n:08d}")
    white_player = factory.Sequence(lambda n: f"White Player {n}")
    black_player = factory.Sequence(lambda n: f"Black Player {n}")
    result = "1-0"
    moves = "1. e4 e5 2. Nf3 Nc6"
```

---

## Running Tests

### Basic Commands

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest games/tests/test_parsers.py

# Run specific test class
uv run pytest games/tests/test_models.py::TestOpeningModel

# Run specific test
uv run pytest games/tests/test_parsers.py::TestPGNParserDateParsing::test_parse_date_valid
```

### Coverage Reports

```bash
# Run with terminal coverage report
uv run pytest --cov=games --cov-report=term-missing

# Generate HTML coverage report
uv run pytest --cov=games --cov-report=html
# Open htmlcov/index.html in browser

# Run with both reports
uv run pytest --cov=games --cov-report=term-missing --cov-report=html
```

### Filtering Tests

```bash
# Run only tests matching a pattern
uv run pytest -k "parse_date"

# Run tests except those matching a pattern
uv run pytest -k "not integration"

# Stop on first failure
uv run pytest -x

# Run last failed tests
uv run pytest --lf
```

---

## Integration Test Workflows

### End-to-End Import Flow

```python
def test_load_then_import_with_detection():
    """Complete workflow: load openings, import games with detection."""
    # Step 1: Load openings
    call_command("load_openings")
    
    # Step 2: Import games (openings detected automatically)
    call_command("import_games", "games.pgn")
    
    # Verify: Game has opening assigned
    game = Game.objects.first()
    assert game.opening is not None
```

### Backfill Workflow

```python
def test_import_then_backfill():
    """Import games first, then backfill openings."""
    # Step 1: Import without openings
    call_command("import_games", "games.pgn")
    assert Game.objects.first().opening is None
    
    # Step 2: Load openings
    call_command("load_openings")
    
    # Step 3: Backfill
    call_command("detect_openings")
    
    # Verify: Game now has opening
    game = Game.objects.first()
    game.refresh_from_db()
    assert game.opening is not None
```

---

## Adding New Tests

### Guidelines

1. **Naming**: Use descriptive names starting with `test_`
2. **Docstrings**: Include a brief description of what's being tested
3. **Isolation**: Each test should be independent
4. **Fixtures**: Reuse fixtures from `conftest.py` when possible
5. **Assertions**: Use clear, specific assertions

### Example Test

```python
@pytest.mark.django_db
class TestNewFeature:
    """Tests for the new feature."""

    def test_feature_happy_path(self, sample_opening):
        """Feature works correctly with valid input."""
        result = new_feature(sample_opening)
        assert result.success is True
        assert result.data == expected_data

    def test_feature_edge_case(self):
        """Feature handles edge case gracefully."""
        result = new_feature(None)
        assert result.success is False
        assert "error" in result.message
```

---

## Maintenance

### When to Update Tests

- **New feature**: Add functional tests for the feature
- **Bug fix**: Add regression test to prevent recurrence
- **Refactoring**: Ensure existing tests still pass
- **Model changes**: Update model tests and factories

### Coverage Goals

- **Minimum**: 90% statement coverage
- **Target**: 95%+ statement coverage
- **Current**: 99% statement coverage

### CI Integration

Tests are configured to run automatically. Ensure all tests pass before merging:

```bash
# Pre-commit check
uv run pytest --tb=short

# Full CI check
uv run ruff check . && uv run pytest --cov=games
```
