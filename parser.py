import re
from typing import Dict, List, Tuple, Optional, Any
from constraint import Problem, AllDifferentConstraint

# =============================================================================
# CONFIGURATION - Enter input data here
# =============================================================================

# Puzzle text (complete)
PUZZLE_TEXT = '''
There are 6 houses, numbered 1 to 6 from left to right, as seen from across the street. Each house is occupied by a different person. Each house has a unique attribute for each of the following characteristics:
- Each person has a unique name: `Arnold`, `Peter`, `Eric`, `Alice`, `Bob`, `Carol`
- People have unique favorite book genres: `biography`, `science fiction`, `fantasy`, `mystery`, `romance`, `historical fiction`
- People have unique favorite sports: `baseball`, `basketball`, `swimming`, `volleyball`, `tennis`, `soccer`
- People own unique car models: `honda civic`, `ford f150`, `tesla model 3`, `chevrolet silverado`, `bmw 3 series`, `toyota camry`

## Clues:
1. Eric is the person who loves mystery books.
2. The person who loves tennis is the person who loves fantasy books.
3. The person who loves soccer is directly left of the person who loves science fiction books.
4. There is one house between the person who owns a Honda Civic and the person who loves biography books.
5. Peter is somewhere to the right of Carol.
6. The person who loves tennis is in the first house.
7. The person who owns a Tesla Model 3 is somewhere to the right of the person who loves baseball.
8. Eric is somewhere to the left of the person who loves romance books.
9. The person who owns a Toyota Camry is somewhere to the right of the person who loves romance books.
10. The person who owns a BMW 3 Series is Peter.
11. The person who owns a BMW 3 Series is the person who loves basketball.
12. The person who owns a Tesla Model 3 is directly left of Arnold.
13. Alice and the person who loves volleyball are next to each other.
14. The person who loves historical fiction books is the person who loves soccer.
15. The person who owns a Chevrolet Silverado is not in the first house.
16. The person who loves science fiction books is directly left of the person who loves swimming.
'''
#None

# Grid size (only for grid puzzles, otherwise None)
GRID_SIZE = None  # e.g. (5, 7) for 5 houses and 7 attributes

# Question (only for multiple choice)
QUESTION = "What is Name of the person who lives in House 5?" #None

# Answer choices (only for multiple choice)
CHOICES = [
"Eric",
"Bob",
"Alice",
"Peter",
"Carol",
"Arnold"
] #None

# Solution template (only for grid puzzles)
SOLUTION_TEMPLATE = None

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def isGridPuzzle() -> bool:
    """
    Determines whether this is a grid puzzle or multiple choice.
    
    Returns:
        True if grid puzzle, False if multiple choice
    """
    # Grid puzzle has GRID_SIZE and SOLUTION_TEMPLATE
    # Multiple choice has QUESTION and CHOICES
    if GRID_SIZE is not None and SOLUTION_TEMPLATE is not None:
        return True
    elif QUESTION is not None and CHOICES is not None:
        return False
    else:
        # Fallback: search for "Question:" in text
        if PUZZLE_TEXT and "Question:" in PUZZLE_TEXT:
            return False
        return True


def parse_puzzle_header(text: str) -> Dict[str, Any]:
    """
    Parses the puzzle header and extracts attributes and values.
    
    Returns:
        Dict with 'num_houses', 'attributes' (Dict of attribute_name -> [values])
    """
    result = {
        'num_houses': 0,
        'attributes': {}
    }
    
    # Extract number of houses
    house_match = re.search(r'There are (\d+) houses', text)
    if house_match:
        result['num_houses'] = int(house_match.group(1))
    
    # Extract attributes - look for lines with attribute definitions
    lines = text.split('\n')
    
    for line in lines:
        # Search for attribute definitions
        # Pattern: "- Each person has a unique [attribute]: `value1`, `value2`, ..."
        attr_match = re.search(r'-\s*.*?(?:name|nationality|book genre|food|color|animal|sport|car model)s?:\s*`(.+?)(?:`\s*$|$)', line, re.IGNORECASE)
        
        if attr_match:
            # Determine attribute type from line
            attr_type = None
            if 'name' in line.lower():
                attr_type = 'Name'
            elif 'nationality' in line.lower() or 'nationalities' in line.lower():
                attr_type = 'Nationality'
            elif 'book genre' in line.lower():
                attr_type = 'BookGenre'
            elif 'food' in line.lower():
                attr_type = 'Food'
            elif 'color' in line.lower():
                attr_type = 'Color'
            elif 'animal' in line.lower():
                attr_type = 'Animal'
            elif 'sport' in line.lower():
                attr_type = 'Sport'
            elif 'car model' in line.lower():
                attr_type = 'CarModel'
            
            if attr_type:
                # Extract values (separated by `, `)
                values_str = attr_match.group(1)
                values = [v.strip().strip('`').strip() for v in re.split(r'`,\s*`|`,\s*|,\s*`', values_str)]
                values = [v for v in values if v]  # Remove empty strings
                
                result['attributes'][attr_type] = values
    
    return result


