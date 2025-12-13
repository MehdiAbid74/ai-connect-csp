"""
Data Loader for ZebraLogicBench Dataset
=======================================
Loads puzzles from HuggingFace, local JSON/CSV files, or custom datasets.
Modular design for easy submission with different test sets.
"""

import re
import json
import os
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field

try:
    from datasets import load_dataset
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("Warning: 'datasets' library not installed. Run: pip install datasets")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


@dataclass
class CSPPuzzle:
    """Represents a parsed CSP puzzle."""
    puzzle_id: str
    num_houses: int
    attributes: Dict[str, List[str]]  # attribute_name -> list of values
    clues: List[str]  # Raw clue strings
    parsed_clues: List[Dict[str, Any]] = field(default_factory=list)  # Parsed constraint info
    solution: Optional[Dict] = None  # Ground truth solution if available
    question: Optional[str] = None  # For multiple choice puzzles
    choices: Optional[List[str]] = None  # For multiple choice puzzles
    answer: Optional[str] = None  # Correct answer


def load_zebra_logic_bench(split: str = "test", max_puzzles: Optional[int] = None, 
                           mode: str = "grid_mode") -> List[CSPPuzzle]:
    """
    Load puzzles from ZebraLogicBench dataset.
    
    Args:
        split: Dataset split ('train', 'test', etc.)
        max_puzzles: Maximum number of puzzles to load (None for all)
        mode: Dataset configuration ('grid_mode' or 'mc_mode')
    
    Returns:
        List of CSPPuzzle objects
    """
    if not HF_AVAILABLE:
        raise ImportError("Please install datasets: pip install datasets")
    
    print(f"Loading ZebraLogicBench dataset (split: {split}, mode: {mode})...")
    dataset = load_dataset("allenai/ZebraLogicBench", mode)
    
    puzzles = []
    data = dataset[split]
    
    if max_puzzles:
        data = data.select(range(min(max_puzzles, len(data))))
    
    for idx, item in enumerate(data):
        puzzle = parse_dataset_item(item, idx)
        if puzzle:
            puzzles.append(puzzle)
    
    print(f"Loaded {len(puzzles)} puzzles")
    return puzzles


def parse_dataset_item(item: Dict, idx: int) -> Optional[CSPPuzzle]:
    """
    Parse a single dataset item into a CSPPuzzle object.
    
    Args:
        item: Raw dataset item
        idx: Index for puzzle ID
    
    Returns:
        CSPPuzzle object or None if parsing fails
    """
    try:
        puzzle_text = item.get('puzzle', '')
        
        # Parse header to get houses and attributes
        puzzle_data = parse_puzzle_header(puzzle_text)
        
        # Parse clues
        clues = parse_clues(puzzle_text)
        
        # Parse each clue to constraint info
        parsed_clues = []
        for clue in clues:
            parsed = parse_clue_to_constraint(clue, puzzle_data['attributes'], puzzle_data['num_houses'])
            parsed_clues.append(parsed)
        
        # Extract question and answer for multiple choice
        question = None
        choices = None
        answer = item.get('answer', None)
        
        # Check if there's a question in the puzzle
        question_match = re.search(r'Question:\s*(.+?)(?:\n|$)', puzzle_text)
        if question_match:
            question = question_match.group(1).strip()
        
        # Extract choices if present
        choices_match = re.search(r'Choices?:\s*(.+?)(?:\n##|\Z)', puzzle_text, re.DOTALL)
        if choices_match:
            choices_text = choices_match.group(1)
            choices = [c.strip() for c in re.findall(r'[A-E]\)\s*(.+?)(?=[A-E]\)|$)', choices_text)]
        
        # Parse solution if available
        solution = None
        if 'solution' in item and item['solution']:
            try:
                if isinstance(item['solution'], str):
                    solution = json.loads(item['solution'])
                else:
                    solution = item['solution']
            except:
                pass
        
        return CSPPuzzle(
            puzzle_id=f"puzzle_{idx:03d}",
            num_houses=puzzle_data['num_houses'],
            attributes=puzzle_data['attributes'],
            clues=clues,
            parsed_clues=parsed_clues,
            solution=solution,
            question=question,
            choices=choices,
            answer=answer
        )
    
    except Exception as e:
        print(f"Warning: Could not parse puzzle {idx}: {e}")
        return None


