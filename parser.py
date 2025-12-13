import re
import csv
from typing import Dict, List, Tuple, Optional, Any
from constraint import Problem, AllDifferentConstraint

def read_puzzle_from_csv(csv_file: str) -> List[Dict[str, Any]]:
    """Reads all puzzle data from CSV with columns: id, puzzle, question, choices, solution_template, answer, created_at"""
    
    puzzles = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            puzzle_text = row.get('puzzle', '')
            question = row.get('question', None)
            choices_str = row.get('choices', '[]')
            solution_template = row.get('solution_template', None)
            puzzle_id = row.get('id', 'unknown')
            
            # Parse choices - handle format like "['Eric','Bob','Alice',...]"
            choices = []
            if choices_str and choices_str.strip():
                # Remove brackets and quotes, split by comma
                choices_str = choices_str.strip("[]'\"")
                choices = [c.strip().strip("'\"") for c in choices_str.split(',')]
                choices = [c for c in choices if c]  # remove empty strings
            
            # Parse solution_template if provided
            template = None
            if solution_template and solution_template.strip():
                template = solution_template.strip()
            
            puzzles.append({
                'puzzle_text': puzzle_text,
                'question': question if question and question.strip() else None,
                'choices': choices if choices else None,
                'solution_template': template,
                'puzzle_id': puzzle_id,
                'puzzle_type': 'grid' if template else ('mc' if question else 'unknown')
            })
    
    return puzzles

# Puzzle text
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

# Grid size (only for grid puzzles, otherwise None)
GRID_SIZE = None  # e.g. (5, 7) for 5 houses and 7 attributes

# Question (only for multiple choice)
QUESTION = "What is Name of the person who lives in House 5?"

# Answer choices (only for multiple choice)
CHOICES = [
"Eric",
"Bob",
"Alice",
"Peter",
"Carol",
"Arnold"
]

# Solution template (only for grid puzzles)
SOLUTION_TEMPLATE = None

# utility functions

def isGridPuzzle() -> bool:
    # determines if grid puzzle or multiple choice
    # grid puzzle has solution_template, multiple choice has questions and choices
    if SOLUTION_TEMPLATE is not None:
        return True
    elif QUESTION is not None and CHOICES is not None:
        return False
    else:
        # fallback: search for "Question:" in text
        if PUZZLE_TEXT and "Question:" in PUZZLE_TEXT:
            return False
        return True

def compute_grid_size(num_houses: int, attributes: Dict[str, List[str]]) -> Tuple[int, int]:
    # finds out grid size from puzzle data
    x = num_houses
    y = len(attributes)
    return (x, y)

def parse_puzzle_header(text: str) -> Dict[str, Any]:
    # parses puzzle header and extracts attributes and values
    result = {
        'num_houses': 0,
        'attributes': {}
    }
    
    # extract number of houses
    house_match = re.search(r'There are (\d+) houses', text)
    if house_match:
        result['num_houses'] = int(house_match.group(1))
    
    # extract attributes - look for lines with attribute definitions
    lines = text.split('\n')
    
    for line in lines:
        # search for attribute definitions
        # pattern: "- Each person has a unique [attribute]: `value1`, `value2`, ..."
        attr_match = re.search(r'-\s*.*?(?:name|nationality|book genre|food|color|animal|sport|car model)s?:\s*`(.+?)(?:`\s*$|$)', line, re.IGNORECASE)
        
        if attr_match:
            # determine attribute type from line
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
                # extract values (separated by `, `)
                values_str = attr_match.group(1)
                values = [v.strip().strip('`').strip() for v in re.split(r'`,\s*`|`,\s*|,\s*`', values_str)]
                values = [v for v in values if v]  # remove empty strings
                
                result['attributes'][attr_type] = values
    
    return result

def parse_clues(text: str) -> List[str]:
    # extracts all clues from the text
    clues = []
    
    # search for "## Clues:" and extract numbered list
    clues_section = re.search(r'##\s*Clues?:\s*\n(.*?)(?:\n##|\nQuestion:|\nPuzzle:|\nChoices:|\Z)', text, re.DOTALL | re.IGNORECASE)
    
    if clues_section:
        clues_text = clues_section.group(1)
        # extract numbered lines
        clue_matches = re.findall(r'\d+\.\s*(.+?)(?=\n\d+\.|\Z)', clues_text, re.DOTALL)
        clues = [c.strip() for c in clue_matches if c.strip()]
    
    return clues