def parse_clues(text: str) -> List[str]:
    """
    Extracts all clues from the text.
    
    Returns:
        List of clue strings
    """
    clues = []
    
    # Search for "## Clues:" and extract numbered list
    clues_section = re.search(r'##\s*Clues?:\s*\n(.*?)(?:\n##|\nQuestion:|\nPuzzle:|\nChoices:|\Z)', text, re.DOTALL | re.IGNORECASE)
    
    if clues_section:
        clues_text = clues_section.group(1)
        # Extract numbered lines
        clue_matches = re.findall(r'\d+\.\s*(.+?)(?=\n\d+\.|\Z)', clues_text, re.DOTALL)
        clues = [c.strip() for c in clue_matches if c.strip()]
    
    return clues


def extract_entity(text: str, attributes: Dict[str, List[str]]) -> Tuple[Optional[str], Optional[str]]:
    """
    Extracts an entity (attribute value) from text.
    
    Returns:
        Tuple of (attribute_name, value) or (None, None)
    """
    text_lower = text.lower()
    
    for attr_name, values in attributes.items():
        for value in values:
            # Check if this value appears in the text
            if value.lower() in text_lower:
                return (attr_name, value)
    
    return (None, None)


def extract_two_entities(clue: str, attributes: Dict[str, List[str]]) -> Tuple[Optional[Tuple], Optional[Tuple]]:
    """
    Extracts two entities from a clue.
    
    Returns:
        Tuple of ((attr1, val1), (attr2, val2))
    """
    found_entities = []
    clue_lower = clue.lower()
    
    # Sort attributes by value length (longest first) to avoid partial matches
    all_values = []
    for attr_name, values in attributes.items():
        for value in values:
            all_values.append((attr_name, value, len(value)))
    
    all_values.sort(key=lambda x: x[2], reverse=True)
    
    # Track which parts of the clue we've already matched
    matched_positions = []
    
    for attr_name, value, _ in all_values:
        value_lower = value.lower()
        pos = clue_lower.find(value_lower)
        
        if pos != -1:
            # Check if this position overlaps with already matched text
            overlaps = False
            for start, end in matched_positions:
                if not (pos >= end or pos + len(value_lower) <= start):
                    overlaps = True
                    break
            
            if not overlaps:
                found_entities.append((attr_name, value))
                matched_positions.append((pos, pos + len(value_lower)))
    
    if len(found_entities) >= 2:
        return (found_entities[0], found_entities[1])
    elif len(found_entities) == 1:
        return (found_entities[0], None)
    
    return (None, None)


