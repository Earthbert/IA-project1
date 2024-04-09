from argparse import ArgumentParser
import utils as u

if __name__ == '__main__':
	parser = ArgumentParser()
	parser.add_argument('path_file', type=str, help='The path of the file containing the problem', action='store')
	parser.add_argument('algorithm', type=str, help='The algorithm to be used', choices=['astar', 'hc'], action='store')	
	args = parser.parse_args()
 
	timetable_specs = u.read_yaml_file(args.path_file)
	print(timetable_specs)
