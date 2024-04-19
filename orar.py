from argparse import ArgumentParser
import re

import utils as u
from copy import deepcopy
from numpy import array, int32, where, full, ndarray
from numpy import ndarray, array, full, where, int32
import re
from copy import deepcopy
from heapq import heappush, heappop


PROFESSOR = 0
CLASSROOM = 1


class Course:
    def __init__(self, name : str, nr_students : int):
        self.name : str = name
        self.nr_students : int = nr_students


class Classroom:
    def __init__(self, name : str, classroom_entry : dict, courses : ndarray[Course]):
        self.name : str = name
        self.capacity : int = classroom_entry[u.CAPACITY]
        self.courses : ndarray[int] = array([i for i, course in enumerate(courses) if course.name in classroom_entry[u.MATERII]])


class Professor:
    def __init__(self, name : str, professor_entry : dict, courses : ndarray[Course],
                 interval_names : ndarray[str], days_names : ndarray[str]):
        self.name : str = name
        self.courses : ndarray[int] = array([i for i, course in enumerate(courses) if course.name in professor_entry[u.MATERII]])
        self.parse_constraints(professor_entry[u.CONSTRAINTS], interval_names, days_names)


    def parse_constraints(self, constraints : list[str], interval_names : ndarray[str], days_names : ndarray[str]):
        self.hours_constraints : ndarray[int] = full(interval_names.size, 0, dtype=int32)
        self.days_constraints : ndarray[int] = full(days_names.size, 0, dtype=int32)
        self.pause_constraints : int = 0
        for constraint in constraints:
            if constraint[0] == '!':
                preference : int = -1
                start_idx : int = 1
            else:
                preference : int = 1
                start_idx : int = 0

            if constraint[start_idx : ] in days_names:
                self.days_constraints[where(days_names == constraint[start_idx : ])[0]] = preference
            elif '-' in constraint:
                start, end = [int(hour) for hour in constraint[start_idx : ].split('-')]
                for i in range(start, end, 2):
                    interval_name : str = '(' + str(i) + ', ' + str(i + 2) + ')'
                    if interval_name in interval_names:
                        self.hours_constraints[where(interval_names == interval_name)[0]] = preference
                    else:
                        print(f'Interval {interval_name} not found. Ignoring...')
            elif 'Pauza' in constraint:
                get_pause = re.search(r'\d+', constraint)
                if get_pause:
                    self.pause_constraints = int(get_pause.group())
                else:
                    print(f'Invalid pause constraint {constraint}. Ignoring...')


class Problem_Specs:
    def __init__(self, timetable_specs):
        self.interval_names : ndarray[str] = array([name for name in timetable_specs[u.INTERVALE]])
        self.days_names : ndarray[str] = array([name for name in timetable_specs[u.ZILE]])
        self.courses : ndarray[Course] = array([Course(name, nr_students) for name, nr_students in timetable_specs[u.MATERII].items()])
        self.classrooms : ndarray[Classroom] = array([Classroom(name, classroom_entry, self.courses)
                                              for (name, classroom_entry) in timetable_specs[u.SALI].items()])
        self.professors : ndarray[Professor] = array([Professor(name, professor_entry, self.courses, self.interval_names, self.days_names) 
                                              for (name, professor_entry) in timetable_specs[u.PROFESORI].items()])
        self.professors_per_course : ndarray[ndarray[int]] = full((self.courses.size, self.professors.size), False, dtype=bool)
        for i, professor in enumerate(self.professors):
            for course in professor.courses:
                self.professors_per_course[course][i] = True
        self.total_students : int = sum([course.nr_students for course in self.courses])


class State:
    def _init_from_problem_specs(self, problem_specs : Problem_Specs):
        self.slots : ndarray[ndarray[ndarray[(int, int)]]] = full((problem_specs.days_names.size,
                                                                   problem_specs.interval_names.size,
                                                                   problem_specs.classrooms.size, 2), -1, dtype=int32)
        self.students_left : ndarray[int] = array([course.nr_students for course in problem_specs.courses], dtype=int32)
        self.professors_left : ndarray[int] = full(problem_specs.professors.size, 7, dtype=int32)
        self.cost : int = 0


    def _init_from_state(self, state : 'State'):
        self.slots : ndarray[ndarray[ndarray[(int, int)]]] = deepcopy(state.slots)
        self.students_left : ndarray[int] = deepcopy(state.students_left)
        self.cost : int = state.cost
        self.professors_left : ndarray[int] = deepcopy(state.professors_left)


    def __init__(self, *args):
        if len(args) != 1:
            raise ValueError('Invalid number of arguments')
        if isinstance(args[0], Problem_Specs):
            self._init_from_problem_specs(*args)
        elif isinstance(args[0], State):
            self._init_from_state(*args)


    def __lt__(self, other : 'State') -> bool:
        return self.students_left.sum() < other.students_left.sum()