def parse_clue_to_constraint(clue: str, attributes: Dict[str, List[str]], num_houses: int) -> Dict[str, Any]:
    """
    Parses a single clue and returns constraint information.
    
    Returns:
        Dict with constraint type and parameters
    """
    clue_lower = clue.lower()
    
    # Check constraint types in order of specificity (most specific first)
    
    # Type 9: "not in the first house" (must check before "in the first house")
    if 'not in the first house' in clue_lower:
        entities = extract_two_entities(clue, attributes)
        return {
            'type': 'not_first_house',
            'clue': clue,
            'entities': entities
        }
    
    # Type 8: "in the first house"
    if 'in the first house' in clue_lower:
        entities = extract_two_entities(clue, attributes)
        return {
            'type': 'first_house',
            'clue': clue,
            'entities': entities
        }
    
    # Type 2: "directly left of" (must check before "left of")
    if 'directly left of' in clue_lower:
        entities = extract_two_entities(clue, attributes)
        return {
            'type': 'directly_left',
            'clue': clue,
            'entities': entities
        }
    
    # Type 3: "next to each other"
    if 'next to each other' in clue_lower:
        entities = extract_two_entities(clue, attributes)
        return {
            'type': 'next_to',
            'clue': clue,
            'entities': entities
        }
    
    # Type 6: "one house between"
    if 'one house between' in clue_lower:
        entities = extract_two_entities(clue, attributes)
        return {
            'type': 'one_between',
            'clue': clue,
            'entities': entities
        }
    
    # Type 7: "two houses between"
    if 'two houses between' in clue_lower:
        entities = extract_two_entities(clue, attributes)
        return {
            'type': 'two_between',
            'clue': clue,
            'entities': entities
        }
    
    # Type 4: "somewhere to the left"
    if 'somewhere to the left' in clue_lower:
        entities = extract_two_entities(clue, attributes)
        return {
            'type': 'left_of',
            'clue': clue,
            'entities': entities
        }
    
    # Type 5: "somewhere to the right"
    if 'somewhere to the right' in clue_lower:
        entities = extract_two_entities(clue, attributes)
        return {
            'type': 'right_of',
            'clue': clue,
            'entities': entities
        }
    
    # Type 1: "X is Y" (direct equality) - check last since it's most general
    if ' is the ' in clue_lower or ' is ' in clue_lower:
        entities = extract_two_entities(clue, attributes)
        return {
            'type': 'equality',
            'clue': clue,
            'entities': entities
        }
    
    # Unknown type
    entities = extract_two_entities(clue, attributes)
    return {
        'type': 'unknown',
        'clue': clue,
        'entities': entities
    }


# =============================================================================
# CSP SOLVER
# =============================================================================

