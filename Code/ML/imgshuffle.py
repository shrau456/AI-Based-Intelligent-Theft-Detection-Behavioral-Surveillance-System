import os
import shutil

# Define the source directory containing the images
source_directory = r'C:\Users\sprat\OneDrive\Desktop\BTech Project\Shoplifting\yolo-pose-shoplifting\yolopose\images1' 

# Define the target directories
normal_folder = r'C:\Users\sprat\OneDrive\Desktop\BTech Project\Shoplifting\yolo-pose-shoplifting\yolopose\dataset_path\Normal' 
suspicious_folder = r'C:\Users\sprat\OneDrive\Desktop\BTech Project\Shoplifting\yolo-pose-shoplifting\yolopose\dataset_path\Suspicious'

os.makedirs(normal_folder, exist_ok=True)
os.makedirs(suspicious_folder, exist_ok=True)

for file_name in os.listdir(source_directory):
    file_path = os.path.join(source_directory, file_name)
    if os.path.isfile(file_path):
        if file_name.startswith('person_nn_'):
            number = int(file_name.split('_')[2].split('.')[0])
            # Move files based on the number
            # this 300 we got from the Sus.py files. images between this are considered normal
            if 0 <= number <= 815:  # Move person_nn_0.jpg to person_nn_10.jpg to Normal folder
                shutil.move(file_path, os.path.join(normal_folder, file_name))
                print(f'Moved {file_name} to Normal folder.')
            else:
                shutil.move(file_path, os.path.join(suspicious_folder, file_name))
                print(f'Moved {file_name} to Suspicious folder.')

print("File moving complete.")
