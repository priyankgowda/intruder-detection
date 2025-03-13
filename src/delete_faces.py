import os
import pickle
import shutil
from datetime import datetime
import config

def log_message(message):
    """Simple logging function"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    
    # Also write to log file
    with open(os.path.join(config.LOGS_DIR, "delete_log.txt"), "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def delete_person(person_name):
    """Delete all images for a specific person"""
    person_dir = os.path.join(config.DATASET_DIR, person_name)
    
    if not os.path.exists(person_dir):
        log_message(f"Person '{person_name}' not found in dataset")
        return False
        
    # Delete the directory
    try:
        shutil.rmtree(person_dir)
        log_message(f"Successfully deleted all images for '{person_name}'")
        
        # Also remove from encodings file if it exists
        if os.path.exists(config.ENCODINGS_FILE):
            with open(config.ENCODINGS_FILE, "rb") as f:
                data = pickle.load(f)
                
            # Find indices to remove
            indices_to_remove = [i for i, name in enumerate(data["names"]) if name == person_name]
            
            if indices_to_remove:
                # Create new lists excluding the person
                new_encodings = [enc for i, enc in enumerate(data["encodings"]) if i not in indices_to_remove]
                new_names = [name for i, name in enumerate(data["names"]) if i not in indices_to_remove]
                
                # Save updated data
                new_data = {"encodings": new_encodings, "names": new_names}
                with open(config.ENCODINGS_FILE, "wb") as f:
                    pickle.dump(new_data, f)
                    
                log_message(f"Removed {len(indices_to_remove)} encodings for '{person_name}'")
            
        return True
    except Exception as e:
        log_message(f"ERROR deleting '{person_name}': {str(e)}")
        return False

def list_people():
    """List all people in the dataset"""
    if not os.path.exists(config.DATASET_DIR):
        log_message("Dataset directory does not exist")
        return []
        
    people = [name for name in os.listdir(config.DATASET_DIR)
              if os.path.isdir(os.path.join(config.DATASET_DIR, name))]
    
    if people:
        log_message("People in dataset:")
        for i, person in enumerate(people, 1):
            num_images = len([img for img in os.listdir(os.path.join(config.DATASET_DIR, person))
                           if img.lower().endswith(('.png', '.jpg', '.jpeg'))])
            log_message(f"  {i}. {person} ({num_images} images)")
    else:
        log_message("No people found in dataset")
        
    return people

def show_menu():
    """Display interactive menu"""
    print("\n===== FACE MANAGEMENT UTILITY =====")
    print("1. List all people in the dataset")
    print("2. Delete a person from the dataset")
    print("3. Exit")
    return input("\nEnter your choice (1-3): ")

def interactive_delete():
    """Interactive deletion of a person"""
    people = list_people()
    
    if not people:
        input("\nNo people found in dataset. Press Enter to continue...")
        return
        
    print("\nEnter the number of the person to delete, or their exact name:")
    choice = input("> ")
    
    # Check if input is a number
    person_name = None
    try:
        index = int(choice) - 1
        if 0 <= index < len(people):
            person_name = people[index]
    except ValueError:
        # Input is not a number, treat as a name
        if choice in people:
            person_name = choice
    
    if not person_name:
        log_message(f"Invalid selection: '{choice}'")
        input("Press Enter to continue...")
        return
    
    # Confirm deletion
    confirm = input(f"\nAre you sure you want to delete '{person_name}'? This cannot be undone. (y/n): ")
    if confirm.lower() == 'y':
        if delete_person(person_name):
            log_message(f"Successfully deleted '{person_name}' from dataset")
        else:
            log_message(f"Failed to delete '{person_name}'")
    else:
        log_message(f"Deletion of '{person_name}' cancelled")
    
    input("\nPress Enter to continue...")

def main():
    """Main interactive function"""
    while True:
        choice = show_menu()
        
        if choice == '1':
            list_people()
            input("\nPress Enter to continue...")
        elif choice == '2':
            interactive_delete()
        elif choice == '3':
            log_message("Exiting face management utility")
            break
        else:
            print("Invalid choice, please try again.")

if __name__ == "__main__":
    main()