from argparse import ArgumentParser
import re
from numpy import array
import utils as u

class _course:
    def __init__(self, name : str, nr_students : int):
        self.name : str = name
        self.nr_students : int = nr_students

class _classroom:
    def __init__(self, name : str, classroom_entry : dict, courses : list[_course]):
        self.name : str = name
        self.capacity : int = classroom_entry[u.CAPACITY]
        self.courses : list[int] = [i for i, course in enumerate(courses) if course.name in classroom_entry[u.MATERII]]

class _professor:
    def __init__(self, name : str, professor_entry : dict, courses : list[_course], interval_names : dict[int, str], days_names : dict[int, str]):
        self.name : str = name
        self.courses : list[int] = [i for i, course in enumerate(courses) if course.name in professor_entry[u.MATERII]]
        self._parse_constraints(professor_entry[u.CONSTRAINTS], interval_names, days_names)
        
    def _parse_constraints(self, constraints : list[str], interval_names : dict[int, str], days_names : dict[int, str]):
        self.hours_constraints : array[int] = array([0 for _ in range(len(interval_names))])
        self.days_constraints : array[int] = array([0 for _ in range(len(days_names))])
        self.pause_constraints : int = 0
        for constraint in constraints:
            if constraint[0] == '!':
                preference : int = -1
                start_idx : int = 1
            else:
                preference : int = 1
                start_idx : int = 0

            if constraint[start_idx : ] in days_names.values():
                self.days_constraints[list(days_names.values()).index(constraint[start_idx : ])] = preference
            elif '-' in constraint:
                start, end = [int(hour) for hour in constraint[start_idx : ].split('-')]
                for i in range(start, end, 2):
                    interval_name : str = '(' + str(i) + ', ' + str(i + 2) + ')'
                    if interval_name in interval_names.values():
                        self.hours_constraints[list(interval_names.values()).index(interval_name)] = preference
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
        self.interval_names : dict[int, str] = {i : name for i, name in enumerate(timetable_specs[u.INTERVALE])}
        self.days_names : dict[int, str] = {i : name for i, name in enumerate(timetable_specs[u.ZILE])}
        self.courses : list[_course] = [_course(name, nr_students) for name, nr_students in timetable_specs[u.MATERII].items()]
        self.classrooms : list[_classroom] = [_classroom(name, classroom_entry, self.courses)
                                              for (name, classroom_entry) in timetable_specs[u.SALI].items()]
        self.professors : list[_professor] = [_professor(name, professor_entry, self.courses, self.interval_names, self.days_names) 
                                              for (name, professor_entry) in timetable_specs[u.PROFESORI].items()]

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('path_file', type=str, help='The path of the file containing the problem', action='store')
    parser.add_argument('algorithm', type=str, help='The algorithm to be used', choices=['astar', 'hc'], action='store')	
    args = parser.parse_args()

    timetable_specs = u.read_yaml_file(args.path_file)
    problem_specs = Problem_Specs(timetable_specs)