def parse_puzzle_header(text: str) -> Dict[str, Any]:
    """
    Parse puzzle header to extract number of houses and attributes.
    
    Args:
        text: Full puzzle text
    
    Returns:
        Dict with 'num_houses' and 'attributes'
    """
    result = {
        'num_houses': 0,
        'attributes': {}
    }
    
    # Extract number of houses (handle various formats)
    house_patterns = [
        r'There are (\d+) houses',
        r'(\d+) houses',
        r'(\d+) people',
        r'(\d+) friends',
    ]
    
    for pattern in house_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['num_houses'] = int(match.group(1))
            break
    
    # Default to 5 if not found
    if result['num_houses'] == 0:
        result['num_houses'] = 5
    
    # Extract attributes
    lines = text.split('\n')
    
    # Common attribute patterns - expanded list
    attribute_keywords = {
        'name': 'Name',
        'nationality': 'Nationality',
        'nationalities': 'Nationality',
        'book genre': 'BookGenre',
        'favorite book': 'BookGenre',
        'book': 'BookGenre',
        'genre': 'Genre',
        'food': 'Food',
        'foods': 'Food',
        'lunch': 'Lunch',
        'breakfast': 'Breakfast',
        'dinner': 'Dinner',
        'meal': 'Meal',
        'color': 'Color',
        'colors': 'Color',
        'colour': 'Color',
        'animal': 'Animal',
        'animals': 'Animal',
        'pet': 'Pet',
        'pets': 'Pet',
        'sport': 'Sport',
        'sports': 'Sport',
        'car model': 'CarModel',
        'car': 'CarModel',
        'vehicle': 'CarModel',
        'drink': 'Drink',
        'drinks': 'Drink',
        'beverage': 'Drink',
        'hobby': 'Hobby',
        'hobbies': 'Hobby',
        'job': 'Job',
        'jobs': 'Job',
        'occupation': 'Occupation',
        'profession': 'Profession',
        'music genre': 'MusicGenre',
        'music': 'Music',
        'instrument': 'Instrument',
        'flower': 'Flower',
        'flowers': 'Flower',
        'movie': 'Movie',
        'movies': 'Movie',
        'city': 'City',
        'cities': 'City',
        'shirt': 'Shirt',
        'clothing': 'Clothing',
        'child': 'Children',
        'children': 'Children',
        'height': 'Height',
        'heights': 'Height',
        'age': 'Age',
        'ages': 'Age',
        'birthday': 'Birthday',
        'month': 'Month',
        'year': 'Year',
        'dessert': 'Dessert',
        'smoothie': 'Smoothie',
        'juice': 'Juice',
        'tea': 'Tea',
        'coffee': 'Coffee',
        'fruit': 'Fruit',
        'vegetable': 'Vegetable',
        'shoe': 'Shoe',
        'brand': 'Brand',
        'subject': 'Subject',
        'language': 'Language',
        'country': 'Country',
        'state': 'State',
        'transport': 'Transport',
        'vacation': 'Vacation',
        'destination': 'Destination',
        'cigar': 'Cigar',
        'smoke': 'Smoke',
        'phone': 'Phone',
        'phone model': 'Phone',
        'education': 'Education',
        'degree': 'Degree',
        'house style': 'HouseStyle',
        'style of house': 'HouseStyle',
        'hair': 'HairColor',
        'hair color': 'HairColor',
        'mother': 'Mother',
        "mother's name": 'Mother',
    }
    
    attr_counter = 0
    for line in lines:
        line_lower = line.lower()
        
        # Skip non-attribute lines
        if not line.strip().startswith('-') and 'unique' not in line_lower:
            continue
        
        # Extract values first - look for backtick-quoted values
        values = re.findall(r'`([^`]+)`', line)
        
        if not values:
            # Try comma-separated values after colon
            colon_match = re.search(r':\s*(.+)$', line)
            if colon_match:
                values_text = colon_match.group(1)
                values = [v.strip().strip('`"\'') for v in values_text.split(',')]
        
        if not values:
            continue
        
        values = [v.strip() for v in values if v.strip()]
        if not values:
            continue
        
        # Find attribute type from keywords
        attr_type = None
        for keyword, attr_name in attribute_keywords.items():
            if keyword in line_lower:
                attr_type = attr_name
                break
        
        # If no keyword match, generate a unique attribute name
        if not attr_type:
            attr_counter += 1
            attr_type = f'Attr{attr_counter}'
        
        result['attributes'][attr_type] = values
    
    return result


