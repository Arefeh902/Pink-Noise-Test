import matplotlib.pyplot as plt
import numpy as np

def plot_numbers_from_file(file_path, output_image_path):
    # Read numbers from the file
    with open(file_path, 'r') as f:
        numbers = [float(line.strip()) for line in f.readlines()]
    
    # Create a simple line plot
    plt.figure(figsize=(10, 6))  # Set the figure size (optional)
    plt.plot(numbers, marker='o', linestyle='-', color='b', label='Numbers')  # Line plot with circles at data points
    
    # Adding labels and title
    plt.xlabel('Index')
    plt.ylabel('Value')
    plt.title('Line Plot of Numbers from File')
    
    # Add a grid for better readability
    plt.grid(True)
    
    # Optionally, add a legend
    plt.legend()
    
    # # Save the plot to an image file
    # plt.savefig(output_image_path, dpi=300)
    
    # Show the plot (optional)
    plt.show()

# Example usage
for i in range(1, 7):
	print(i)
	input_file_path = f'./results/__/{i}_diffs.txt' # Change to your input file
	output_image_path = f'numbers_plot_{i}.png'  # Output image file

	plot_numbers_from_file(input_file_path, output_image_path)
