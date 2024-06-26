from argparse import ArgumentParser
import random
import re

import utils as u
from copy import deepcopy
from numpy import append, array, int32, where, full, ndarray, zeros
from numpy import ndarray, array, full, where, int32, std, mean
import re
from copy import deepcopy
from heapq import heappush, heappop
from time import time

PROFESSOR = 0
CLASSROOM = 1

MAX_HOURS = 7

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

        if (0 in self.hours_constraints or 0 in self.days_constraints):
            raise ValueError('Invalid constraints')


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
        self.professors_left : ndarray[int] = full(problem_specs.professors.size, MAX_HOURS, dtype=int32)
        self.cost : float = 0


    def _init_from_state(self, state : 'State'):
        self.slots : ndarray[ndarray[ndarray[(int, int)]]] = deepcopy(state.slots)
        self.students_left : ndarray[int] = deepcopy(state.students_left)
        self.cost : float = state.cost
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


def _compute_penalty(state : State, problem_specs : Problem_Specs, day_idx : int, interval_idx : int, prof_index : int) -> float:
    remaning_students : int = state.students_left.sum();
    if (problem_specs.professors[prof_index].days_constraints[day_idx] == -1 or
        problem_specs.professors[prof_index].hours_constraints[interval_idx] == -1):
        return remaning_students / problem_specs.total_students
    return 0


def generate_all_possible_states(current_state : State, problem_specs : Problem_Specs) -> ndarray[State]:
    possible_states : ndarray[State] = array([], dtype=State)
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
                                    new_state.students_left[course_idx] = max(new_state.students_left[course_idx] -
                                                                              problem_specs.classrooms[classroom_idx].capacity, 0)
                                    new_state.cost += _compute_penalty(new_state, problem_specs, day_idx, interval_idx, prof_index)
                                    new_state.professors_left[prof_index] -= 1
                                    possible_states = append(possible_states, new_state)
    return possible_states


def compute_professor_workload_balance(state : State, problem_specs : Problem_Specs) -> float:
    remaning_students : int = state.students_left.sum()
    balance : float = 0
    if remaning_students == 0:
        return 0
    for course_idx, students in enumerate(state.students_left):
        professors : ndarray[int] = where(problem_specs.professors_per_course[course_idx])[0]
        professors_workload : ndarray[int] = array([MAX_HOURS - state.professors_left[prof] for prof in professors])
        std_dev : float = std(professors_workload)
        range_dev : float = professors_workload.max() - professors_workload.min()
        if range_dev == 0:
            continue
        balance += (students / remaning_students) * (std_dev / range_dev)
    return balance


def compute_classroom_workload_balance(state : State, problem_specs : Problem_Specs) -> float:
    remaning_students : int = state.students_left.sum()
    if remaning_students == 0:
        return 0

    possible_students_assignment : ndarray[float] = zeros(problem_specs.courses.size, dtype=float)

    for day_idx in range(problem_specs.days_names.size):
        for interval_idx in range(problem_specs.interval_names.size):
            for classroom_idx in range(problem_specs.classrooms.size):
                if state.slots[day_idx][interval_idx][classroom_idx][PROFESSOR] == -1:
                    for course in problem_specs.classrooms[classroom_idx].courses:
                        possible_students_assignment[course] += problem_specs.courses[course].nr_students

    for i, possible_students in enumerate(possible_students_assignment):
        if state.students_left[i] == 0:
            possible_students_assignment[i] = 0
        elif possible_students == 0 and state.students_left[i] > 0:
            possible_students_assignment[i] = 10
        else:
            possible_students_assignment[i] = state.students_left[i] / possible_students

    return mean(possible_students_assignment)


def compute_cost(state : State, problem_specs : Problem_Specs) -> float:
    remaning_students_factor : float = state.students_left.sum() / problem_specs.total_students
    classroom_workload_factor : float = compute_classroom_workload_balance(state, problem_specs)
    return remaning_students_factor + classroom_workload_factor


def is_final_state(state : State) -> bool:
    return state.students_left.sum() == 0


def astar(start : State, problem_specs : Problem_Specs, h : callable = compute_cost,
          generate_states : callable = generate_all_possible_states, is_final : callable = is_final_state, print_flag : bool = True) -> State:
    frontier = []
    heappush(frontier, (h(start, problem_specs), start))

    iterations : int = 0
    states_generated : int = 0

    while frontier:
        [_, node] = heappop(frontier)
        iterations += 1
        if is_final(node):
            break
        neighbours = generate_states(node, problem_specs)
        states_generated += neighbours.size
        for neighbour in neighbours:
            heappush(frontier, (neighbour.cost + h(neighbour, problem_specs), neighbour))

    if print_flag:
        print(f'Iterations: {iterations}')
        print(f'States generated: {states_generated}')

    return node


def hill_climbing(initial: State, problem_specs : Problem_Specs, h : callable = compute_cost,
                  generate_states : callable = generate_all_possible_states, is_final : callable = is_final_state,
                  max_iters: int = 100, print_flag : bool = True) -> tuple[bool, State, int, int]:
    iterations = 0
    states_generated = 0

    current_state = initial

    while iterations < max_iters:
        iterations += 1

        cost = current_state.cost + h(current_state, problem_specs)
        all_states = generate_states(current_state, problem_specs)
        
        states_generated += all_states.size
        
        sampled_states = random.sample(list(all_states), min(30, all_states.size))

        next_states = [state for state in sampled_states if (state.cost * state.cost + h(state, problem_specs)) < cost]

        if not next_states:
            break
        current_state = random.choice(next_states)
        if is_final(current_state):
            break

    return is_final(current_state), current_state, iterations, states_generated


def try_hill_climbing(initial: State, problem_specs : Problem_Specs, max_tries : int = 100, print_flag : bool = True) -> State:
    best_state = None
    
    total_states_generated = 0
    total_iterations = 0

    max_hc_iterations = initial.slots.size

    for _ in range(max_tries):
        final, state, iterations, states_generated = hill_climbing(initial, problem_specs, max_iters=max_hc_iterations, print_flag=print_flag)
        total_states_generated += states_generated
        total_iterations += iterations
        
        if final:
            best_state = state
            break
        elif best_state is None or state.cost < best_state.cost:
            best_state = state

    if print_flag:
        if not is_final_state(best_state):
            print('No valid solution found')
        print(f'Total iterations: {total_iterations}')
        print(f'Total states generated: {total_states_generated}')
    return best_state


def print_state(state : State, problem_specs : Problem_Specs, input_path : str):
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

    print(u.pretty_print_timetable_aux_zile(time_table, input_path))


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('path_file', type=str, help='The path of the file containing the problem', action='store')
    parser.add_argument('algorithm', type=str, help='The algorithm to be used', choices=['astar', 'hc'], action='store')	
    args = parser.parse_args()

    timetable_specs = u.read_yaml_file(args.path_file)
    problem_specs = Problem_Specs(timetable_specs)
    
    initial_state = State(problem_specs)

    start_time = time()

    if args.algorithm == 'astar':
        final_state = astar(initial_state, problem_specs)
        print_state(final_state, problem_specs, args.path_file)
    else:
        final_state = try_hill_climbing(initial_state, problem_specs)
        print_state(final_state, problem_specs, args.path_file)

    print(f'Execution time: {time() - start_time} seconds')