def parse_clues(text: str) -> List[str]:
    """
    Extract all clues from puzzle text.
    
    Args:
        text: Full puzzle text
    
    Returns:
        List of clue strings
    """
    clues = []
    
    # Find clues section
    clues_patterns = [
        r'##\s*Clues?:\s*\n(.*?)(?:\n##|\nQuestion:|\Z)',
        r'Clues?:\s*\n(.*?)(?:\n##|\nQuestion:|\Z)',
    ]
    
    clues_text = None
    for pattern in clues_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            clues_text = match.group(1)
            break
    
    if clues_text:
        # Extract numbered clues
        clue_matches = re.findall(r'\d+\.\s*(.+?)(?=\n\d+\.|\Z)', clues_text, re.DOTALL)
        clues = [c.strip().replace('\n', ' ') for c in clue_matches if c.strip()]
    
    return clues


def parse_clue_to_constraint(clue: str, attributes: Dict[str, List[str]], num_houses: int) -> Dict[str, Any]:
    """
    Parse a single clue into constraint information.
    
    Args:
        clue: Clue text
        attributes: Dict of attribute_name -> list of values
        num_houses: Number of houses in puzzle
    
    Returns:
        Dict with constraint type and parameters
    """
    clue_lower = clue.lower()
    
    # Extract entities from clue
    entities = extract_two_entities(clue, attributes)
    
    # Determine constraint type (check most specific patterns first)
    
    # Position constraints
    if 'not in the first house' in clue_lower:
        return {'type': 'not_first_house', 'clue': clue, 'entities': entities}
    
    if 'not in the last house' in clue_lower:
        return {'type': 'not_last_house', 'clue': clue, 'entities': entities, 'num_houses': num_houses}
    
    if re.search(r'in the first house|in house 1\b', clue_lower):
        return {'type': 'first_house', 'clue': clue, 'entities': entities}
    
    if re.search(r'in the last house|in house ' + str(num_houses), clue_lower):
        return {'type': 'last_house', 'clue': clue, 'entities': entities, 'num_houses': num_houses}
    
    # Specific house number
    house_num_match = re.search(r'in house (\d+)', clue_lower)
    if house_num_match:
        return {'type': 'in_house', 'clue': clue, 'entities': entities, 'house': int(house_num_match.group(1))}
    
    # Relative position constraints
    if 'directly left of' in clue_lower:
        return {'type': 'directly_left', 'clue': clue, 'entities': entities}
    
    if 'directly right of' in clue_lower:
        return {'type': 'directly_right', 'clue': clue, 'entities': entities}
    
    if 'next to each other' in clue_lower or 'are neighbors' in clue_lower:
        return {'type': 'next_to', 'clue': clue, 'entities': entities}
    
    if 'next to' in clue_lower:
        return {'type': 'next_to', 'clue': clue, 'entities': entities}
    
    # Houses between
    between_match = re.search(r'(\d+|one|two|three|four) houses? between', clue_lower)
    if between_match:
        num_str = between_match.group(1)
        num_between = {'one': 1, 'two': 2, 'three': 3, 'four': 4}.get(num_str, int(num_str) if num_str.isdigit() else 1)
        return {'type': 'houses_between', 'clue': clue, 'entities': entities, 'num_between': num_between}
    
    # Left/Right constraints
    if 'somewhere to the left' in clue_lower or 'to the left of' in clue_lower:
        return {'type': 'left_of', 'clue': clue, 'entities': entities}
    
    if 'somewhere to the right' in clue_lower or 'to the right of' in clue_lower:
        return {'type': 'right_of', 'clue': clue, 'entities': entities}
    
    # Equality (most general - check last)
    if ' is ' in clue_lower:
        return {'type': 'equality', 'clue': clue, 'entities': entities}
    
    # Unknown
    return {'type': 'unknown', 'clue': clue, 'entities': entities}