def extract_entity(text: str, attributes: Dict[str, List[str]]) -> Tuple[Optional[str], Optional[str]]:
    # extracts an entity (attribute value) from text
    text_lower = text.lower()
    
    for attr_name, values in attributes.items():
        for value in values:
            # check if this value appears in the text
            if value.lower() in text_lower:
                return (attr_name, value)
    
    return (None, None)

def extract_two_entities(clue: str, attributes: Dict[str, List[str]]) -> Tuple[Optional[Tuple], Optional[Tuple]]:
    # extracts two entities from a clue
    found_entities = []
    clue_lower = clue.lower()
    
    # sort attributes by value length (longest first) to avoid partial matches
    all_values = []
    for attr_name, values in attributes.items():
        for value in values:
            all_values.append((attr_name, value, len(value)))
    
    all_values.sort(key=lambda x: x[2], reverse=True)
    
    # track which parts of the clue we've already matched
    matched_positions = []
    
    for attr_name, value, _ in all_values:
        value_lower = value.lower()
        pos = clue_lower.find(value_lower)
        
        if pos != -1:
            # check if this position overlaps with already matched text
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
    # parses a single clue and returns constraint information
    clue_lower = clue.lower()
    
    # check constraint types in order (most specific first)
    
    # "not in the first house" (important: check before "in the first house")
    if 'not in the first house' in clue_lower:
        entities = extract_two_entities(clue, attributes)
        return {
            'type': 'not_first_house',
            'clue': clue,
            'entities': entities
        }
    
    # "in the first house"
    if 'in the first house' in clue_lower:
        entities = extract_two_entities(clue, attributes)
        return {
            'type': 'first_house',
            'clue': clue,
            'entities': entities
        }
    
    if 'directly left of' in clue_lower:
        entities = extract_two_entities(clue, attributes)
        return {
            'type': 'directly_left',
            'clue': clue,
            'entities': entities
        }
    
    if 'next to each other' in clue_lower:
        entities = extract_two_entities(clue, attributes)
        return {
            'type': 'next_to',
            'clue': clue,
            'entities': entities
        }
    
    if 'one house between' in clue_lower:
        entities = extract_two_entities(clue, attributes)
        return {
            'type': 'one_between',
            'clue': clue,
            'entities': entities
        }
    
    if 'two houses between' in clue_lower:
        entities = extract_two_entities(clue, attributes)
        return {
            'type': 'two_between',
            'clue': clue,
            'entities': entities
        }
    
    if 'somewhere to the left' in clue_lower:
        entities = extract_two_entities(clue, attributes)
        return {
            'type': 'left_of',
            'clue': clue,
            'entities': entities
        }
    
    if 'somewhere to the right' in clue_lower:
        entities = extract_two_entities(clue, attributes)
        return {
            'type': 'right_of',
            'clue': clue,
            'entities': entities
        }
    
    # "X is Y" (direct equality) - check last since it's most general
    if ' is the ' in clue_lower or ' is ' in clue_lower:
        entities = extract_two_entities(clue, attributes)
        return {
            'type': 'equality',
            'clue': clue,
            'entities': entities
        }
    
    # unknown type
    entities = extract_two_entities(clue, attributes)
    return {
        'type': 'unknown',
        'clue': clue,
        'entities': entities
    }

# csp solver

def solve_grid_puzzle(puzzle_data: Dict[str, Any]) -> Dict[str, Any]:
    # solves a grid puzzle using csp solver
    num_houses = puzzle_data['num_houses']
    attributes = puzzle_data['attributes']
    clues = puzzle_data['clues']
    
    problem = Problem()
    
    # add variables: for each value of each attribute, a variable
    # variable = (AttributeName, Value) -> house number (1 to num_houses)
    for attr_name, values in attributes.items():
        for value in values:
            var_name = f"{attr_name}_{value}"
            problem.addVariable(var_name, range(1, num_houses + 1))
    
    # alldifferent for each attribute
    for attr_name, values in attributes.items():
        vars_for_attr = [f"{attr_name}_{value}" for value in values]
        problem.addConstraint(AllDifferentConstraint(), vars_for_attr)
    
    # add constraints from clues
    for clue_info in clues:
        add_constraint_from_clue(problem, clue_info, attributes)
    
    # find solution
    solutions = problem.getSolutions()
    
    if solutions:
        solution = solutions[0]
        return format_grid_solution(solution, attributes, num_houses)
    else:
        return {"error": "no solution found"}

