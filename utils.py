import os
import pandas as pd
from config import INPUT_DATA_FILE_NAME, INPUT_CIRCLES_FILE_NAME, INPUT_RECTS_FILE_NAME

def create_input_file_from_excel(directory: str, output_file: str):
    """
    Combines general test data, circles, and rectangles data from Excel files into a single input CSV file.

    Args:
        directory (str): Path to the directory containing the Excel files.
        output_file (str): Path to the output file to be generated (CSV format).
    """
    general_test_data_path = os.path.join(directory, INPUT_DATA_FILE_NAME)
    circles_path = os.path.join(directory, INPUT_CIRCLES_FILE_NAME)
    rects_path = os.path.join(directory, INPUT_RECTS_FILE_NAME)
        
    # Check if required files exist
    if not all(os.path.exists(path) for path in [general_test_data_path, circles_path, rects_path]):
        raise FileNotFoundError("One or more required Excel files (general_test_data.xlsx, circles.xlsx, rects.xlsx) are missing.")

    # Read Excel files into DataFrames
    general_test_data = pd.read_excel(general_test_data_path, header=None)
    circles = pd.read_excel(circles_path, header=None)
    rects = pd.read_excel(rects_path, header=None)

    # Prepare the output DataFrame
    output_data = []
    
    circle_data_size = 3
    rect_data_size = 4

    for gen_row, circle_row, rect_row in zip(
        general_test_data.itertuples(index=False), 
        circles.itertuples(index=False), 
        rects.itertuples(index=False)
    ):
            
        # Extract middle circles
        middle_circles = list(circle_row)  # Remaining fields for middle circles
        num_middle_circles = len(middle_circles) // circle_data_size  # Each circle has 3 fields
        for i in range(0, num_middle_circles, circle_data_size):
            if middle_circles[i+2] == 0:
                num_middle_circles -= 1
                middle_circles = middle_circles[:i] + middle_circles[i+circle_data_size:]
        
        # Extract rectangles
        rectangles = list(rect_row)  # All fields in `rects.xlsx` are rectangles
        num_rectangles = len(rectangles) // rect_data_size  # Each rectangle has 6 fields
        for i in range(0, num_rectangles, rect_data_size):
            zeros = 0
            for j in range(rect_data_size):
                if rectangles[i+j] == 0:
                    zeros += 1
            if zeros == rect_data_size:
                num_rectangles -= 1
                rectangles = rectangles[:i] + rectangles[i+rect_data_size:]
            
        # Combine all data into a single row
        combined_row = [
            *gen_row,
            num_middle_circles, *middle_circles,
            num_rectangles, *rectangles
        ]
        output_data.append(combined_row)

    # Save the output DataFrame to a CSV file
    output_df = pd.DataFrame(output_data)  # Adjust for column size
    output_df.to_csv(output_file, index=False, header=None)

    print(f"Input file created at: {output_file}")


# Example usage
# create_input_file_from_excel("./data/", "input_file.csv")

def create_type_folders_in_data_directory(folder_list, data_dircetory, number_of_inside_folders=1):
    if not os.path.exists(data_dircetory):
        raise FileNotFoundError(f"The directory '{data_dircetory}' does not exist.")
    
    for folder in folder_list:
        folder_path = os.path.join(data_dircetory, folder)
        try:
            os.makedirs(folder_path, exist_ok=True)
            for i in range(1, number_of_inside_folders+1):
                os.makedirs(os.path.join(folder_path, str(i)), exist_ok=True)
        except Exception as e:
            print(f"Error creating folder '{folder_path}': {e}")
    

# from config import FORM_OPTIONS_TYPES, DATA_DIRECTORY
# create_type_folders_in_data_directory(FORM_OPTIONS_TYPES, DATA_DIRECTORY, 6)