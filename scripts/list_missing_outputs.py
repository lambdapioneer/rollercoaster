import os
import sys


def get_input_files(folder_path):
    paths = sorted(os.listdir(folder_path))
    for path in paths:
        if not ".input" in path or ".output" in path:
            continue
        yield os.path.join(folder_path, path)

if __name__=="__main__":
    input_paths = list(get_input_files(sys.argv[1]))
    missing_output_files = [
        input_path + '.output'
        for input_path in input_paths
        if not os.path.exists(input_path + '.output')
    ]

    for missing_path in missing_output_files:
        print("MISSING:", missing_path)
    print()
    print(f"Total missing {len(missing_output_files)} of total {len(input_paths)}")