def solve_multiple_choice(puzzle_data: Dict[str, Any]) -> str:
    # solves CSP multiple choice puzzle
    num_houses = puzzle_data['num_houses']
    attributes = puzzle_data['attributes']
    clues = puzzle_data['clues']
    question = puzzle_data['question']
    choices = puzzle_data['choices']
    
    problem = Problem()
    
    # add variables
    print(f"\nadding variables for {num_houses} houses...")
    for attr_name, values in attributes.items():
        for value in values:
            var_name = f"{attr_name}_{value}"
            problem.addVariable(var_name, range(1, num_houses + 1))
    
    # alldifferent for each attribute
    for attr_name, values in attributes.items():
        vars_for_attr = [f"{attr_name}_{value}" for value in values]
        problem.addConstraint(AllDifferentConstraint(), vars_for_attr)
    
    # try to add all constraints from clues
    print(f"adding {len(clues)} constraints...")
    constraints_added = 0
    for clue_info in clues:
        try:
            add_constraint_from_clue(problem, clue_info, attributes)
            if clue_info['type'] != 'unknown':
                constraints_added += 1
        except Exception as e:
            print(f"warning: could not add constraint for clue: {clue_info['clue'][:50]}...")
            print(f"  error: {e}")
    
    print(f"successfully added {constraints_added} constraints")
    
    # find solution
    print("solving...")
    solutions = problem.getSolutions()
    
    print(f"found {len(solutions)} solution(s)")
    
    if solutions:
        solution = solutions[0]
        
        # print the full solution
        print("\nfull solution:")
        grid = format_grid_solution(solution, attributes, num_houses)
        if 'header' in grid:
            print(" | ".join(grid['header']))
            print("-" * 80)
            for row in grid['rows']:
                print(" | ".join(row))
        
        answer = extract_answer_from_solution(solution, question, choices, attributes)
        return answer
    else:
        return "no solution found"

def add_constraint_from_clue(problem: Problem, clue_info: Dict, attributes: Dict):
    # adds constraints to the csp problem (depends on clue type)
    clue_type = clue_info['type']
    entities = clue_info['entities']
    clue_lower = clue_info['clue'].lower()
    
    # for first_house and not_first_house
    if clue_type in ['first_house', 'not_first_house']:
        if entities[0] is None:
            return
        attr1, val1 = entities[0]
        var1 = f"{attr1}_{val1}"
    else:
        # for other constraint types, we need both entities
        if entities[0] is None or entities[1] is None:
            return
        
        attr1, val1 = entities[0]
        attr2, val2 = entities[1]
        
        var1 = f"{attr1}_{val1}"
        var2 = f"{attr2}_{val2}"
        
        # for directional constraints, find correct order
        # (check which entity appears first in the clue text)
        if clue_type in ['directly_left', 'left_of', 'right_of']:
            pos1 = clue_lower.find(val1.lower())
            pos2 = clue_lower.find(val2.lower())
            
            # swap if entity2 appears first
            if pos2 < pos1:
                var1, var2 = var2, var1
    
    if clue_type == 'equality':
        # both entities are in the same house
        # example: "the german is bob" -> house(german) == house(bob)
        problem.addConstraint(lambda x, y: x == y, [var1, var2])
    
    elif clue_type == 'directly_left':
        # entity 1 is directly left of entity 2
        # example: "the dog owner is directly left of the fish enthusiast"
        # house(dog owner) == house(fish enthusiast) - 1
        problem.addConstraint(lambda x, y: x == y - 1, [var1, var2])
    
    elif clue_type == 'next_to':
        # entities are next to each other
        # example: "alice and the person who loves volleyball are next to each other"
        # |house(alice) - house(volleyball)| == 1
        problem.addConstraint(lambda x, y: abs(x - y) == 1, [var1, var2])
    
    elif clue_type == 'left_of':
        # entity 1 is somewhere to the left of entity 2
        # example: "the person who loves blue is somewhere to the left of the dane"
        # house(blue) < house(dane)
        problem.addConstraint(lambda x, y: x < y, [var1, var2])
    
    elif clue_type == 'right_of':
        # entity 1 is somewhere to the right of entity 2
        # example: "peter is somewhere to the right of carol"
        # house(peter) > house(carol)
        problem.addConstraint(lambda x, y: x > y, [var1, var2])
    
    elif clue_type == 'one_between':
        # there is one house between two entities
        # example: "there is one house between the norwegian and arnold"
        # |house(norwegian) - house(arnold)| == 2
        problem.addConstraint(lambda x, y: abs(x - y) == 2, [var1, var2])
    
    elif clue_type == 'two_between':
        # there are two houses between two entities
        # example: "there are two houses between the norwegian and alice"
        # |house(norwegian) - house(alice)| == 3
        problem.addConstraint(lambda x, y: abs(x - y) == 3, [var1, var2])
    
    elif clue_type == 'first_house':
        # entity is in the first house
        # example: "the person who loves tennis is in the first house"
        problem.addConstraint(lambda x: x == 1, [var1])
    
    elif clue_type == 'not_first_house':
        # entity is not in the first house
        # example: "the person who owns a chevrolet silverado is not in the first house"
        problem.addConstraint(lambda x: x != 1, [var1])

