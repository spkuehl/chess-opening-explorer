# Chess Explorer API Documentation

This document describes the REST API for the Chess Explorer application.

## Overview

The API is built with Django Ninja and provides endpoints for exploring chess games and opening statistics. The API follows REST conventions and returns JSON responses.

## Base URL

All API endpoints are versioned and accessible at:

```
/api/v1/
```

## Documentation

Interactive API documentation is available at:

- **Swagger UI**: `/api/v1/docs` - Interactive API explorer
- **OpenAPI Schema**: `/api/v1/openapi.json` - Machine-readable API specification

## Authentication

Currently, the API does not require authentication. All endpoints are publicly accessible.

## Endpoints

### Opening Statistics

#### GET /api/v1/openings/stats/

Returns aggregated statistics for chess openings including game counts, win/draw/loss distribution, and average move counts.

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `white_player` | string | - | Filter games where white player name contains this value (case-insensitive) |
| `black_player` | string | - | Filter games where black player name contains this value (case-insensitive) |
| `any_player` | string | - | Filter games where either player contains this value (OR condition). Takes precedence over `white_player`/`black_player` |
| `date_from` | date | - | Lower bound for game date (inclusive, format: YYYY-MM-DD) |
| `date_to` | date | - | Upper bound for game date (inclusive, format: YYYY-MM-DD) |
| `white_elo_min` | integer | - | Minimum white player ELO |
| `white_elo_max` | integer | - | Maximum white player ELO |
| `black_elo_min` | integer | - | Minimum black player ELO |
| `black_elo_max` | integer | - | Maximum black player ELO |
| `threshold` | integer | 1 | Minimum game count required for an opening to appear in results |

**Response**

```json
{
  "items": [
    {
      "eco_code": "B33",
      "name": "Sicilian: Sveshnikov",
      "moves": "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 e5",
      "game_count": 1523,
      "white_wins": 687,
      "draws": 412,
      "black_wins": 424,
      "avg_moves": 42.3
    }
  ],
  "total": 847
}
```

**Response Fields**

| Field | Type | Description |
|-------|------|-------------|
| `items` | array | List of opening statistics |
| `items[].eco_code` | string | ECO classification code (e.g., "B33") |
| `items[].name` | string | Opening name (e.g., "Sicilian Defense") |
| `items[].moves` | string | Opening move sequence (e.g., "1. e4 c5") |
| `items[].game_count` | integer | Total number of games with this opening |
| `items[].white_wins` | integer | Number of games won by white (result "1-0") |
| `items[].draws` | integer | Number of drawn games (result "1/2-1/2") |
| `items[].black_wins` | integer | Number of games won by black (result "0-1") |
| `items[].avg_moves` | float | Average number of moves per game (null if no data) |
| `total` | integer | Total count of openings in the response |

**Example Requests**

```bash
# Get all opening statistics
curl http://localhost:8000/api/v1/openings/stats/

# Get statistics for a specific player (any color)
curl "http://localhost:8000/api/v1/openings/stats/?any_player=Carlsen"

# Get statistics for high-ELO games only (2700+)
curl "http://localhost:8000/api/v1/openings/stats/?white_elo_min=2700&black_elo_min=2700"

# Get statistics with minimum 10 games per opening
curl "http://localhost:8000/api/v1/openings/stats/?threshold=10"

# Combined filters
curl "http://localhost:8000/api/v1/openings/stats/?white_player=Nakamura&created_at_from=2024-01-01&threshold=5"
```

## Error Responses

### 422 Unprocessable Entity

Returned when query parameters fail validation.

```json
{
  "detail": [
    {
      "loc": ["query", "threshold"],
      "msg": "value is not a valid integer",
      "type": "type_error.integer"
    }
  ]
}
```

## Architecture

The API follows SOLID principles with clean layer separation:

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer                               │
│  games/api/router.py - Thin controllers, request handling   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Schema Layer                              │
│  games/api/schemas.py - Pydantic models for validation      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Service Layer                              │
│  games/services/opening_stats.py - Business logic           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  games/models.py - Django ORM models                        │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Service Layer Pattern**: Business logic is encapsulated in service classes (`OpeningStatsService`), keeping API controllers thin.

2. **Filter Parameters Dataclass**: Filter parameters use a dataclass (`OpeningStatsFilterParams`) for type safety and default values.

3. **Database Aggregation**: All counting and averaging is done at the database level using Django's `annotate()` with `Count()` and `Avg()`, ensuring optimal performance for large datasets.

4. **Indexed Fields**: Key filter fields (`white_player`, `black_player`, `date`, `white_elo`, `black_elo`, `created_at`) are indexed for efficient queries.

5. **Threshold Filtering**: The threshold filter uses SQL's `HAVING` clause (applied after aggregation) to efficiently exclude low-count openings.

## Performance Considerations

- **Database Indexes**: Filter fields are indexed for O(log n) lookups
- **Single Query**: All aggregation happens in a single database query
- **Lazy Evaluation**: QuerySets are evaluated lazily, allowing the database to optimize
- **Move Count Caching**: `move_count` is stored on the `Game` model to avoid runtime calculation

## Versioning

The API uses URL-based versioning (`/api/v1/`). Future breaking changes will be introduced under a new version prefix (e.g., `/api/v2/`).

## Future Endpoints

Planned endpoints for future releases:

- `GET /api/v1/games/` - List/search games with pagination
- `GET /api/v1/games/{id}/` - Get single game details with moves
- `GET /api/v1/players/stats/` - Player statistics (win rates, opening preferences)
- `POST /api/v1/games/upload/` - Upload PGN games