def extract_two_entities(clue: str, attributes: Dict[str, List[str]]) -> Tuple[Optional[Tuple], Optional[Tuple]]:
    """
    Extract two entities from a clue text.
    
    Args:
        clue: Clue text
        attributes: Dict of attribute_name -> list of values
    
    Returns:
        Tuple of ((attr1, val1), (attr2, val2)) or (None, None)
    """
    found_entities = []
    clue_lower = clue.lower()
    
    # Sort by value length (longest first) to avoid partial matches
    all_values = []
    for attr_name, values in attributes.items():
        for value in values:
            all_values.append((attr_name, value, len(value)))
    
    all_values.sort(key=lambda x: x[2], reverse=True)
    
    # Track matched positions to avoid overlaps
    matched_positions = []
    
    for attr_name, value, _ in all_values:
        value_lower = value.lower()
        pos = clue_lower.find(value_lower)
        
        if pos != -1:
            # Check for overlap with already matched text
            overlaps = False
            for start, end in matched_positions:
                if not (pos >= end or pos + len(value_lower) <= start):
                    overlaps = True
                    break
            
            if not overlaps:
                found_entities.append((attr_name, value, pos))
                matched_positions.append((pos, pos + len(value_lower)))
    
    # Sort by position in clue
    found_entities.sort(key=lambda x: x[2])
    
    if len(found_entities) >= 2:
        return ((found_entities[0][0], found_entities[0][1]), 
                (found_entities[1][0], found_entities[1][1]))
    elif len(found_entities) == 1:
        return ((found_entities[0][0], found_entities[0][1]), None)
    
    return (None, None)