def format_grid_solution(solution: Dict, attributes: Dict, num_houses: int) -> Dict:
    # formats the solution as a grid
    # create header
    header = ["House"] + list(attributes.keys())
    
    # create rows
    rows = []
    for house in range(1, num_houses + 1):
        row = [str(house)]
        for attr_name in attributes.keys():
            # find the value for this attribute in this house
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
    # extracts the answer to the question from the solution
    # example: "what is name of the person who lives in house 5?"
    house_match = re.search(r'House (\d+)', question)
    
    if house_match:
        target_house = int(house_match.group(1))
        
        # determine what attribute is being asked for
        # usually it's the name
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
            # find the value of this attribute in the target house
            for value in attributes[target_attr]:
                var_name = f"{target_attr}_{value}"
                if solution.get(var_name) == target_house:
                    return value
    
    return "unknown"

# main solver

def solve_puzzle():
    # main function: decides which puzzle type and solves it
    if PUZZLE_TEXT is None:
        print("error: PUZZLE_TEXT is not set!")
        return
    
    # parse puzzle
    puzzle_data = parse_puzzle_header(PUZZLE_TEXT)
    puzzle_data['clues'] = [parse_clue_to_constraint(c, puzzle_data['attributes'], puzzle_data['num_houses']) 
                            for c in parse_clues(PUZZLE_TEXT)]
    
    # compute grid size
    grid_size = compute_grid_size(puzzle_data['num_houses'], puzzle_data['attributes'])
    
    print(f"\nparsed {puzzle_data['num_houses']} houses")
    print(f"attributes: {list(puzzle_data['attributes'].keys())}")
    print(f"grid size: {grid_size[0]} houses x {grid_size[1]} attributes")
    print(f"number of clues: {len(puzzle_data['clues'])}")
    
    # debug: show parsed clues
    print("\nparsed clue types:")
    for i, clue_info in enumerate(puzzle_data['clues'], 1):
        print(f"  {i}. type: {clue_info['type']}, entities: {clue_info['entities']}")
    
    # determine puzzle type
    if isGridPuzzle():
        print("\n=== grid puzzle ===")
        puzzle_data['solution_template'] = SOLUTION_TEMPLATE
        puzzle_data['grid_size'] = grid_size
        result = solve_grid_puzzle(puzzle_data)
        print("\nsolution:")
        if 'header' in result:
            # print as formatted table
            print(" | ".join(result['header']))
            print("-" * (len(" | ".join(result['header']))))
            for row in result['rows']:
                print(" | ".join(row))
        else:
            print(result)
    else:
        print("\n=== multiple choice puzzle ===")
        puzzle_data['question'] = QUESTION
        puzzle_data['choices'] = CHOICES
        puzzle_data['grid_size'] = grid_size
        result = solve_multiple_choice(puzzle_data)
        print(f"\nanswer: {result}")

# execution

if __name__ == "__main__":
    # optionally read from CSV file
    # example: python parser.py mc.csv (for multiple choice)
    # example: python parser.py grid.csv (for grid mode)
    import sys
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        try:
            csv_puzzles = read_puzzle_from_csv(csv_file)
            print(f"loaded {len(csv_puzzles)} puzzle(s) from {csv_file}\n")
            
            # solve each puzzle
            for puzzle_data in csv_puzzles:
                PUZZLE_TEXT = puzzle_data['puzzle_text']
                QUESTION = puzzle_data['question']
                CHOICES = puzzle_data['choices']
                SOLUTION_TEMPLATE = puzzle_data['solution_template']
                puzzle_type = puzzle_data['puzzle_type']
                
                print(f"\n{'='*60}")
                print(f"puzzle: {puzzle_data['puzzle_id']} ({puzzle_type} mode)")
                print(f"{'='*60}")
                
                try:
                    solve_puzzle()
                except Exception as e:
                    print(f"error solving puzzle {puzzle_data['puzzle_id']}: {e}")
                    import traceback
                    traceback.print_exc()
                
        except Exception as e:
            print(f"error reading CSV file: {e}")
            import traceback
            traceback.print_exc()
    else:
        # use hardcoded PUZZLE_TEXT
        if PUZZLE_TEXT is None:
            print("please set PUZZLE_TEXT and other variables at the top of the script!")
        else:
            solve_puzzle()