def solve_grid_puzzle(puzzle_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Solves a grid puzzle using CSP solver.
    
    Returns:
        Dict with filled solution grid
    """
    num_houses = puzzle_data['num_houses']
    attributes = puzzle_data['attributes']
    clues = puzzle_data['clues']
    
    problem = Problem()
    
    # Add variables: for each value of each attribute, a variable
    # Variable = (AttributeName, Value) -> House number (1 to num_houses)
    for attr_name, values in attributes.items():
        for value in values:
            var_name = f"{attr_name}_{value}"
            problem.addVariable(var_name, range(1, num_houses + 1))
    
    # AllDifferent for each attribute
    for attr_name, values in attributes.items():
        vars_for_attr = [f"{attr_name}_{value}" for value in values]
        problem.addConstraint(AllDifferentConstraint(), vars_for_attr)
    
    # Add constraints from clues
    for clue_info in clues:
        add_constraint_from_clue(problem, clue_info, attributes)
    
    # Find solution
    solutions = problem.getSolutions()
    
    if solutions:
        solution = solutions[0]
        return format_grid_solution(solution, attributes, num_houses)
    else:
        return {"error": "No solution found"}


def solve_multiple_choice(puzzle_data: Dict[str, Any]) -> str:
    """
    Solves a multiple choice puzzle using CSP solver.
    
    Returns:
        String with the answer
    """
    num_houses = puzzle_data['num_houses']
    attributes = puzzle_data['attributes']
    clues = puzzle_data['clues']
    question = puzzle_data['question']
    choices = puzzle_data['choices']
    
    problem = Problem()
    
    # Add variables
    print(f"\nAdding variables for {num_houses} houses...")
    for attr_name, values in attributes.items():
        for value in values:
            var_name = f"{attr_name}_{value}"
            problem.addVariable(var_name, range(1, num_houses + 1))
    
    # AllDifferent for each attribute
    for attr_name, values in attributes.items():
        vars_for_attr = [f"{attr_name}_{value}" for value in values]
        problem.addConstraint(AllDifferentConstraint(), vars_for_attr)
    
    # Add constraints from clues
    print(f"Adding {len(clues)} constraints...")
    constraints_added = 0
    for clue_info in clues:
        try:
            add_constraint_from_clue(problem, clue_info, attributes)
            if clue_info['type'] != 'unknown':
                constraints_added += 1
        except Exception as e:
            print(f"Warning: Could not add constraint for clue: {clue_info['clue'][:50]}...")
            print(f"  Error: {e}")
    
    print(f"Successfully added {constraints_added} constraints")
    
    # Find solution
    print("Solving...")
    solutions = problem.getSolutions()
    
    print(f"Found {len(solutions)} solution(s)")
    
    if solutions:
        solution = solutions[0]
        
        # Debug: print the full solution
        print("\nFull solution:")
        grid = format_grid_solution(solution, attributes, num_houses)
        if 'header' in grid:
            print(" | ".join(grid['header']))
            print("-" * 80)
            for row in grid['rows']:
                print(" | ".join(row))
        
        answer = extract_answer_from_solution(solution, question, choices, attributes)
        return answer
    else:
        return "No solution found"


def add_constraint_from_clue(problem: Problem, clue_info: Dict, attributes: Dict):
    """
    Adds constraints to the CSP problem based on clue type.
    
    Args:
        problem: The CSP problem instance
        clue_info: Dictionary containing clue type and entities
        attributes: Dictionary of all attributes and their values
    """
    clue_type = clue_info['type']
    entities = clue_info['entities']
    clue_lower = clue_info['clue'].lower()
    
    # For first_house and not_first_house, we only need one entity
    if clue_type in ['first_house', 'not_first_house']:
        if entities[0] is None:
            return
        attr1, val1 = entities[0]
        var1 = f"{attr1}_{val1}"
    else:
        # For other constraint types, we need both entities
        if entities[0] is None or entities[1] is None:
            return
        
        attr1, val1 = entities[0]
        attr2, val2 = entities[1]
        
        var1 = f"{attr1}_{val1}"
        var2 = f"{attr2}_{val2}"
        
        # For directional constraints, we need to determine the correct order
        # by checking which entity appears first in the clue text
        if clue_type in ['directly_left', 'left_of', 'right_of']:
            pos1 = clue_lower.find(val1.lower())
            pos2 = clue_lower.find(val2.lower())
            
            # If entity2 appears before entity1, swap them
            if pos2 < pos1:
                var1, var2 = var2, var1
    
    if clue_type == 'equality':
        # Type 1: Both entities are in the same house
        # Example: "The German is Bob" -> house(German) == house(Bob)
        problem.addConstraint(lambda x, y: x == y, [var1, var2])
    
    elif clue_type == 'directly_left':
        # Type 2: Entity 1 is directly left of entity 2
        # Example: "The dog owner is directly left of the fish enthusiast"
        # house(dog owner) == house(fish enthusiast) - 1
        problem.addConstraint(lambda x, y: x == y - 1, [var1, var2])
    
    elif clue_type == 'next_to':
        # Type 3: Entities are next to each other
        # Example: "Alice and the person who loves volleyball are next to each other"
        # |house(Alice) - house(volleyball)| == 1
        problem.addConstraint(lambda x, y: abs(x - y) == 1, [var1, var2])
    
    elif clue_type == 'left_of':
        # Type 4: Entity 1 is somewhere to the left of entity 2
        # Example: "The person who loves blue is somewhere to the left of the Dane"
        # house(blue) < house(Dane)
        problem.addConstraint(lambda x, y: x < y, [var1, var2])
    
    elif clue_type == 'right_of':
        # Type 5: Entity 1 is somewhere to the right of entity 2
        # Example: "Peter is somewhere to the right of Carol"
        # house(Peter) > house(Carol)
        problem.addConstraint(lambda x, y: x > y, [var1, var2])
    
    elif clue_type == 'one_between':
        # Type 6: There is one house between two entities
        # Example: "There is one house between the Norwegian and Arnold"
        # |house(Norwegian) - house(Arnold)| == 2
        problem.addConstraint(lambda x, y: abs(x - y) == 2, [var1, var2])
    
    elif clue_type == 'two_between':
        # Type 7: There are two houses between two entities
        # Example: "There are two houses between the Norwegian and Alice"
        # |house(Norwegian) - house(Alice)| == 3
        problem.addConstraint(lambda x, y: abs(x - y) == 3, [var1, var2])
    
    elif clue_type == 'first_house':
        # Type 8: Entity is in the first house
        # Example: "The person who loves tennis is in the first house"
        problem.addConstraint(lambda x: x == 1, [var1])
    
    elif clue_type == 'not_first_house':
        # Type 9: Entity is not in the first house
        # Example: "The person who owns a Chevrolet Silverado is not in the first house"
        problem.addConstraint(lambda x: x != 1, [var1])


def format_grid_solution(solution: Dict, attributes: Dict, num_houses: int) -> Dict:
    """
    Formats the solution as a grid.
    
    Args:
        solution: Dictionary mapping variable names to house numbers
        attributes: Dictionary of all attributes and their values
        num_houses: Total number of houses
    
    Returns:
        Dictionary with 'header' and 'rows' for the solution grid
    """
    # Create header
    header = ["House"] + list(attributes.keys())
    
    # Create rows
    rows = []
    for house in range(1, num_houses + 1):
        row = [str(house)]
        for attr_name in attributes.keys():
            # Find the value for this attribute in this house
            value = "___"
            for attr_value in attributes[attr_name]:
                var_name = f"{attr_name}_{attr_value}"
                if solution.get(var_name) == house:
                    value = attr_value
                    break
            row.append(value)
        rows.append(row)
    
    return {"header": header, "rows": rows}


def extract_answer_from_solution(solution: Dict, question: str, choices: List[str], attributes: Dict) -> str:
    """
    Extracts the answer to the question from the solution.
    
    Args:
        solution: Dictionary mapping variable names to house numbers
        question: The question being asked
        choices: List of possible answers
        attributes: Dictionary of all attributes
    
    Returns:
        The answer string
    """
    # Example: "What is Name of the person who lives in House 5?"
    house_match = re.search(r'House (\d+)', question)
    
    if house_match:
        target_house = int(house_match.group(1))
        
        # Determine what attribute is being asked for
        # Usually it's the Name
        target_attr = None
        if 'name' in question.lower():
            target_attr = 'Name'
        elif 'nationality' in question.lower():
            target_attr = 'Nationality'
        elif 'book genre' in question.lower():
            target_attr = 'BookGenre'
        elif 'sport' in question.lower():
            target_attr = 'Sport'
        elif 'car model' in question.lower():
            target_attr = 'CarModel'
        
        if target_attr and target_attr in attributes:
            # Find the value of this attribute in the target house
            for value in attributes[target_attr]:
                var_name = f"{target_attr}_{value}"
                if solution.get(var_name) == target_house:
                    return value
    
    return "Unknown"


# =============================================================================
# MAIN SOLVER
# =============================================================================

def solve_puzzle():
    """
    Main function: determines puzzle type and solves it accordingly.
    """
    if PUZZLE_TEXT is None:
        print("Error: PUZZLE_TEXT is not set!")
        return
    
    # Parse puzzle
    puzzle_data = parse_puzzle_header(PUZZLE_TEXT)
    puzzle_data['clues'] = [parse_clue_to_constraint(c, puzzle_data['attributes'], puzzle_data['num_houses']) 
                            for c in parse_clues(PUZZLE_TEXT)]
    
    print(f"\nParsed {puzzle_data['num_houses']} houses")
    print(f"Attributes: {list(puzzle_data['attributes'].keys())}")
    print(f"Number of clues: {len(puzzle_data['clues'])}")
    
    # Debug: show parsed clues
    print("\nParsed clue types:")
    for i, clue_info in enumerate(puzzle_data['clues'], 1):
        print(f"  {i}. Type: {clue_info['type']}, Entities: {clue_info['entities']}")
    
    # Determine puzzle type
    if isGridPuzzle():
        print("\n=== GRID PUZZLE ===")
        puzzle_data['solution_template'] = SOLUTION_TEMPLATE
        result = solve_grid_puzzle(puzzle_data)
        print("\nSolution:")
        if 'header' in result:
            # Print as formatted table
            print(" | ".join(result['header']))
            print("-" * (len(" | ".join(result['header']))))
            for row in result['rows']:
                print(" | ".join(row))
        else:
            print(result)
    else:
        print("\n=== MULTIPLE CHOICE PUZZLE ===")
        puzzle_data['question'] = QUESTION
        puzzle_data['choices'] = CHOICES
        result = solve_multiple_choice(puzzle_data)
        print(f"\nAnswer: {result}")


# =============================================================================
# EXECUTION
# =============================================================================

if __name__ == "__main__":
    # Check if data is set
    if PUZZLE_TEXT is None:
        print("Please set PUZZLE_TEXT and other variables at the top of the script!")
    else:
        solve_puzzle()