def load_puzzles_from_json(filepath: str) -> List[CSPPuzzle]:
    """
    Load puzzles from a local JSON file.
    
    Supports multiple JSON formats:
    1. List of puzzle objects: [{"puzzle": "...", "id": "..."}, ...]
    2. Dict with puzzles: {"puzzles": [...]}
    3. Single puzzle: {"puzzle": "..."}
    
    Args:
        filepath: Path to JSON file
    
    Returns:
        List of CSPPuzzle objects
    """
    print(f"Loading puzzles from JSON: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle different JSON formats
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        if 'puzzles' in data:
            items = data['puzzles']
        elif 'data' in data:
            items = data['data']
        elif 'puzzle' in data:
            items = [data]
        else:
            items = [data]
    else:
        items = [data]
    
    puzzles = []
    for idx, item in enumerate(items):
        # Use 'id' field if present, otherwise generate
        puzzle_id = item.get('id', f'puzzle_{idx:03d}')
        puzzle = parse_dataset_item(item, idx)
        if puzzle:
            puzzle.puzzle_id = puzzle_id
            puzzles.append(puzzle)
    
    print(f"Loaded {len(puzzles)} puzzles from JSON")
    return puzzles


def load_puzzles_from_csv(filepath: str, puzzle_column: str = 'puzzle',
                          id_column: str = 'id') -> List[CSPPuzzle]:
    """
    Load puzzles from a CSV file.
    
    Args:
        filepath: Path to CSV file
        puzzle_column: Name of column containing puzzle text
        id_column: Name of column containing puzzle ID
    
    Returns:
        List of CSPPuzzle objects
    """
    if not PANDAS_AVAILABLE:
        raise ImportError("pandas is required for CSV loading: pip install pandas")
    
    print(f"Loading puzzles from CSV: {filepath}")
    df = pd.read_csv(filepath)
    
    puzzles = []
    for idx, row in df.iterrows():
        item = row.to_dict()
        # Ensure puzzle text is in correct field
        if puzzle_column in item and puzzle_column != 'puzzle':
            item['puzzle'] = item[puzzle_column]
        
        puzzle = parse_dataset_item(item, idx)
        if puzzle:
            if id_column in item:
                puzzle.puzzle_id = str(item[id_column])
            puzzles.append(puzzle)
    
    print(f"Loaded {len(puzzles)} puzzles from CSV")
    return puzzles


def load_puzzles_from_parquet(filepath: str, puzzle_column: str = 'puzzle',
                               id_column: str = 'id') -> List[CSPPuzzle]:
    """
    Load puzzles from a Parquet file.
    
    Args:
        filepath: Path to Parquet file
        puzzle_column: Name of column containing puzzle text
        id_column: Name of column containing puzzle ID
    
    Returns:
        List of CSPPuzzle objects
    """
    if not PANDAS_AVAILABLE:
        raise ImportError("pandas is required for Parquet loading: pip install pandas pyarrow")
    
    print(f"Loading puzzles from Parquet: {filepath}")
    df = pd.read_parquet(filepath)
    
    puzzles = []
    for idx, row in df.iterrows():
        item = row.to_dict()
        if puzzle_column in item and puzzle_column != 'puzzle':
            item['puzzle'] = item[puzzle_column]
        
        puzzle = parse_dataset_item(item, idx)
        if puzzle:
            if id_column in item:
                puzzle.puzzle_id = str(item[id_column])
            puzzles.append(puzzle)
    
    print(f"Loaded {len(puzzles)} puzzles from Parquet")
    return puzzles


def load_puzzles(source: str, **kwargs) -> List[CSPPuzzle]:
    """
    Universal puzzle loader - automatically detects source type.
    
    This is the main function to use for loading puzzles from any source.
    
    Args:
        source: Can be:
            - "zebra" or "zebralogic": Load from HuggingFace ZebraLogicBench
            - Path to .json file
            - Path to .csv file  
            - Path to .parquet file
            - HuggingFace dataset name (e.g., "allenai/ZebraLogicBench")
        **kwargs: Additional arguments passed to specific loader
            - split: Dataset split (default: "test")
            - max_puzzles: Maximum puzzles to load
            - mode: "grid_mode" or "mc_mode" for ZebraLogicBench
            - puzzle_column: Column name for puzzle text (CSV/Parquet)
            - id_column: Column name for puzzle ID (CSV/Parquet)
    
    Returns:
        List of CSPPuzzle objects
    
    Examples:
        # Load from ZebraLogicBench
        puzzles = load_puzzles("zebra", split="test", max_puzzles=100)
        
        # Load from local JSON
        puzzles = load_puzzles("test_data.json")
        
        # Load from CSV
        puzzles = load_puzzles("puzzles.csv", puzzle_column="puzzle_text")
        
        # Load from Parquet
        puzzles = load_puzzles("data/test.parquet")
    """
    source_lower = source.lower()
    
    # Check if it's a file path
    if os.path.exists(source):
        ext = os.path.splitext(source)[1].lower()
        if ext == '.json':
            return load_puzzles_from_json(source)
        elif ext == '.csv':
            return load_puzzles_from_csv(source, 
                                         puzzle_column=kwargs.get('puzzle_column', 'puzzle'),
                                         id_column=kwargs.get('id_column', 'id'))
        elif ext == '.parquet':
            return load_puzzles_from_parquet(source,
                                              puzzle_column=kwargs.get('puzzle_column', 'puzzle'),
                                              id_column=kwargs.get('id_column', 'id'))
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    # Check if it's a ZebraLogicBench shorthand
    if source_lower in ['zebra', 'zebralogic', 'zebralogicbench']:
        return load_zebra_logic_bench(
            split=kwargs.get('split', 'test'),
            max_puzzles=kwargs.get('max_puzzles'),
            mode=kwargs.get('mode', 'grid_mode')
        )
    
    # Try loading as HuggingFace dataset
    if '/' in source:
        if not HF_AVAILABLE:
            raise ImportError("datasets library required: pip install datasets")
        
        print(f"Loading from HuggingFace: {source}")
        dataset = load_dataset(source, kwargs.get('mode', 'grid_mode'))
        split = kwargs.get('split', 'test')
        data = dataset[split]
        
        max_puzzles = kwargs.get('max_puzzles')
        if max_puzzles:
            data = data.select(range(min(max_puzzles, len(data))))
        
        puzzles = []
        for idx, item in enumerate(data):
            puzzle = parse_dataset_item(item, idx)
            if puzzle:
                puzzles.append(puzzle)
        
        print(f"Loaded {len(puzzles)} puzzles")
        return puzzles
    
    raise ValueError(f"Could not determine how to load: {source}")


def puzzle_to_dict(puzzle: CSPPuzzle) -> Dict:
    """
    Convert a CSPPuzzle to dictionary format.
    
    Args:
        puzzle: CSPPuzzle object
    
    Returns:
        Dictionary representation
    """
    return {
        'puzzle_id': puzzle.puzzle_id,
        'num_houses': puzzle.num_houses,
        'attributes': puzzle.attributes,
        'clues': puzzle.clues,
        'parsed_clues': puzzle.parsed_clues,
        'solution': puzzle.solution,
        'question': puzzle.question,
        'choices': puzzle.choices,
        'answer': puzzle.answer
    }


if __name__ == "__main__":
    # Test loading
    print("Testing data loader...")
    print("=" * 50)
    
    if HF_AVAILABLE:
        # Test universal loader
        print("\n1. Testing ZebraLogicBench loader:")
        puzzles = load_puzzles("zebra", split="test", max_puzzles=3)
        
        for p in puzzles:
            print(f"\n  {p.puzzle_id}:")
            print(f"    Houses: {p.num_houses}")
            print(f"    Attributes: {list(p.attributes.keys())}")
            print(f"    Clues: {len(p.clues)}")
        
        print("\n" + "=" * 50)
        print("Data loader test complete!")
    else:
        print("Please install datasets: pip install datasets")
