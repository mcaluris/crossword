import sys
from copy import deepcopy
from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        if not self.ac3():
            return None

        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        remove_words = []
        for var, domain in self.domains.items():
            for word in domain:
                if len(word) != var.length:
                    remove_words.append(word)
            for word in remove_words:
                self.domains[var].remove(word)
            remove_words.clear()

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        revised = False
        remove_words = set()
        if not self.crossword.overlaps[x, y]:
            return revised
        overlap = self.crossword.overlaps[x, y]
        x_words = list(self.domains[x])
        for word_x in x_words:
            count = 0
            for word_y in self.domains[y]:
                if word_x[overlap[0]] == word_y[overlap[1]]:
                    break
                if word_x[overlap[0]] != word_y[overlap[1]]:
                    count += 1
            if count == len(self.domains[y]):
                remove_words.add(word_x)
                revised = True
        if remove_words:
            for word in remove_words:
                self.domains[x].remove(word)
        return revised

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        queue = list()
        if arcs is None:
            for arc in self.crossword.overlaps:
                if arc is not None:
                    queue.append(arc)
        else:
            for arc in arcs:
                queue.append(arc)
        while queue:
            arc = queue.pop(0)
            x, y = arc
            if self.revise(x, y):
                if not self.domains[x]:
                    return False
                for neighbor in self.crossword.neighbors(x):
                    if neighbor != y:
                        queue.append((neighbor, x))
        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        if len(assignment.keys()) == len(self.domains.keys()):
            return True
        return False

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        if len(assignment.values()) != len(set(assignment.values())):
            return False
        for var_1, word in assignment.items():
            neighbors = self.crossword.neighbors(var_1)
            for var_2 in neighbors:
                if var_2 in assignment:
                    overlap = self.crossword.overlaps[var_1, var_2]
                    if assignment[var_1][overlap[0]] != assignment[var_2][overlap[1]]:
                        return False
        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        values = {}
        words = self.domains[var]
        neighbors = self.crossword.neighbors(var)
        for word in words:
            if word in assignment:
                continue
            else:
                count = 0
                for neighbor in neighbors:
                    overlap = self.crossword.overlaps[var, neighbor]
                    if word in self.domains[neighbor]:
                        count = count + 1
                    for w in self.domains[neighbor]:
                        if word[overlap[0]] != w[overlap[1]]:
                            count = count + 1
                values[word] = count
        return sorted(values, key=lambda key: values[key])

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        unassigned_variables = deepcopy(self.domains)
        for var in self.domains:
            if var in assignment:
                unassigned_variables.pop(var)
        lowest_count = min(unassigned_variables.items(),
                           key=lambda x: len(x[1]))
        for k, v in self.domains.items():
            if k in unassigned_variables:
                if(len(v) != len(lowest_count[1])):
                    unassigned_variables.pop(k)
        highest_count = max(unassigned_variables.keys(),
                            key=lambda x: len(self.crossword.neighbors(x)))
        return highest_count

    def backtrack(self, assignment=None):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if self.assignment_complete(assignment):
            return assignment
        copy_domains = deepcopy(self.domains)
        var = self.select_unassigned_variable(assignment)
        var_words = self.order_domain_values(var, assignment)
        for word in var_words:
            assignment.update({var: word})
            self.domains[var] = {word}
            arcs = self.get_arcs(var, assignment)
            self.ac3(arcs)
            if self.consistent(assignment):
                result = self.backtrack(assignment)
                if result is not None:
                    return result
            self.domains = copy_domains
            assignment.pop(var)
        return None

    def get_arcs(self, var, assignment):
        arcs = dict()
        neighbors = self.crossword.neighbors(var)
        for neighbor in neighbors:
            if neighbor not in assignment:
                arcs[neighbor, var] = 1
        return arcs


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    print(structure)
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()
    # Print result

    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
