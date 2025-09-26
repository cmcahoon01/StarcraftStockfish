# Adaptive Build Order System

## Overview

The Adaptive Build Order system replaces the previous fixed build order with a dynamic system that responds to enemy compositions. Instead of following 11 simultaneous build lists, it now uses a single adaptive system that prioritizes counter units based on current game state.

## Key Components

### 1. UnitCounterRequest (`stockfish/unit_counter_request.py`)

Stores the required units and buildings to counter enemy compositions.

```python
# Example usage (this will be populated by future counter logic)
request = knowledge.unit_counter_request
request.add_unit_requirement(UnitTypeId.VIKINGFIGHTER, 12)  # Need 12 Vikings
request.add_building_requirement(UnitTypeId.STARPORT, 3)    # Need 3 Starports
```

### 2. AdaptiveBuildOrder (`stockfish/adaptive_build_order.py`)

The main build order class that:
- Checks counter requirements from `knowledge.unit_counter_request`
- Prioritizes units based on current vs required ratios
- Ensures sufficient production capacity
- Balances resource usage (minerals vs gas)
- Falls back to default build order when no counters needed

### 3. Knowledge Integration (`sharpy/knowledges/knowledge.py`)

Added `unit_counter_request` property to the Knowledge class for storing counter requirements throughout the game.

## How It Works

### 1. Ratio-Based Prioritization

The system builds units based on how far behind you are from the target ratio:

```
Priority = Current Count / Required Count
```

Lower ratios = higher priority. For example:
- Marines: 5/20 = 0.25 ratio
- Vikings: 1/12 = 0.08 ratio  
- **Vikings get built first** (lower ratio)

### 2. Production Capacity Management

Automatically calculates required production buildings:
- 20 Vikings → needs ~3 Starports
- 15 Marines → needs ~3 Barracks
- 8 Siege Tanks → needs ~2 Factories

### 3. Resource-Aware Building

Prioritizes units based on current resources:
- **High minerals, low gas** → build Marines, Hellions (mineral-only units)
- **High gas, low minerals** → build Marauders, Siege Tanks (gas-heavy units)

### 4. Default Build Order

When no counter requirements are set, uses a standard build order:
- Basic economy (SCVs, Depots)
- Core buildings (Barracks → Factory → Starport)
- Basic units (Marines, Hellions)

## Integration Example

The system is already integrated into the main Stockfish bot. Here's how future counter logic would work:

```python
# Future enemy analysis code would do something like:
if enemy_has_lots_of_air_units:
    knowledge.unit_counter_request.add_unit_requirement(UnitTypeId.VIKINGFIGHTER, 12)
    knowledge.unit_counter_request.add_unit_requirement(UnitTypeId.MARINE, 20)
    knowledge.unit_counter_request.add_building_requirement(UnitTypeId.STARPORT, 3)

elif enemy_has_heavy_armor:
    knowledge.unit_counter_request.add_unit_requirement(UnitTypeId.SIEGETANK, 8)
    knowledge.unit_counter_request.add_unit_requirement(UnitTypeId.MARAUDER, 15)
    knowledge.unit_counter_request.add_building_requirement(UnitTypeId.FACTORY, 2)
```

## Key Benefits

1. **Responsive**: Adapts to enemy composition in real-time
2. **Efficient**: Prioritizes most needed units first
3. **Resource-Aware**: Uses available resources optimally  
4. **Scalable**: Easy to add new counter strategies
5. **Minimal**: Only replaces build order logic, keeps everything else intact

## Testing

Run the demonstration to see how it works:

```bash
python demo_adaptive_build_order.py
```

Run the unit tests:

```bash
python test_adaptive_standalone.py
```

## Future Work

The counter logic that populates `unit_counter_request` will be implemented separately. This system provides the framework for:

1. **Enemy Analysis**: Detect enemy unit compositions
2. **Counter Selection**: Determine optimal counter units
3. **Dynamic Response**: Adjust build priorities in real-time
4. **Strategic Adaptation**: Learn and improve counter strategies

## Migration Notes

- **Old System**: 11 simultaneous build lists with minimal enemy reaction
- **New System**: Single adaptive system with dynamic counter prioritization
- **Compatibility**: All existing tactics, micro, and other bot systems remain unchanged
- **Performance**: More efficient resource usage and faster adaptation to threats

The adaptive build order maintains the bot's existing functionality while adding intelligent counter-unit production based on enemy analysis.