def print_state(state : State, problem_specs : Problem_Specs):
    time_table = {}
    for day_idx, day_name in enumerate(problem_specs.days_names):
        time_table[day_name] = {}
        for interval_idx, interval_name in enumerate(problem_specs.interval_names):
            interval = tuple([int(hour) for hour in interval_name.strip('()').split(', ')])
            time_table[day_name][interval] = {}
            for classroom_idx, classroom in enumerate(problem_specs.classrooms):
                time_table[day_name][interval][classroom.name] = {}
                if state.slots[day_idx][interval_idx][classroom_idx][PROFESSOR] != -1:
                    time_table[day_name][interval][classroom.name] = (problem_specs.professors[state.slots[day_idx][interval_idx][classroom_idx][PROFESSOR]].name,
                                                                           problem_specs.courses[state.slots[day_idx][interval_idx][classroom_idx][CLASSROOM]].name)
                    
    print(u.pretty_print_timetable_aux_zile(time_table))


def _compute_penalty(problem_specs : Problem_Specs, day_idx : int, interval_idx : int, prof_index : int) -> int:
    if (problem_specs.professors[prof_index].days_constraints[day_idx] == -1 or
        problem_specs.professors[prof_index].hours_constraints[interval_idx] == -1):
        return 100
    if (problem_specs.professors[prof_index].days_constraints[day_idx] == 0 or
        problem_specs.professors[prof_index].hours_constraints[interval_idx] == 0):
        return 50
    return 0


def generate_all_possible_states(current_state : State, problem_specs : Problem_Specs) -> list[State]:
    possible_states : list[State] = []
    for day_idx in range(problem_specs.days_names.size):
        for interval_idx in range(problem_specs.interval_names.size):
            for classroom_idx in range(problem_specs.classrooms.size):
                if current_state.slots[day_idx][interval_idx][classroom_idx][PROFESSOR] == -1:
                    for course_idx in range(problem_specs.courses.size):
                        if current_state.students_left[course_idx] > 0 and course_idx in problem_specs.classrooms[classroom_idx].courses:
                            for prof_index, _ in enumerate(problem_specs.professors_per_course[course_idx]):
                                if (not any([prof_index == current_state.slots[day_idx][interval_idx][i][PROFESSOR] 
                                            for i, _ in enumerate(problem_specs.classrooms)])
                                    and course_idx in problem_specs.professors[prof_index].courses
                                    and current_state.professors_left[prof_index] > 0):
                                    new_state = State(current_state)
                                    new_state.slots[day_idx][interval_idx][classroom_idx][PROFESSOR] = prof_index
                                    new_state.slots[day_idx][interval_idx][classroom_idx][CLASSROOM] = course_idx
                                    new_state.students_left[course_idx] -= problem_specs.classrooms[classroom_idx].capacity
                                    new_state.cost += _compute_penalty(problem_specs, day_idx, interval_idx, prof_index)
                                    new_state.professors_left[prof_index] -= 1
                                    possible_states.append(new_state)
    return possible_states


def compute_cost(state : State, problem_specs : Problem_Specs) -> float:
    total_students = problem_specs.total_students
    remaining_students = state.students_left.sum()
    if (total_students - remaining_students) == 0:
        return 0
    return ((remaining_students * state.cost) / (total_students - remaining_students))


def is_final_state(state : State) -> bool:
    return state.students_left.sum() == 0


def astar(start : State, problem_specs : Problem_Specs, h : callable = compute_cost,
          compute_neightbours : callable = generate_all_possible_states, is_final : callable = is_final_state) -> State:
    frontier = []
    heappush(frontier, (h(start, problem_specs), start))

    iterations = 0
    
    while frontier:
        [_, node] = heappop(frontier)
        iterations += 1
        if is_final(node):
            break
        neighbours = compute_neightbours(node, problem_specs)
        for neighbour in neighbours:
            heappush(frontier, (neighbour.cost + h(neighbour, problem_specs), neighbour))

    print(f'Iterations: {iterations}')
    return node


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('path_file', type=str, help='The path of the file containing the problem', action='store')
    parser.add_argument('algorithm', type=str, help='The algorithm to be used', choices=['astar', 'hc'], action='store')	
    args = parser.parse_args()

    timetable_specs = u.read_yaml_file(args.path_file)
    problem_specs = Problem_Specs(timetable_specs)
    
    initial_state = State(problem_specs)

    if args.algorithm == 'astar':
        final_state = astar(initial_state, problem_specs)
        print_state(final_state, problem_specs)
    else:
        print('Not implemented')
