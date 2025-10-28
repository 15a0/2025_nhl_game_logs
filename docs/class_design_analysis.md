# Class Design Analysis

**Document Purpose**: Identify where classes add value vs. where functions are sufficient. Analyze state management, lifecycle, and reusability.

**Status**: Design Phase (pre-implementation)  
**Last Updated**: October 28, 2025

---

## Table of Contents

1. [When Classes Make Sense](#when-classes-make-sense)
2. [Candidate Classes](#candidate-classes)
3. [Candidate Functions (No Class Needed)](#candidate-functions-no-class-needed)
4. [Detailed Analysis](#detailed-analysis)
5. [Class Hierarchy & Relationships](#class-hierarchy--relationships)
6. [Final Recommendation](#final-recommendation)

---

## When Classes Make Sense

Classes are useful when you have:

1. **State to manage**: Data that persists across multiple operations
2. **Lifecycle**: Setup, operations, teardown (e.g., connect/close)
3. **Encapsulation**: Hide internal complexity, expose clean interface
4. **Reusability**: Same object used in multiple contexts
5. **Inheritance/Polymorphism**: Shared behavior across variants

Classes are **overkill** when you have:
- ❌ Pure functions (no state)
- ❌ One-off operations
- ❌ No shared data
- ❌ No lifecycle management

---

## Candidate Classes

### 1. **DBManager** ✅ STRONG CASE FOR CLASS

**Why**:
- **State**: Manages connection object (`self.conn`)
- **Lifecycle**: `connect()` → operations → `close()`
- **Reusability**: Used throughout orchestrator
- **Context manager**: Natural fit for `with` statement

**Current Design**:
```python
class DBManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
    
    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
    
    def insert_game(self, ...):
        # Uses self.conn
    
    def close(self):
        if self.conn:
            self.conn.close()
```

**Usage**:
```python
with DBManager(DB_PATH) as db:
    db.insert_game(game_id, ...)
    db.insert_game_stats(game_id, team, stats)
```

**Verdict**: ✅ **DEFINITE CLASS**

---

### 2. **GameProcessor** ✅ STRONG CASE FOR CLASS

**Why**:
- **State**: Tracks game being processed (game_id, boxscore, plays, stats)
- **Lifecycle**: Fetch → Parse → Calculate → Store
- **Encapsulation**: Hides complexity of multi-step process
- **Reusability**: Used by orchestrator for each game

**Proposed Design**:
```python
class GameProcessor:
    def __init__(self, game_id, db_manager):
        self.game_id = game_id
        self.db = db_manager
        self.boxscore = None
        self.play_by_play = None
        self.plays = None
        self.teams = None
        self.stats = {}
    
    def fetch(self):
        """Fetch boxscore and play-by-play"""
        self.boxscore = fetch_boxscore(self.game_id)
        self.play_by_play = fetch_play_by_play(self.game_id)
        return self
    
    def parse(self):
        """Parse JSON responses"""
        self.teams = parse_boxscore(self.boxscore)
        self.plays = parse_plays(self.play_by_play)
        return self
    
    def calculate(self):
        """Calculate stats for all teams"""
        for team in self.teams:
            self.stats[team['abbrev']] = compute_team_stats(
                self.boxscore, self.plays, team['id']
            )
        return self
    
    def store(self):
        """Store in database"""
        for team_abbrev, stats in self.stats.items():
            self.db.insert_game_stats(self.game_id, team_abbrev, stats)
        return self
    
    def process(self):
        """Orchestrate entire pipeline"""
        return self.fetch().parse().calculate().store()
```

**Usage**:
```python
processor = GameProcessor(game_id, db)
processor.process()
# Or step-by-step:
processor.fetch().parse().calculate().store()
```

**Benefits**:
- ✅ Fluent interface (method chaining)
- ✅ Can inspect state at any point (e.g., `processor.stats`)
- ✅ Easy to test (mock each step)
- ✅ Easy to extend (add validation, logging, retry logic)

**Verdict**: ✅ **STRONG CLASS**

---

### 3. **Game** ✅ MODERATE CASE FOR CLASS

**Why**:
- **State**: Represents a single game with all its data
- **Encapsulation**: Game logic in one place
- **Reusability**: Can be passed around, queried

**Proposed Design**:
```python
class Game:
    def __init__(self, game_id, date, away_team, home_team, away_score, home_score):
        self.game_id = game_id
        self.date = date
        self.away_team = away_team
        self.home_team = home_team
        self.away_score = away_score
        self.home_score = home_score
        self.stats = {}  # {team_abbrev: stats_dict}
    
    def add_stats(self, team_abbrev, stats):
        self.stats[team_abbrev] = stats
    
    def get_stats(self, team_abbrev):
        return self.stats.get(team_abbrev)
    
    def is_complete(self):
        """Check if both teams have stats"""
        return len(self.stats) == 2
```

**Usage**:
```python
game = Game(2025020001, "2025-10-07", "CHI", "FLA", 3, 4)
game.add_stats("CHI", chi_stats)
game.add_stats("FLA", fla_stats)
db.insert_game(game)
```

**Verdict**: ⚠️ **OPTIONAL CLASS** (Nice to have, but not essential)

---

### 4. **StatsCalculator** ❌ WEAK CASE FOR CLASS

**Why**:
- **No state**: Pure calculations
- **No lifecycle**: No setup/teardown
- **Reusability**: Functions work fine

**Current Design** (functions):
```python
def calculate_xg(x, y, shot_type):
    # Pure function
    pass

def compute_corsi(plays, team_id):
    # Pure function
    pass

def compute_team_stats(boxscore, plays, team_id):
    # Pure function
    pass
```

**Could be a class**:
```python
class StatsCalculator:
    @staticmethod
    def calculate_xg(x, y, shot_type):
        pass
    
    @staticmethod
    def compute_corsi(plays, team_id):
        pass
```

**Problem**: Using `@staticmethod` is just wrapping functions in a class. No benefit.

**Verdict**: ❌ **KEEP AS FUNCTIONS** (No state, no lifecycle)

---

### 5. **APIClient** ⚠️ WEAK-TO-MODERATE CASE FOR CLASS

**Why**:
- **Minimal state**: Base URL, timeout (could be constants)
- **Reusability**: Used multiple times
- **Extensibility**: Could add retry logic, rate limiting, caching

**Current Design** (functions):
```python
def fetch_boxscore(game_id):
    response = requests.get(BOXSCORE_URL.format(game_id))
    return response.json()

def fetch_play_by_play(game_id):
    response = requests.get(PLAY_BY_PLAY_URL.format(game_id))
    return response.json()
```

**Could be a class**:
```python
class APIClient:
    def __init__(self, timeout=10, rate_limit_delay=0.5):
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = None
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def fetch_boxscore(self, game_id):
        self._rate_limit()
        response = requests.get(BOXSCORE_URL.format(game_id), timeout=self.timeout)
        response.raise_for_status()
        return response.json()
    
    def fetch_play_by_play(self, game_id):
        self._rate_limit()
        response = requests.get(PLAY_BY_PLAY_URL.format(game_id), timeout=self.timeout)
        response.raise_for_status()
        return response.json()
```

**Usage**:
```python
api = APIClient(timeout=10, rate_limit_delay=0.5)
boxscore = api.fetch_boxscore(game_id)
pbp = api.fetch_play_by_play(game_id)
```

**Benefits**:
- ✅ Rate limiting (shared state)
- ✅ Configurable timeout
- ✅ Easy to add caching, retry logic later
- ✅ Can mock for testing

**Verdict**: ✅ **MODERATE CLASS** (Nice to have, enables future features)

---

### 6. **DataParser** ❌ WEAK CASE FOR CLASS

**Why**:
- **No state**: Pure parsing
- **No lifecycle**: No setup/teardown
- **Reusability**: Functions work fine

**Current Design** (functions):
```python
def parse_boxscore(boxscore_json):
    # Pure function
    pass

def parse_plays(pbp_json):
    # Pure function
    pass
```

**Verdict**: ❌ **KEEP AS FUNCTIONS** (No state, no lifecycle)

---

## Candidate Functions (No Class Needed)

| Module | Function | Why Not a Class |
|--------|----------|-----------------|
| `stats_calculator.py` | `calculate_xg()` | Pure function, no state |
| `stats_calculator.py` | `compute_corsi()` | Pure function, no state |
| `stats_calculator.py` | `compute_team_stats()` | Pure function, no state |
| `data_parser.py` | `parse_boxscore()` | Pure function, no state |
| `data_parser.py` | `parse_plays()` | Pure function, no state |
| `utils.py` | `normalize_stats()` | Pure function, no state |
| `utils.py` | `calculate_goi()` | Pure function, no state |

---

## Detailed Analysis

### DBManager (Class) - Deep Dive

**State Management**:
```python
self.db_path      # Configuration
self.conn         # Lifecycle (None → Connection → None)
```

**Lifecycle**:
```
__init__()  → connect()  → [operations]  → close()
   ↓            ↓              ↓              ↓
Create      Establish     Use conn      Clean up
instance    connection    for queries   connection
```

**Why Class**:
- Connection is expensive; reuse it
- Need to track connection state
- Context manager (`__enter__`/`__exit__`) is natural
- Easy to add logging, retry logic, connection pooling

**Example with Logging**:
```python
class DBManager:
    def insert_game(self, game_id, ...):
        logger.debug(f"Inserting game {game_id}")
        try:
            self.conn.execute(...)
            logger.info(f"Successfully inserted game {game_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to insert game {game_id}: {e}")
            raise DBError(...)
```

---

### GameProcessor (Class) - Deep Dive

**State Management**:
```python
self.game_id          # Identity
self.db               # Dependency (DBManager)
self.boxscore         # Intermediate state (fetch)
self.play_by_play     # Intermediate state (fetch)
self.plays            # Intermediate state (parse)
self.teams            # Intermediate state (parse)
self.stats            # Final state (calculate)
```

**Lifecycle**:
```
__init__()  → fetch()  → parse()  → calculate()  → store()
   ↓          ↓          ↓          ↓              ↓
Create    Get data   Extract    Compute        Save to
instance  from API   relevant   advanced       database
          fields     stats
```

**Why Class**:
- Multi-step process with intermediate state
- Each step depends on previous step
- Can inspect state at any point (debugging)
- Fluent interface (method chaining) is elegant
- Easy to add error handling, logging, retry logic

**Example with Error Handling**:
```python
class GameProcessor:
    def process(self):
        try:
            self.fetch()
        except APIError as e:
            logger.error(f"Failed to fetch game {self.game_id}: {e}")
            raise
        
        try:
            self.parse()
        except ParseError as e:
            logger.error(f"Failed to parse game {self.game_id}: {e}")
            raise
        
        try:
            self.calculate()
        except Exception as e:
            logger.error(f"Failed to calculate stats for {self.game_id}: {e}")
            raise
        
        try:
            self.store()
        except DBError as e:
            logger.error(f"Failed to store stats for {self.game_id}: {e}")
            raise
        
        logger.info(f"Successfully processed game {self.game_id}")
```

---

### APIClient (Class) - Deep Dive

**State Management**:
```python
self.timeout              # Configuration
self.rate_limit_delay     # Configuration
self.last_request_time    # State (for rate limiting)
```

**Why Class**:
- Rate limiting requires shared state (`last_request_time`)
- Configuration (timeout, delay) is instance-specific
- Easy to add caching, retry logic, exponential backoff

**Example with Caching**:
```python
class APIClient:
    def __init__(self, timeout=10, rate_limit_delay=0.5, cache_ttl=3600):
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self.cache_ttl = cache_ttl
        self.cache = {}  # {game_id: (data, timestamp)}
    
    def fetch_boxscore(self, game_id):
        # Check cache
        if game_id in self.cache:
            data, timestamp = self.cache[game_id]
            if time.time() - timestamp < self.cache_ttl:
                logger.debug(f"Cache hit for boxscore {game_id}")
                return data
        
        # Fetch from API
        self._rate_limit()
        response = requests.get(BOXSCORE_URL.format(game_id), timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        
        # Store in cache
        self.cache[game_id] = (data, time.time())
        return data
```

---

## Class Hierarchy & Relationships

```
┌─────────────────────────────────────────────────┐
│              Orchestrator                        │
│  (Main entry point, coordinates everything)     │
└────────────────┬────────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
    ┌────────────┐   ┌──────────────┐
    │ APIClient  │   │  DBManager   │
    │ (Fetch)    │   │ (Store)      │
    └────────────┘   └──────────────┘
        │                 ▲
        │                 │
        └────────┬────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ GameProcessor    │
        │ (Orchestrate)    │
        │ - fetch()        │
        │ - parse()        │
        │ - calculate()    │
        │ - store()        │
        └──────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
    ┌────────────┐   ┌──────────────┐
    │ Functions  │   │ Functions    │
    │ (Parse)    │   │ (Calculate)  │
    └────────────┘   └──────────────┘
```

**Relationships**:
- `Orchestrator` creates `APIClient` and `DBManager`
- `Orchestrator` creates `GameProcessor` for each game
- `GameProcessor` uses `APIClient` to fetch
- `GameProcessor` uses functions to parse/calculate
- `GameProcessor` uses `DBManager` to store

---

## Final Recommendation

### Classes to Create (3 Total)

| Class | Purpose | State | Lifecycle |
|-------|---------|-------|-----------|
| `DBManager` | Database operations | Connection | connect/close |
| `GameProcessor` | Process single game | Intermediate data | fetch/parse/calc/store |
| `APIClient` | NHL API fetching | Rate limit, cache | (optional) |

### Functions to Keep (No Classes)

| Module | Functions | Reason |
|--------|-----------|--------|
| `stats_calculator.py` | All | Pure calculations, no state |
| `data_parser.py` | All | Pure parsing, no state |
| `utils.py` | All | Pure helpers, no state |

### Code Organization

```python
# modules/db_manager.py
class DBManager:
    def __init__(self, db_path):
        ...

# modules/api_client.py
class APIClient:
    def __init__(self, timeout=10, rate_limit_delay=0.5):
        ...

# modules/game_processor.py
class GameProcessor:
    def __init__(self, game_id, db_manager, api_client):
        ...

# modules/stats_calculator.py
def calculate_xg(x, y, shot_type):
    ...

def compute_corsi(plays, team_id):
    ...

# modules/data_parser.py
def parse_boxscore(boxscore_json):
    ...

def parse_plays(pbp_json):
    ...

# scripts/orchestrator.py
def main():
    api = APIClient()
    db = DBManager(DB_PATH)
    
    for game_id in games_to_process:
        processor = GameProcessor(game_id, db, api)
        processor.process()
```

---

## Summary

**Classes** (3):
- ✅ `DBManager` - Connection lifecycle, state management
- ✅ `GameProcessor` - Multi-step orchestration, intermediate state
- ✅ `APIClient` - Rate limiting, caching, configuration

**Functions** (All others):
- ✅ `stats_calculator.py` - Pure calculations
- ✅ `data_parser.py` - Pure parsing
- ✅ `utils.py` - Pure helpers

**Principle**: Use classes for **stateful, lifecycle-managed operations**. Use functions for **pure transformations**.

---

**Document Version**: 1.0  
**Status**: Ready for Review  
**Author**: Cascade AI Assistant  
**Reviewed By**: [Pending]
