from argparse import ArgumentParser
import re

import utils as u
from copy import deepcopy
from numpy import array, dtype, int32, where, full, ndarray

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
        self.courses : ndarray[int] = array(i for i, course in enumerate(courses) if course.name in classroom_entry[u.MATERII])

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

class State:
    def __init__(self, problem_specs : Problem_Specs):
        self.slots : ndarray[ndarray[ndarray[(int, int)]]] = full((problem_specs.days_names.size,
                                                                   problem_specs.interval_names.size,
                                                                   problem_specs.classrooms.size, 2), -1, dtype=int32)
        self.students_left : ndarray[int] = array([course.nr_students for course in problem_specs.courses], dtype=int32)

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

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('path_file', type=str, help='The path of the file containing the problem', action='store')
    parser.add_argument('algorithm', type=str, help='The algorithm to be used', choices=['astar', 'hc'], action='store')	
    args = parser.parse_args()

    timetable_specs = u.read_yaml_file(args.path_file)
    problem_specs = Problem_Specs(timetable_specs)
    
    initial_state = State(problem_specs)

    print_state(initial_state, problem_specs)
